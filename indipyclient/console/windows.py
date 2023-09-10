
import asyncio, curses, sys

from . import widgets

from .. import events

class MessagesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.devices_btn = widgets.Button(stdscr, "Devices", curses.LINES - 1, curses.COLS//2 - 10)
        self.devices_btn.focus = False
        self.quit_btn = widgets.Button(stdscr, "Quit", curses.LINES - 1, curses.COLS//2 + 2)
        self.quit_btn.focus = True

    @property
    def connected(self):
        return self.consoleclient.connected

    def show(self):
        "Displays title, info string and list of messages on a start screen"
        messages = self.client.messages
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "indipyclient console", curses.A_BOLD)
        if self.connected:
            self.stdscr.addstr(2, 0, "Connected")
        else:
            self.stdscr.addstr(2, 0, "Not Connected")
            self.devices_btn.focus = False
            self.quit_btn.focus = True
        lastmessagenumber = len(messages) - 1
        margin = 4
        mlist = reversed([ t.isoformat(sep='T')[11:21] + "  " + m for t,m in messages ])
        for count, message in enumerate(mlist):
            if count == lastmessagenumber:
                # high light the last, current message
                self.stdscr.addstr(4+count, margin, message, curses.A_BOLD)
            else:
                self.stdscr.addstr(4+count, margin, message)
        # put [Devices] [Quit] buttons on screen
        info1txt = "Use Tab, Space or arrows to "
        info2txt = "highlight a button and press Enter"
        if len(info1txt)+len(info2txt)+6 > curses.COLS:
            # text too long, split into two lines
            self.stdscr.addstr(curses.LINES - 4, (curses.COLS - len(info1txt))//2, info1txt)
            self.stdscr.addstr(curses.LINES - 3, (curses.COLS - len(info2txt))//2, info2txt)
        else:
            infotext = info1txt + info2txt
            col = (curses.COLS - len(infotext))//2
            self.stdscr.addstr(curses.LINES - 3, col, infotext)
        self.devices_btn.draw()
        self.quit_btn.draw()
        self.stdscr.refresh()


    def update(self, event):
        "Only update if message has changed"
        if isinstance(event, events.Message):
            self.show()


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
                    self.devices_btn.draw()
                    self.quit_btn.draw()
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
                    self.devices_btn.draw()
                    self.quit_btn.draw()
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
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.messages_btn = widgets.Button(stdscr, "Messages", curses.LINES - 1, curses.COLS//2 - 10)
        self.messages_btn.focus = True
        self.focus = "Messages"
        self.quit_btn = widgets.Button(stdscr, "Quit", curses.LINES - 1, curses.COLS//2 + 2)
        # devicename to button dictionary
        self.devices = {}

    def show(self):
        "Displays the screen with list of devices"
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Devices", curses.A_BOLD)
        widgets.drawmessage(self.stdscr, self.client.messages[0])
        if not len(self.client):
            self.stdscr.addstr(4, 4, "No devices have been discovered")
        else:
            self.stdscr.addstr(4, 4, "Choose a device:")
        # Remove current devices
        self.devices.clear()
        linenumber = 5
        colnumber = curses.COLS//2 - 6
        for devicename in self.client:
            linenumber += 1
            self.devices[devicename.lower()] = widgets.Button(self.stdscr, devicename, linenumber, colnumber)
        self.devices["Messages"] = self.messages_btn
        self.devices["Quit"] = self.quit_btn
        if self.focus in self.devices:
            self.devices[self.focus].focus = True
        else:
            # self.focus points at a device which has been removed, so set focus to messages
            self.messages_btn.focus = True
        for devicewidget in self.devices.values():
            devicewidget.draw()
        self.stdscr.refresh()


    def update(self, event):
        "Only update if global message has changed, or a new device added or deleted"
        if isinstance(event, events.Message) and event.devicename is None:
            widgets.drawmessage(self.stdscr, self.client.messages[0])
            self.stdscr.refresh()
            return
        # check devices unchanged
        if isinstance(event, events.delProperty) and event.vectorname is None:
            # a device has being deleted
            self.show()
            return
        if event.devicename is not None:
            if event.devicename.lower() not in self.devices:
                # unknown device, check this is a definition
                if isinstance(event, events.defVector):
                    # could be a new device
                    self.show()
                elif isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.show()



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
                if self.focus not in btnlist:
                    self.messages_btn.focus = True
                    self.focus = "Messages"
                if key == 10:
                    if self.focus == "Quit":
                        widgets.drawmessage(self.stdscr, "Quit chosen ... Please wait", bold = True)
                        self.stdscr.refresh()
                    return self.focus
                if chr(key) == "q" or chr(key) == "Q":
                    widgets.drawmessage(self.stdscr, "Quit chosen ... Please wait", bold = True)
                    self.stdscr.refresh()
                    return "Quit"
                if chr(key) == "m" or chr(key) == "M":
                    return "Messages"

                if key in (32, 9, 261, 338, 258):
                    # go to the next button
                    if self.focus == "Quit":
                        newfocus = btnlist[0]
                    else:
                        indx = btnlist.index(self.focus)
                        newfocus = btnlist[indx+1]
                elif key in (353, 260, 339, 259):
                    # go to previous button
                    if self.focus == btnlist[0]:
                        newfocus = "Quit"
                    else:
                        indx = btnlist.index(self.focus)
                        newfocus = btnlist[indx-1]
                else:
                    # button not recognised
                    continue

                self.devices[self.focus].focus = False
                self.devices[newfocus].focus = True
                self.focus = newfocus
                for btn in self.devices.values():
                    btn.draw()
                self.stdscr.refresh()

        except asyncio.CancelledError:
            raise
        except Exception:
            return "Quit"


class MainScreen:

    def __init__(self, stdscr, consoleclient, devicename):
        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.devicename = devicename
        self.client = consoleclient.client

        # self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")  # still to do
        self.screenparts = ("Groups", "Devices", "Messages", "Quit")

        # groups list
        self.groups = []
        self.group_btns = widgets.Groups(self.stdscr, self.consoleclient)

        # bottom buttons, [Devices] [Messages] [Quit]
        self.device = None
        self.devices_btn = widgets.Button(stdscr, "Devices", curses.LINES - 1, curses.COLS//2 - 15)
        self.devices_btn.focus = True
        self.focus = "Devices"

        self.messages_btn = widgets.Button(stdscr, "Messages", curses.LINES - 1, curses.COLS//2 - 5)
        self.quit_btn = widgets.Button(stdscr, "Quit", curses.LINES - 1, curses.COLS//2 + 6)

        # widgets showing vectors
        self.vectorwidgets = {}


    @property
    def activegroup(self):
        return self.group_btns.active


    def show(self):
        "Displays device"
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Device: "+self.devicename, curses.A_BOLD)
        self.vectorwidgets.clear()
        if self.devicename not in self.client:
            widgets.drawmessage(self.stdscr, f"{self.devicename} not found!")
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()
            self.stdscr.refresh()
            return
        self.device = self.client[self.devicename]
        if self.device.messages:
            widgets.drawmessage(self.stdscr, self.device.messages[0])
        # get the groups this device contains, use a set to avoid duplicates
        groupset = {vector.group for vector in self.device.values()}
        self.groups = sorted(list(groupset))
        # populate a widget showing horizontal list of groups
        self.group_btns.set_groups(self.groups)
        self.group_btns.draw()

        # to do - draw the device vectorwidgets, as given by self.activegroup

        # draw the bottom buttons and refresh
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()
        self.stdscr.refresh()


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
                        widgets.drawmessage(self.stdscr, "Quit chosen ... Please wait", bold = True)
                        self.stdscr.refresh()
                    # return the focus value of whichever item was in focus when enter was pressed
                    return self.focus
                if chr(key) == "q" or chr(key) == "Q":
                    widgets.drawmessage(self.stdscr, "Quit chosen ... Please wait", bold = True)
                    self.stdscr.refresh()
                    return "Quit"
                if chr(key) == "m" or chr(key) == "M":
                    return "Messages"
                if chr(key) == "d" or chr(key) == "D":
                    return "Devices"
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
                    # field not recognised
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
                self.stdscr.refresh()
        except asyncio.CancelledError:
            raise
        except Exception:
            return "Quit"
