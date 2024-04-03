
import asyncio, sys, traceback

import curses

from ..ipyclient import IPyClient
from ..events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector, Message, VectorTimeOut)

from . import windows
from . import widgets

# set limit to terminal size
MINROWS = 22
MINCOLS = 78


class ConsoleClient(IPyClient):

    """Overrides IPyClient
       On receiving an event, appends it into eventque
       Which will pass the received event into ConsoleControl"""

    async def rxevent(self, event):
        """Add event to eventque"""
        self.clientdata['eventque'].appendleft(event)


class ConsoleControl:

    def __init__(self, client, blobfolder=None):
        """client is an instance of ConsoleClient
           If given, blobfolder will be the folder where BLOBs will be saved"""
        self.client = client
        self.blobfolder = blobfolder
        if self.blobfolder:
            self.blobenabled = True
        else:
            self.blobenabled = False

        # this is populated with events as they are received
        self.eventque = self.client.clientdata['eventque']

        # set up screen
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.mousemask(curses.BUTTON1_RELEASED)

        self.maxrows, self.maxcols = self.stdscr.getmaxyx()

        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
            curses.nocbreak()
            self.stdscr.keypad(False)
            curses.curs_set(1)
            curses.echo()
            curses.endwin()
            print("Terminal too small! Try 80 columns x 24 rows")
            sys.exit(1)


        # Idle, OK, Busy or Alert.
        # gray, green, yellow and red

        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)

        # this keeps track of which screen is being displayed,
        # initially start with the messages screen
        self.screen = windows.MessagesScreen(self.stdscr, self)
        self.screen.show()

        # this is set to True, to shut down the client
        self._shutdown = False
        # and shutdown routine sets this to True to stop coroutines
        self.stop = False
        # these are set to True when asyncrun is finished
        self.updatescreenstopped = False
        self.getinputstopped = False

        # list of known device names, this is needed to send
        # BLOB's enabled
        self.devicenames = []

        # BLOBfiles, is a dictionary of {(devicename,vectorname,membername):filepath}
        self.BLOBfiles = {}



    def color(self, state):
        "Returns curses.color_pair given a state"
        if not curses.has_colors():
            return curses.color_pair(0)
        state = state.lower()
        if state == "ok":
            return curses.color_pair(1)
        elif state == "busy":
            return curses.color_pair(2)
        elif state == "alert":
            return curses.color_pair(3)
        return curses.color_pair(0)

    @property
    def connected(self):
        return self.client.connected


    def shutdown(self, exc=None):
        """If exc is an exception, and logs are enabled, logs it.
           Sets self._shutdown to True which shuts down the client"""
        self._shutdown = True
        if self.client.level and not(exc is None):
            bytex = "".join(traceback.format_exception(exc)).encode()
            self.client.logfp.write(b"\n"+bytex)


    async def _checkshutdown(self):
        "If self._shutdown becomes True, shutdown"
        while not self._shutdown:
            await asyncio.sleep(0)
        await self.client.report("Shutting down client - please wait")
        self.client.shutdown()
        while not self.client.stopped:
            await asyncio.sleep(0)
        # now stop co-routines
        self.stop = True
        while (not self.updatescreenstopped) and (not self.getinputstopped):
            await asyncio.sleep(0)
        # async tasks finished, clear up the terminal
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()


    async def updatescreen(self):
        "Update while events are being received"
        try:
            while not self.stop:
                await asyncio.sleep(0)
                if isinstance(self.screen, windows.TooSmall):
                    continue
                if not self.connected:
                    if isinstance(self.screen, windows.MessagesScreen):
                        # set disconnected status and focus on the quit button
                        if not self.screen.disconnectionflag:
                            self.devicenames.clear()
                            self.screen.showunconnected() # sets disconnectionflag
                    else:
                        # when not connected, show messages screen
                        self.screen.close("Messages")
                    continue
                # act when an event is received
                try:
                    event = self.eventque.pop()
                except IndexError:
                    # no event received, so do not update screen
                    continue
                if isinstance(event, VectorTimeOut) and (event.devicename == self.screen.devicename):
                    if isinstance(self.screen, windows.ChooseVectorScreen):
                        self.screen.timeout(event)
                        continue
                    if isinstance(self.screen, windows.VectorScreen) and (self.screen.vectorname == event.vectorname):
                        self.screen.timeout(event)
                        continue
                if hasattr(event, 'devicename'):
                    # if this is a new device, update it with BLOB status
                    if event.devicename and (event.devicename not in self.devicenames):
                        if event.devicename in self.client:
                            device = self.client[event.devicename]
                            if device.enable:
                                # new devicename
                                self.devicenames.append(event.devicename)
                                if self.blobenabled:
                                    self.client.send_enableBLOB('Also', event.devicename)
                                else:
                                    self.client.send_enableBLOB('Never', event.devicename)
                # If the event is a received BLOB, save it to the BLOB Folder
                if isinstance(event, setBLOBVector):
                    # make filename from timestamp
                    timestampstring = event.timestamp.strftime('%Y%m%d_%H_%M_%S')
                    for membername, membervalue in event.items():
                        sizeformat = event.sizeformat[membername]
                        filename =  membername + "_" + timestampstring + sizeformat[1]
                        counter = 0
                        while True:
                            filepath = self.blobfolder / filename
                            if filepath.exists():
                                # append a digit to the filename
                                counter += 1
                                filename = membername + "_" + timestampstring + "_" + str(counter) + sizeformat[1]
                            else:
                                # filepath does not exist, so a new file with this filepath can be created
                                break
                        filepath.write_bytes(membervalue)
                        # record the filepath
                        self.BLOBfiles[(event.devicename, event.vectorname, membername)] = filepath
                if isinstance(self.screen, windows.MessagesScreen):
                    self.screen.update(event)
                    continue
                if isinstance(self.screen, windows.DevicesScreen):
                    self.screen.update(event)
                    continue
                if isinstance(self.screen, windows.EnableBLOBsScreen):
                    self.screen.update(event)
                    continue
                if event.devicename != self.screen.devicename:
                    # the remaining screens are only affected if the event devicename
                    # is the device they refer to
                    continue
                if isinstance(event, delProperty):
                    if event.vectorname is None:
                        # the whole device is disabled,
                        if event.devicename and (event.devicename in self.devicenames):
                            self.devicenames.remove(event.devicename)
                        # show devicesscreen
                        self.screen.close("Devices")
                        continue
                    if isinstance(self.screen, windows.ChooseVectorScreen):
                        # one vector has been disabled, update the ChooseVectorScreen
                        self.screen.update(event)
                        continue
                    if isinstance(self.screen, windows.VectorScreen) and (self.screen.vectorname == event.vectorname):
                        # This vector has been disabled, show ChooseVectorScreen
                        self.screen.close("Vectors")
                        continue
                    continue
                # so its not a delete property
                if isinstance(self.screen, windows.ChooseVectorScreen):
                    self.screen.update(event)
                    continue
                if isinstance(self.screen, windows.VectorScreen) and (self.screen.vectorname == event.vectorname):
                    # The event refers to this vector
                    self.screen.update(event)

        except asyncio.CancelledError:
            self.shutdown()
            raise
        except Exception as e:
            self.shutdown(e)
        finally:
            self.updatescreenstopped = True


    async def getinput(self):
        try:
            while not self.stop:
                await asyncio.sleep(0)
                if isinstance(self.screen, windows.TooSmall):
                    result = await self.screen.inputs()
                    if result == "Resize":
                        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
                        if self.maxrows < 10 or self.maxcols < 40:
                            self.shutdown()
                            continue
                        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
                            self.screen = windows.TooSmall(self.stdscr, self)
                            self.screen.show()
                            continue
                        # so resize has increased to proper size
                        self.screen = windows.MessagesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Quit":
                        self.shutdown()
                        break

                if isinstance(self.screen, windows.MessagesScreen):
                    result = await self.screen.inputs()
                    if result == "Resize":
                        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
                        if self.maxrows < 16 or self.maxcols < 40:
                            self.shutdown()
                            continue
                        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
                            self.screen = windows.TooSmall(self.stdscr, self)
                            self.screen.show()
                            continue
                        self.screen = windows.MessagesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Quit":
                        self.shutdown()
                        break
                    if result == "Devices":
                        self.screen = windows.DevicesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "EnableBLOBs":
                        self.screen = windows.EnableBLOBsScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                if isinstance(self.screen, windows.EnableBLOBsScreen):
                    result = await self.screen.inputs()
                    if result == "Resize":
                        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
                        if self.maxrows < 16 or self.maxcols < 40:
                            self.shutdown()
                            continue
                        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
                            self.screen = windows.TooSmall(self.stdscr, self)
                            self.screen.show()
                            continue
                        self.screen = windows.EnableBLOBsScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Quit":
                        self.shutdown()
                        break
                    if result == "Messages":
                        self.screen = windows.MessagesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Devices":
                        self.screen = windows.DevicesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                if isinstance(self.screen, windows.DevicesScreen):
                    result = await self.screen.inputs()
                    if result == "Resize":
                        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
                        if self.maxrows < 16 or self.maxcols < 40:
                            self.shutdown()
                            continue
                        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
                            self.screen = windows.TooSmall(self.stdscr, self)
                            self.screen.show()
                            continue
                        self.screen = windows.DevicesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Quit":
                        self.shutdown()
                        break
                    if result == "Messages":
                        self.screen = windows.MessagesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    devices = {devicename.lower():device for devicename, device in self.client.items() if device.enable}
                    if result in devices:
                        devicename = devices[result].devicename
                        self.screen = windows.ChooseVectorScreen(self.stdscr, self, devicename)
                        self.screen.show()
                        continue
                if isinstance(self.screen, windows.ChooseVectorScreen):
                    result = await self.screen.inputs()
                    if result == "Resize":
                        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
                        if self.maxrows < 16 or self.maxcols < 40:
                            self.shutdown()
                            continue
                        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
                            self.screen = windows.TooSmall(self.stdscr, self)
                            self.screen.show()
                            continue
                        self.screen = windows.ChooseVectorScreen(self.stdscr, self, self.screen.devicename, group=self.screen.groupwin.active)
                        self.screen.show()
                        continue
                    if result == "Quit":
                        self.shutdown()
                        break
                    if result == "Messages":
                        self.screen = windows.MessagesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Devices":
                        self.screen = windows.DevicesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Vectors":
                        # get device, vector and show VectorScreen
                        self.screen = windows.VectorScreen(self.stdscr, self, self.screen.devicename, self.screen.vectorname)
                        self.screen.show()
                        continue
                if isinstance(self.screen, windows.VectorScreen):
                    result = await self.screen.inputs()
                    if result == "Resize":
                        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
                        if self.maxrows < 16 or self.maxcols < 40:
                            self.shutdown()
                            continue
                        if self.maxrows < MINROWS or self.maxcols < MINCOLS:
                            self.screen = windows.TooSmall(self.stdscr, self)
                            self.screen.show()
                            continue
                        self.screen = windows.VectorScreen(self.stdscr, self, self.screen.devicename, self.screen.vectorname)
                        self.screen.show()
                        continue
                    if result == "Quit":
                        self.shutdown()
                        break
                    if result == "Messages":
                        self.screen = windows.MessagesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Devices":
                        self.screen = windows.DevicesScreen(self.stdscr, self)
                        self.screen.show()
                        continue
                    if result == "Vectors":
                        self.screen = windows.ChooseVectorScreen(self.stdscr, self, self.screen.devicename, group=self.screen.vector.group)
                        self.screen.show()
                        continue

        except asyncio.CancelledError:
            self.shutdown()
            raise
        except Exception as e:
            self.shutdown(e)
        finally:
            self.getinputstopped = True


    def send_enableBLOB(self):
        "Sends Also to enable blobs for all devices"
        if not self.blobenabled:
            return
        for devicename,device in self.client.items():
            if device.enable:
                self.client.send_enableBLOB('Also', devicename)

    def send_disableBLOB(self):
        "Sends Never to disable blobs for all devices"
        if self.blobenabled:
            return
        for devicename,device in self.client.items():
            if device.enable:
                self.client.send_enableBLOB('Never', devicename)


    async def asyncrun(self):
        """Gathers tasks to be run simultaneously"""
        self.stop = False
        await asyncio.gather(self.updatescreen(), self.getinput(), self._checkshutdown())
