
import asyncio, curses, sys

from . import widgets

from .. import events

class MessagesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.consoleclient = consoleclient
        self.client = consoleclient.client

        self.disconnectionflag = False

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, curses.COLS, 0, 0)
        self.titlewin.addstr(0, 0, "indipyclient console", curses.A_BOLD)

        # messages window (8 lines, full row - 4, starting at 4,3)
        self.messwin = self.stdscr.subwin(8, curses.COLS-4, 4, 3)

        # info window
        self.infowin = self.stdscr.subwin(3, 60, curses.LINES-5, curses.COLS//2 - 29)
        self.infowin.addstr(0, 0, "Once connected, choose 'Devices' and press Enter. Then use")
        self.infowin.addstr(1, 0, "Tab/Shift-Tab to move between fields, Enter to select, and")
        self.infowin.addstr(2, 0, "Arrow/Page keys to show further fields where necessary.")

        # buttons window (1 line, full row, starting at  curses.LINES - 1, 0)
        self.buttwin = self.stdscr.subwin(1, curses.COLS, curses.LINES - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, curses.COLS//2 - 10)
        self.devices_btn.focus = False
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, curses.COLS//2 + 2)
        self.quit_btn.focus = True

    @property
    def connected(self):
        return self.consoleclient.connected

    def showunconnected(self):
        "Called by consoleclient on disconnection"
        if self.consoleclient.connected:
            self.disconnectionflag = False
            return
        if self.disconnectionflag:
            # already showing a disconnected status
            return
        # disconnectionflag is false, but the client is disconnected
        # so update buttons and titlewin, and set flag True, so the update
        # does not keep repeating
        self.disconnectionflag = True
        self.titlewin.addstr(2, 0, "Not Connected")
        self.devices_btn.focus = False
        self.quit_btn.focus = True
        self.buttwin.clear()
        self.devices_btn.draw()
        self.quit_btn.draw()
        self.titlewin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()


    def show(self):
        "Displays title, info string and list of messages on a start screen"
        if self.connected:
            self.disconnectionflag = False
            self.titlewin.addstr(2, 0, "Connected    ")
            self.devices_btn.focus = True
            self.quit_btn.focus = False
        else:
            self.disconnectionflag = True
            self.titlewin.addstr(2, 0, "Not Connected")
            self.devices_btn.focus = False
            self.quit_btn.focus = True

        # draw messages
        self.messwin.clear()
        messages = self.client.messages
        lastmessagenumber = len(messages) - 1
        mlist = reversed([ t.isoformat(sep='T')[11:21] + "  " + m for t,m in messages ])
        for count, message in enumerate(mlist):
            if count == lastmessagenumber:
                # highlight the last, current message
                self.messwin.addstr(count, 0, message, curses.A_BOLD)
            else:
                self.messwin.addstr(count, 0, message)

        # draw buttons
        self.buttwin.clear()
        self.devices_btn.draw()
        self.quit_btn.draw()

        # refresh these sub-windows and update physical screen

        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.infowin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()


    def update(self, event):
        "Only update if message has changed"
        if not isinstance(event, events.Message):
            return
        self.messwin.clear()
        messages = self.client.messages
        lastmessagenumber = len(messages) - 1
        mlist = reversed([ t.isoformat(sep='T')[11:21] + "  " + m for t,m in messages ])
        for count, message in enumerate(mlist):
            if count == lastmessagenumber:
                # highlight the last, current message
                self.messwin.addstr(count, 0, message, curses.A_BOLD)
            else:
                self.messwin.addstr(count, 0, message)

        # check if connected or not
        if self.connected:
            self.titlewin.addstr(2, 0, "Connected    ")
        else:
            self.titlewin.addstr(2, 0, "Not Connected")

        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        curses.doupdate()


# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"
        try:
            self.stdscr.nodelay(True)
            while (not self.consoleclient.stop) and (self.consoleclient.screen is self):
                await asyncio.sleep(0)
                key = self.stdscr.getch()
                if key == -1:
                    continue
                if not self.connected:
                    # only accept quit
                    self.devices_btn.focus = False
                    self.quit_btn.focus = True
                    self.buttwin.clear()
                    self.devices_btn.draw()
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                    curses.doupdate()
                    if key == 10 or chr(key) == "q" or chr(key) == "Q":
                        return "Quit"
                    continue

                if key in (32, 9, 261, 338, 258, 353, 260, 339, 259):
                    # go to the other button
                    if self.devices_btn.focus:
                        self.devices_btn.focus = False
                        self.quit_btn.focus = True
                    else:
                        self.quit_btn.focus = False
                        self.devices_btn.focus = True
                    self.buttwin.clear()
                    self.devices_btn.draw()
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                    curses.doupdate()
                if chr(key) == "q" or chr(key) == "Q":
                    return "Quit"
                if chr(key) == "d" or chr(key) == "D":
                    return "Devices"
                if key == 10:
                    if self.devices_btn.focus:
                        return "Devices"
                    else:
                        return "Quit"
        except asyncio.CancelledError:
            raise
        except Exception:
            return "Quit"


class DevicesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.consoleclient = consoleclient
        self.client = consoleclient.client

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, curses.COLS, 0, 0)
        self.titlewin.addstr(0, 0, "Devices", curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, curses.COLS, 2, 0)

        # status window (1 line, full row-4, starting at 4,4)
        self.statwin = self.stdscr.subwin(1, curses.COLS-4, 4, 4)

        # devices window (8 lines, full row-4, starting at 6,4)
        self.devwin = self.stdscr.subwin(8, curses.COLS-4, 6, 4)

        # create a pad of 50 lines, full row-4
        #self.devwin = curses.newpad(50, curses.COLS-4)


        # buttons window (1 line, full row, starting at  curses.LINES - 1, 0)
        self.buttwin = self.stdscr.subwin(1, curses.COLS, curses.LINES - 1, 0)

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, curses.COLS//2 - 10)
        self.messages_btn.focus = True
        self.focus = None
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, curses.COLS//2 + 2)
        # devicename to button dictionary
        self.devices = {}


    def show(self):
        "Displays the screen with list of devices"

        # draw the message
        if self.client.messages:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.client.messages[0])

        # draw status
        if not len(self.client):
            self.statwin.addstr(0, 0, "No devices have been discovered")
        else:
            self.statwin.addstr(0, 0, "Choose a device:               ")

        # draw devices
        self.drawdevices()

        # draw buttons
        self.drawbuttons()

        # refresh these sub-windows and update physical screen

        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.statwin.noutrefresh()
        self.devwin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()



    def drawdevices(self):
        self.devwin.clear()

        # Remove current devices
        self.devices.clear()
        colnumber = curses.COLS//2 - 6
        for linenumber, devicename in enumerate(self.client):
            self.devices[devicename.lower()] = widgets.Button(self.devwin, devicename, linenumber, colnumber)

        # start with all device buttons focus False
        for devbutton in self.devices.values():
            devbutton.focus = False

        if self.focus not in self.devices:
            self.focus = None
        else:
            self.devices[self.focus].focus = True

        # draw devices buttons
        for devbutton in self.devices.values():
            devbutton.draw()


    def drawbuttons(self):
        self.buttwin.clear()

        # If a device is in focus, these buttons are not
        if self.focus:
            self.messages_btn.focus = False
            self.quit_btn.focus = False
        elif not self.quit_btn.focus:
            # device button not in focus, so one of these must be
            self.messages_btn.focus = True

        self.messages_btn.draw()
        self.quit_btn.draw()



    def update(self, event):
        "Only update if global message has changed, or a new device added or deleted"
        if isinstance(event, events.Message) and event.devicename is None:
            widgets.drawmessage(self.messwin, self.client.messages[0])
            self.messwin.noutrefresh()
            curses.doupdate()
            return
        # check devices unchanged
        if isinstance(event, events.delProperty) and event.vectorname is None:
            # a device has being deleted
            self.drawdevices()
            self.drawbuttons()
            self.devwin.noutrefresh()
            self.buttwin.noutrefresh()
            curses.doupdate()
            return
        if event.devicename is not None:
            if event.devicename.lower() not in self.devices:
                # unknown device, check this is a definition
                if isinstance(event, events.defVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwin.noutrefresh()
                    curses.doupdate()
                elif isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwin.noutrefresh()
                    curses.doupdate()



# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"
        try:
            self.stdscr.nodelay(True)
            while (not self.consoleclient.stop) and (self.consoleclient.screen is self):
                await asyncio.sleep(0)
                key = self.stdscr.getch()
                if key == -1:
                    continue
                # which button has focus
                btnlist = list(self.devices.keys())
                if key == 10:
                    if self.quit_btn.focus:
                        widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True)
                        self.messwin.noutrefresh()
                        curses.doupdate()
                        return "Quit"
                    if self.messages_btn.focus:
                        return "Messages"
                    # If not Quit or Messages, return the device in focus
                    return self.focus

                if chr(key) == "q" or chr(key) == "Q":
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"

                if chr(key) == "m" or chr(key) == "M":
                    return "Messages"

                if key in (32, 9, 261, 338, 258):
                    # go to the next button
                    if self.quit_btn.focus:
                        self.quit_btn.focus = False
                        self.focus = btnlist[0]
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        self.quit_btn.focus = True
                    else:
                        indx = btnlist.index(self.focus)
                        if indx == len(btnlist) - 1:
                            # last device
                            self.focus = None
                            self.messages_btn.focus = True
                        else:
                            self.focus = btnlist[indx+1]

                elif key in (353, 260, 339, 259):
                    # go to previous button
                    if self.quit_btn.focus:
                        self.quit_btn.focus = False
                        self.messages_btn.focus = True
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        self.focus = btnlist[-1]
                    elif self.focus == btnlist[0]:
                        self.focus = None
                        self.quit_btn.focus = True
                    else:
                        indx = btnlist.index(self.focus)
                        self.focus = btnlist[indx-1]
                else:
                    # button not recognised
                    continue

                # draw devices and buttons
                self.drawdevices()
                self.drawbuttons()
                self.devwin.noutrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()

        except asyncio.CancelledError:
            raise
        except Exception:
            return "Quit"


