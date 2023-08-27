
import asyncio, curses

from . import widgets

class MessagesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.devices_btn = widgets.Button(stdscr, "Devices", curses.LINES - 1, curses.COLS//2 - 10)
        self.devices_btn.focus = False
        self.quit_btn = widgets.Button(stdscr, "Quit", curses.LINES - 1, curses.COLS//2 + 2)
        self.quit_btn.focus = True

    @property
    def connected(self):
        return self.consoleclient.connected

    def show(self, client):
        "Displays title, info string and list of messages on a start screen"
        messages = client.messages
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "indipyclient console", curses.A_BOLD)
        if self.connected:
            self.stdscr.addstr(2, 0, "Connected")
        else:
            self.stdscr.addstr(2, 0, "Not Connected")
            self.devices_btn.focus = False
            self.quit_btn.focus = True
        lastmessagenumber = len(messages) - 1
        if curses.COLS < 80:
            margin = 1
            mlist = [ t.isoformat(sep='T')[11:19] + "  " + m for t,m in messages ]
        else:
            margin = 4
            mlist = [ t.isoformat(sep='T')[11:21] + "  " + m for t,m in messages ]
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
        except Exception:
            return "Quit"


class DevicesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.messages_btn = widgets.Button(stdscr, "Messages", curses.LINES - 1, curses.COLS//2 - 10)
        self.messages_btn.focus = True
        self.focus = "Messages"
        self.quit_btn = widgets.Button(stdscr, "Quit", curses.LINES - 1, curses.COLS//2 + 2)
        # devicename to button dictionary
        self.devices = {}


    def show(self, client):
        "Displays list of devices"
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Devices", curses.A_BOLD)
        message = client.messages[-1][0].isoformat(sep='T')[11:21] + "  " + client.messages[-1][1]
        self.stdscr.addstr(2, 4, message)
        if not len(client):
            self.stdscr.addstr(4, 4, "No devices have been discovered")
        else:
            self.stdscr.addstr(4, 4, "Choose a device:")
        # Remove current devices
        self.devices.clear()
        linenumber = 5
        colnumber = 4
        for devicename in client:
            linenumber += 1
            self.devices[devicename.lower()] = widgets.Button(self.stdscr, devicename, linenumber, colnumber)
            if self.focus == devicename.lower():
                self.devices[devicename.lower()].focus = True
            self.devices[devicename.lower()].draw()
        self.devices["Messages"] = self.messages_btn
        self.devices["Quit"] = self.quit_btn
        self.messages_btn.draw()
        self.quit_btn.draw()
        self.stdscr.refresh()


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
                        self.stdscr.addstr(2, 4, "Quit chosen ... Please wait" + " "*(curses.COLS - 31), curses.A_BOLD)
                        self.stdscr.refresh()
                    return self.focus
                if chr(key) == "q" or chr(key) == "Q":
                    self.stdscr.addstr(2, 4, "Quit chosen ... Please wait" + " "*(curses.COLS - 31), curses.A_BOLD)
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

        except Exception:
            return "Quit"