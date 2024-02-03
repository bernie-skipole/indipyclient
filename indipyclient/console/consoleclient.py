
import asyncio, sys

import curses

from base64 import standard_b64decode

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise


from ..ipyclient import IPyClient
from ..events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector, Message)

from . import windows, vector


class ConsoleClient(IPyClient):

    "Overrides IPyClient to add any event to an 'eventque'"

    async def rxevent(self, event):
        """Add event to eventque"""
        self.clientdata['eventque'].appendleft(event)


class ConsoleControl:

    def __init__(self, client, eventque, blobfolder=None):
        self.client = client
        self.blobfolder = blobfolder
        if self.blobfolder:
            self.blobenabled = True
        else:
            self.blobenabled = False

        # this is populated with events as they are received
        self.eventque = eventque

        # set up screen
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.stdscr.keypad(True)

        if curses.LINES < 24 or curses.COLS < 80:
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


    def shutdown(self):
        self._shutdown = True


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
                ##########
                # If the event is a received BLOB, save it to the BLOB Folder
                if isinstance(event, setBLOBVector):
                    # make filename from timestamp, and change colon in the timestamp to _ for safer name
                    members = event.vector.members()
                    timestampstring = event.timestamp.isoformat(sep='T').replace(":", "_")
                    for membername, member in members.items():
                        filename =  membername + "_" + timestampstring + member.blobformat
                        counter = 0
                        while True:
                            filepath = self.blobfolder / filename
                            if filepath.exists():
                                # append a digit to the filename
                                counter += 1
                                filename = membername + "_" + timestampstring + "_" + str(counter) + member.blobformat
                            else:
                                # filepath does not exist, so a new file with this filepath can be created
                                break
                        filepath.write_bytes(standard_b64decode(member.membervalue))
                ############
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
                    if isinstance(self.screen, vector.VectorScreen) and (self.screen.vectorname == event.vectorname):
                        # This vector has been disabled, show ChooseVectorScreen
                        self.screen.close("Vectors")
                        continue
                    continue
                # so its not a delete property
                if isinstance(self.screen, windows.ChooseVectorScreen):
                    self.screen.update(event)
                    continue
                if isinstance(self.screen, vector.VectorScreen) and (self.screen.vectorname == event.vectorname):
                    # The event refers to this vector
                    self.screen.update(event)

        except asyncio.CancelledError:
            self._shutdown = True
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self._shutdown = True
        finally:
            self.updatescreenstopped = True


    async def getinput(self):
        try:
            while not self.stop:
                await asyncio.sleep(0)
                if isinstance(self.screen, windows.MessagesScreen):
                    result = await self.screen.inputs()
                    if result == "Quit":
                        self._shutdown = True
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
                    if result == "Quit":
                        self._shutdown = True
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
                    if result == "Quit":
                        self._shutdown = True
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
                    if result == "Quit":
                        self._shutdown = True
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
                        self.screen = vector.VectorScreen(self.stdscr, self, self.screen.devicename, self.screen.vectorname)
                        self.screen.show()
                        continue
                if isinstance(self.screen, vector.VectorScreen):
                    result = await self.screen.inputs()
                    if result == "Quit":
                        self._shutdown = True
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
                        self.screen = windows.ChooseVectorScreen(self.stdscr, self, self.screen.devicename)
                        self.screen.show()
                        continue

        except asyncio.CancelledError:
            self._shutdown = True
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self._shutdown = True
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