class MainScreen:

    def __init__(self, stdscr, consoleclient, devicename):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.consoleclient = consoleclient
        self.devicename = devicename
        self.client = consoleclient.client

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, curses.COLS, 0, 0)
        self.titlewin.addstr(0, 0, "Device: " + self.devicename, curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, curses.COLS, 2, 0)

        # self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")  # still to do
        self.screenparts = ("Groups", "Devices", "Messages", "Quit")

        # groups window (1 line, full row, starting at 4,0)
        self.groupswin = self.stdscr.subwin(1, curses.COLS, 4, 0)

        # groups list
        self.groups = []
        self.group_btns = widgets.Groups(self.stdscr, self.groupswin, self.consoleclient)


        # create a pad of 50 lines
        self.gpad = curses.newpad(50, curses.COLS)

        # bottom buttons, [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  curses.LINES - 1, 0)
        self.buttwin = self.stdscr.subwin(1, curses.COLS, curses.LINES - 1, 0)

        self.device = None
        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, curses.COLS//2 - 15)
        self.devices_btn.focus = True
        self.focus = "Devices"

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, curses.COLS//2 - 5)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, curses.COLS//2 + 6)

        self.line = 0


    @property
    def activegroup(self):
        return self.group_btns.active


    def show(self):
        "Displays device"

        if self.devicename not in self.client:
            widgets.drawmessage(self.messwin, f"{self.devicename} not found!")
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.titlewin.noutrefresh()
            self.messwin.noutrefresh()
            self.buttwin.noutrefresh()

            curses.doupdate()
            return

        self.device = self.client[self.devicename]
        if self.device.messages:
            widgets.drawmessage(self.messwin, self.device.messages[0])


        # get the groups this device contains, use a set to avoid duplicates
        groupset = {vector.group for vector in self.device.values()}
        self.groups = sorted(list(groupset))
        # populate a widget showing horizontal list of groups
        self.group_btns.set_groups(self.groups)
        self.group_btns.draw()

        # to do - draw the device vector widgets, as given by self.activegroup



        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        for y in range(0,50):
            for x in range(0, curses.COLS-1):
                if x == y:
                    self.gpad.addch(y,x, ord('a'))

        coords = (0, 0, 6, 1, curses.LINES - 3, curses.COLS-2)
                  # pad row, pad col,   win start row, win start col, win end row, win end col

        self.gpad.overlay(self.stdscr, *coords)
        self.gpad.noutrefresh(*coords)

        # draw the bottom buttons
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.groupswin.noutrefresh()
        self.buttwin.noutrefresh()

        curses.doupdate()


    def drawgpad(self, line=0):
        "draw the group pad"
        coords = (line, 0, 6, 1, curses.LINES - 3, curses.COLS-2)
                  # pad row, pad col,   win start row, win start col, win end row, win end col
        self.gpad.overwrite(self.stdscr, *coords)
        self.gpad.noutrefresh(*coords)
        curses.doupdate()


    def update(self, event):
        pass


# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"

        try:
            self.stdscr.nodelay(True)
            while (not self.consoleclient.stop) and (self.consoleclient.screen is self):
                await asyncio.sleep(0)
                if self.focus not in self.screenparts:
                    # as default, start with focus on the Devices button
                    self.devices_btn.focus = True
                    self.focus = "Devices"
                if self.focus == "Groups":
                    # focus has been given to the groups widget which monitors its own inputs
                    newgroup, key = await self.group_btns.input()
                    if key == 10:
                        # must update the screen with a new group
                        self.show()
                        continue
                    # if key != 10 just continue below with key checking for q, m etc.,
                else:
                    key = self.stdscr.getch()

                if key == -1:
                    continue

                if key == 10:
                    # enter key pressed
                    if self.focus == "Quit":
                        widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True)
                        self.messwin.noutrefresh()
                        curses.doupdate()
                    # return the focus value of whichever item was in focus when enter was pressed
                    return self.focus
                if chr(key) == "q" or chr(key) == "Q":
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"
                if chr(key) == "m" or chr(key) == "M":
                    return "Messages"
                if chr(key) == "d" or chr(key) == "D":
                    return "Devices"

                if chr(key) == "p":
                    self.line += 1
                    self.drawgpad(self.line)
                    continue


                if key in (32, 9, 261, 338, 258):
                    # go to the next widget
                    if self.focus == "Quit":
                        newfocus = "Groups"
                    else:
                        indx = self.screenparts.index(self.focus)
                        newfocus = self.screenparts[indx+1]
                elif key in (353, 260, 339, 259):
                    # go to previous button
                    if self.focus == "Groups":
                        newfocus = "Quit"
                    else:
                        indx = self.screenparts.index(self.focus)
                        newfocus = self.screenparts[indx-1]
                else:
                    # key not recognised
                    continue
                if self.focus == "Vectors":
                    # still to do
                    pass
                elif self.focus == "Groups":
                    self.group_btns.focus = False
                elif self.focus == "Devices":
                    self.devices_btn.focus = False
                elif self.focus == "Messages":
                    self.messages_btn.focus = False
                elif self.focus == "Quit":
                    self.quit_btn.focus = False
                if newfocus == "Vectors":
                    # still to do
                    pass
                elif newfocus == "Groups":
                    self.group_btns.focus = True
                elif newfocus == "Devices":
                    self.devices_btn.focus = True
                elif newfocus == "Messages":
                    self.messages_btn.focus = True
                elif newfocus == "Quit":
                    self.quit_btn.focus = True
                self.focus = newfocus

                # so buttons have been set with the appropriate focus
                # now draw them
                self.group_btns.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()

                self.groupswin.noutrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()
        except asyncio.CancelledError:
            raise
        except Exception:
            return "Quit"
