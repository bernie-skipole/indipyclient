
import asyncio, curses, sys

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise




from . import widgets

from .. import events

class MessagesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.stdscr.clear()

        self.maxrows, self.maxcols = self.stdscr.getmaxyx()

        self.consoleclient = consoleclient
        self.client = consoleclient.client

        self.disconnectionflag = False

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "indipyclient console", curses.A_BOLD)

        # messages window (8 lines, full row - 4, starting at 4,3)
        self.messwin = self.stdscr.subwin(8, self.maxcols-4, 4, 3)

        # info window
        self.infowin = self.stdscr.subwin(4, 60, self.maxrows-6, self.maxcols//2 - 29)
        self.infowin.addstr(0, 14, "All Timestamps are UTC")
        self.infowin.addstr(1, 0, "Once connected, choose 'Devices' and press Enter. Then use")
        self.infowin.addstr(2, 0, "Tab/Shift-Tab to move between fields, Enter to select, and")
        self.infowin.addstr(3, 0, "Arrow/Page keys to show further fields where necessary.")

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10)
        self.devices_btn.focus = False
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2)
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
            traceback.print_exc(file=sys.stderr)
            return "Quit"


class DevicesScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.stdscr.clear()

        self.maxrows, self.maxcols = self.stdscr.getmaxyx()

        self.consoleclient = consoleclient
        self.client = consoleclient.client

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Devices", curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)

        # status window (1 line, full row-4, starting at 4,4)
        self.statwin = self.stdscr.subwin(1, self.maxcols-4, 4, 4)

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.topmore_btn.show = False

        # devices window - create a pad of 40+2*devices lines, full row
        self.devwin = curses.newpad(40 + 2* len(self.client), self.maxcols)

        # devices window top and bottom row numbers
        self.devwintop = 8
        # ensure bottom row is an even number at position self.maxrows - 6 or -7
        row = self.maxrows - 7
        # very large screen may produce a window bigger that the pad,
        # so reduce it to around ten times less than the pad
        if row > 30 + 2* len(self.client):
            row = 30 + 2* len(self.client)
        self.devwinbot = row + row % 2

        # topline of pad to show
        self.topline = 0

        # botmorewin (1 line, full row, starting at self.maxrows - 4, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 4, 0)
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.botmore_btn.show = False

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        # this holds the messages and quit buttons
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 10)
        self.messages_btn.focus = True
        self.focus = None
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2)
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

        # draw device buttons, and if necessary the 'more' buttons
        self.drawdevices()

        # draw messages and quit buttons
        self.drawbuttons()

        # refresh these sub-windows and update physical screen

        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.statwin.noutrefresh()
        self.devwinrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()


    def devwinrefresh(self):

        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.topline, 0, self.devwintop, 0, self.devwinbot, self.maxcols-1)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.devwin.overwrite(self.stdscr, *coords)

        self.topmorewin.noutrefresh()
        self.devwin.noutrefresh(*coords)
        self.botmorewin.noutrefresh()


    @property
    def botline(self):
        "Returns the bottom line of the pad to be displayed"

        return self.topline + self.devwinbot - self.devwintop

    #    self.devwintop = 8
    #    self.devwinbot = self.maxrows - 7 or - 6


    # ex1: self.topline = 0, self.maxrows = 30
    # self.devwinbot = 24
    # botline = 0 + 24 - 8 = 16

    # ex2: self.topline = 0, self.maxrows = 31
    # self.devwinbot = 24
    # botline = 0 + 24 - 8 = 16

    # ex3: topline = 0, self.maxrows = 32
    # self.devwinbot = 26
    # botline = 0 + 26 - 8 = 18

    # ex4: self.topline = 2, self.maxrows = 15
    # self.devwinbot = 8
    # botline = 2 + 8 - 8 = 2

    # ex5: self.topline = 2, self.maxrows = 16
    # self.devwinbot = 10
    # botline = 2 + 10 - 8 = 4

    # ex6: self.topline = 2, self.maxrows = 17
    # self.devwinbot = 10
    # botline = 2 + 10 - 8 = 4


    @property
    def topdevice(self):
        "Returns the index of the top device being displayed"
        return self.topline//2

    @property
    def bottomdevice(self):
        "Returns the index of the bottom device being displayed"
        idx_of_last_device = len(self.client) - 1

        last_displayed = self.botline//2

        if idx_of_last_device > last_displayed:
            return last_displayed
        return idx_of_last_device


    def drawdevices(self):
        self.topmorewin.clear()
        self.devwin.clear()
        self.botmorewin.clear()

        if not len(self.client):
            self.focus = None
            self.topmore_btn.show = False
            self.botmore_btn.show = False
            self.topmore_btn.focus = False
            self.botmore_btn.focus = False
            return

        # Remove current devices
        self.devices.clear()

        colnumber = self.maxcols//2 - 6
        for linenumber, devicename in enumerate(self.client):
            self.devices[devicename.lower()] = widgets.Button(self.devwin, devicename, linenumber*2, colnumber)

        # start with all device buttons focus False
        for devbutton in self.devices.values():
            devbutton.focus = False

        if self.focus not in self.devices:
            self.focus = None
        else:
            self.devices[self.focus].focus = True

        # if self.topdevice is not zero, then draw top more button
        if self.topdevice:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
            self.topmore_btn.focus = False
        self.topmore_btn.draw()

        # draw devices buttons
        for devbutton in self.devices.values():
            devbutton.draw()

        number_of_devices = len(self.client)
        # each device takes 2 lines
        if self.bottomdevice < number_of_devices -1:
            self.botmore_btn.show = True
        else:
            self.botmore_btn.show = False
            self.botmore_btn.focus = False
        self.botmore_btn.draw()



    def drawbuttons(self):
        self.buttwin.clear()

        # If a device is in focus, these buttons are not
        if self.focus or self.topmore_btn.focus or self.botmore_btn.focus:
            self.messages_btn.focus = False
            self.quit_btn.focus = False
        elif not self.quit_btn.focus:
            self.messages_btn.focus = True
        elif not self.messages_btn.focus:
            self.quit_btn.focus = True

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
            self.devwinrefresh()
            self.buttwin.noutrefresh()
            curses.doupdate()
            return
        if event.devicename is not None:
            if event.devicename.lower() not in self.devices:
                # unknown device, check this is a definition
                if isinstance(event, events.defVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwinrefresh()
                    curses.doupdate()
                elif isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwinrefresh()
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
                    if self.topmore_btn.focus:
                        # pressing topmore button may cause first device to be displayed
                        # which results in the topmore button vanishing
                        if self.topdevice == 1:
                            self.topmore_btn.focus = False
                            self.focus = btnlist[0]
                        self.topline -= 2
                        self.drawdevices()
                        self.devwinrefresh()
                        curses.doupdate()
                        continue
                    if self.botmore_btn.focus:
                        # pressing botmore button may cause last device to be displayed
                        # which results in the botmore button vanishing
                        if self.bottomdevice == len(self.client) - 2:
                            self.botmore_btn.focus = False
                            self.focus = btnlist[-1]
                        self.topline += 2
                        self.drawdevices()
                        self.devwinrefresh()
                        curses.doupdate()
                        continue

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
                        if self.topdevice:
                            # that is, if topdevice does not have index zero
                            self.topmore_btn.focus = True
                        else:
                            self.focus = btnlist[0]
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        self.quit_btn.focus = True
                    elif self.topmore_btn.focus:
                        self.topmore_btn.focus = False
                        self.focus = btnlist[self.topdevice]
                    elif self.botmore_btn.focus:
                        self.botmore_btn.focus = False
                        self.messages_btn.focus = True
                    else:
                        # one of the devices has focus
                        indx = btnlist.index(self.focus)
                        if indx == len(self.client) - 1:
                            # very last device, the botmore_btn should not be shown
                            self.focus = None
                            self.messages_btn.focus = True
                        elif indx == self.bottomdevice:
                            if key in (338, 258):      # 338 page down, 258 down arrow
                                # display next device
                                self.topline += 2
                                self.focus = btnlist[indx+1]
                            else:
                                # last device on display
                                self.focus = None
                                self.botmore_btn.focus = True
                        else:
                            self.focus = btnlist[indx+1]

                elif key in (353, 260, 339, 259):
                    # go to previous button
                    if self.quit_btn.focus:
                        self.quit_btn.focus = False
                        self.messages_btn.focus = True
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        if self.botmore_btn.show:
                            self.botmore_btn.focus = True
                        else:
                            self.focus = btnlist[-1]
                    elif self.botmore_btn.focus:
                        self.botmore_btn.focus = False
                        self.focus = btnlist[self.bottomdevice]
                    elif self.topmore_btn.focus:
                        self.topmore_btn.focus = False
                        self.quit_btn.focus = True
                    elif self.focus == btnlist[0]:
                        self.focus = None
                        self.quit_btn.focus = True
                    else:
                        indx = btnlist.index(self.focus)
                        if indx == self.topdevice:
                            if key in (339, 259): # 339 page up, 259 up arrow
                                self.topline -= 2
                                self.focus = btnlist[indx-1]
                            else:
                                self.focus = None
                                self.topmore_btn.focus = True
                        else:
                            self.focus = btnlist[indx-1]

                else:
                    # button not recognised
                    continue

                # draw devices and buttons
                self.drawdevices()
                self.drawbuttons()
                self.devwinrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


class MainScreen:

    def __init__(self, stdscr, consoleclient, devicename):
        self.stdscr = stdscr
        self.stdscr.clear()

        self.maxrows, self.maxcols = self.stdscr.getmaxyx()

        self.consoleclient = consoleclient
        self.devicename = devicename
        self.client = consoleclient.client

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Device: " + self.devicename, curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)

        # list areas of the screen, one of these areas as the current 'focus'
        # Groups being the horizontal line of group names associated with a device
        # Vectors being the area showing the vectors associated with a device and group
        # and Devices Messages and Quit are the bottom buttons
        self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")

        # groups list
        try:
            self.groups = []
            self.group_btns = GroupButtons(self.stdscr, self.consoleclient)

            # window showing the vectors of the active group
            self.vectors = VectorListWin(self.stdscr, self.consoleclient)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # bottom buttons, [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.device = None
        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 15)
        self.devices_btn.focus = True
        self.focus = "Devices"

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 5)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 6)


    @property
    def activegroup(self):
        "Return name of group currently active"
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

        # Draw the device vector widgets, as given by self.activegroup
        self.vectors.draw(self.devicename, self.activegroup)

        # draw the bottom buttons
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.group_btns.noutrefresh()

        self.vectors.noutrefresh()

        self.buttwin.noutrefresh()

        curses.doupdate()




    def update(self, event):
        pass


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
                    key = await self.group_btns.input()
                    if key == 10:
                        # must update the screen with a new group
                        self.show()
                        continue
                elif self.focus == "Vectors":
                    # focus has been given to Vectors which monitors its own inputs
                    key = await self.vectors.input()
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
                    self.vectors.focus = False
                elif self.focus == "Groups":
                    self.group_btns.focus = False
                elif self.focus == "Devices":
                    self.devices_btn.focus = False
                elif self.focus == "Messages":
                    self.messages_btn.focus = False
                elif self.focus == "Quit":
                    self.quit_btn.focus = False
                if newfocus == "Vectors":
                    if self.focus == "Groups":
                        self.vectors.set_top_focus()
                    else:
                        self.vectors.set_bot_focus()
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
                self.vectors.draw(self.devicename, self.group_btns.active)
                self.group_btns.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()

                self.vectors.noutrefresh()
                self.group_btns.noutrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"



class GroupButtons:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr

        self.maxrows, self.maxcols = self.stdscr.getmaxyx()

        # window (1 line, full row, starting at 4,0)
        self.window = self.stdscr.subwin(1, self.maxcols, 4, 0)
        self.consoleclient = consoleclient
        self.groups = []          # list of group names
        self.groupcols = {}       # dictionary of groupname to column number
        # active is the name of the group currently being shown
        self.active = None
        # this is True, if this widget is in focus
        self._focus = False
        # this is set to the group in focus, if any
        self.groupfocus = None

        # the horizontal display of group buttons may not hold all the buttons
        # give the index of self.groups from and to
        self.fromgroup = 0
        self.togroup = 0
        self.nextcol = 0
        self.nextfocus = False
        self.prevfocus = False


    def noutrefresh(self):
        self.window.noutrefresh()


    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        self._focus = value
        if value:
            self.groupfocus = self.groups[self.fromgroup]
        else:
            self.groupfocus = None
            self.nextfocus = False
            self.prevfocus = False


    def set_groups(self, groups):
        self.groups = groups.copy()
        self.groupcols.clear()
        if self.groupfocus:
            if self.groupfocus not in self.groups:
                self.groupfocus = None
                self.nextfocus = False
                self.prevfocus = False
        if self.active is None:
            self.active = self.groups[0]
        elif self.active not in self.groups:
            self.active = self.groups[0]


    def draw(self):
        "Draw the line of groups"
        self.groupcols.clear()
        if self.active is None:
            self.active = self.groups[0]
        # clear the line
        self.window.clear()

        # draw 'Prev' button if necessary
        if self.fromgroup:
            self.drawprev(self.prevfocus)
            col = 11
        else:
            col = 2

        for indx, group in enumerate(self.groups):
            if indx < self.fromgroup:
                continue
            self.groupcols[group] = col

            # is this the last?
            if group == self.groups[-1]:
                self.togroup = indx
                if self.nextfocus:
                    self.nextfocus = False
                    self.groupfocus = group

            col = self.drawgroup(group)

            # If not the last, check if another can be drawn
            # otherwise print the 'Next' button
            if (group != self.groups[-1]) and (col+20 >= curses.COLS):
                self.nextcol = col
                self.drawnext(self.nextfocus)
                self.togroup = indx
                break


    def drawgroup(self, group):
        # draw the group, return col position of next group to be shown
        grouptoshow = "["+group+"]"
        col = self.groupcols[group]
        if group == self.active:
            if self.groupfocus == group:
                # group in focus
                self.window.addstr(0, col, grouptoshow, curses.A_REVERSE)
            else:
                # active item
                self.window.addstr(0, col, grouptoshow, curses.A_BOLD)
        else:
            if self.groupfocus == group:
                # group in focus
                self.window.addstr(0, col, grouptoshow, curses.A_REVERSE)
            else:
                self.window.addstr(0, col, grouptoshow)
        col += (len(grouptoshow) + 2)
        return col


    def drawprev(self, focus=False):
        if focus:
            self.window.addstr(0, 2, "<<Prev]", curses.A_REVERSE)
            # set focus on prev button
            self.prevfocus = True
            # remove focus from group
            self.groupfocus = None
        else:
            self.window.addstr(0, 2, "<<Prev]")
            self.prevfocus = False


    def drawnext(self, focus=False):
        if focus:
            # remove focus from group
            self.groupfocus = None
            self.drawgroup(self.groups[self.togroup])
            # set focus on next button
            self.nextfocus = True
            self.window.addstr(0, self.nextcol, "[Next>>", curses.A_REVERSE)
        else:
            self.window.addstr(0, self.nextcol, "[Next>>")
            self.nextfocus = False


    async def input(self):
        "Get group button pressed, or next or previous"
        self.stdscr.nodelay(True)
        while not self.consoleclient.stop:
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key == 10:

                if self.prevfocus:
                    # Enter has been pressed when the 'Prev' button has focus
                    self.fromgroup = self.fromgroup - 1
                    if not self.fromgroup:
                        # self.fromgroup is zero, so no prev button
                        self.prevfocus = False
                        self.groupfocus = self.groups[0]
                    self.draw()
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue

                if self.nextfocus:
                    # Enter has been pressed when the 'Next' button has
                    # focus
                    if self.fromgroup:
                        self.fromgroup = self.fromgroup + 1
                    else:
                        self.fromgroup = 2
                    self.draw()
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue

                # set this groupfocus button as the active button,
                # and return its value
                if self.active == self.groupfocus:
                    # no change
                    continue
                # set a change of the active group
                self.active = self.groupfocus
                return 10
            if chr(key) in ("q", "Q", "m", "M", "d", "D"):
                return key
            if key in (32, 9, 261):   # space, tab, right arrow
                if self.prevfocus:
                    # remove focus from prev button
                    self.drawprev()
                    # set focus on from button
                    self.groupfocus = self.groups[self.fromgroup]
                    self.drawgroup(self.groupfocus)
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue
                if self.nextfocus:
                    return 258   # treat as 258 down arrow key
                # go to the next group
                if self.groupfocus == self.groups[-1]:
                    # At the last group, cannot go further
                    return key
                indx = self.groups.index(self.groupfocus)
                if self.togroup and (indx+1 > self.togroup):
                    # next choice is beyond togroup
                    if key == 261:   # right arrow
                        if self.fromgroup:
                            self.fromgroup = self.fromgroup + 1
                        else:
                            self.fromgroup = 2
                        # get the new group in focus
                        self.groupfocus = self.groups[indx+1]
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue
                    else:
                        # so highlight 'next' key
                        self.drawnext(focus=True)
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue
                # get the new group in focus
                self.groupfocus = self.groups[indx+1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                continue
            if key in (353, 260):   # 353 shift tab, 260 left arrow
                if self.prevfocus:
                    # remove focus from the button
                    self.drawprev(focus=False)
                    return 258   # treat as 258 down arrow key
                if self.nextfocus:
                    # group to the left of the 'Next' button, now has focus
                    self.groupfocus = self.groups[self.togroup]
                    self.drawgroup(self.groups[self.togroup])
                    # remove focus from next button
                    self.drawnext(focus=False)
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue
                # go to the previous group
                indx = self.groups.index(self.groupfocus)
                if not indx:
                    # indx zero means first group
                    return key
                if indx == self.fromgroup:
                    if key == 260:  # left arrow, moves to previous group
                        self.fromgroup = self.fromgroup - 1
                        if not self.fromgroup:
                            # self.fromgroup is zero, so no prev button
                            self.prevfocus = False
                            self.groupfocus = self.groups[0]
                        else:
                            # get the new group in focus
                            self.groupfocus = self.groups[indx-1]
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue
                    else:
                        # the button to the left must be the 'Prev' button
                        # remove focus from current button
                        currentgroup = self.groupfocus
                        self.groupfocus = None
                        self.drawgroup(currentgroup)
                        # set Prev button as the focus
                        self.drawprev(focus=True)
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue

                self.groupfocus = self.groups[indx-1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                continue
            if key in (338, 339, 258, 259):          # 338 page down, 339 page up, 258 down arrow, 259 up arrow
                return key
        return -1




class VectorListWin:

    "Used to display a list of vectors"

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.window = curses.newpad(50, self.maxcols)
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.padtop = 0        # vector index number of top vector being displayed
        self.groupname = None
        self.devicename = None
        self.device = None

        # this is True, if this widget is in focus
        self._focus = False

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols-1, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.topmore_btn.show = False
        self.topmore_btn.focus = False

        # botmorewin (1 line, full row, starting at self.maxrows - 3, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols-1, self.maxrows - 3, 0)
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.botmore_btn.show = False
        self.botmore_btn.focus = False

        self.displaylines = self.maxrows - 5 - 8

        # list of vectors associated with this group
        self.vectors = []

        # list of vector buttons
        self.vector_btns = []


    @property
    def padbot(self):
        "vector index number of bottom vector being displayed"
        return self.padtop + self.displaylines//2


    @property
    def lastvectorindex(self):
        "index number of last vector"
        return len(self.vectors) - 1


    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        if not value:
            self.leave_focus()
            return
        #return
        self._focus = True
        self.botmore_btn.draw()
        self.topmore_btn.draw()
        self.botmorewin.noutrefresh()
        self.topmorewin.noutrefresh()
        curses.doupdate()


    def leave_focus(self):
        "Equivalent to setting focus False"
        self._focus = False
        self.topmore_btn.focus = False
        self.botmore_btn.focus = False
        for btn in self.vector_btns:
            if btn.focus:
                btn.focus = False
                btn.draw()
        self.botmore_btn.draw()
        self.topmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def set_top_focus(self):
        if self._focus and self.topmore_btn.focus:
            # no change
            return
        self._focus = True
        if self.padtop:
            # give top button focus
            self.topmore_btn.show = True
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
            # ensure vectors do not have focus
            for btn in self.vector_btns:
                if btn.focus:
                    btn.focus = False
                    btn.draw()
        else:
            # give first vector focus
            first = True
            for btn in self.vector_btns:
                if first:
                    btn.focus = True
                    btn.draw()
                    first = False
                elif btn.focus:
                    btn.focus = False
                    btn.draw()

        self.botmore_btn.focus = False
        self.botmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def set_bot_focus(self):
        if self._focus and self.botmore_btn.focus:
            # no change
            return
        self._focus = True
        self.topmore_btn.focus = False
        self.topmore_btn.draw()
        if self.botmore_btn.show:
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
            for btn in self.vector_btns:
                if btn.focus:
                    btn.focus = False
                    btn.draw()
        else:
            # set the last vector in focus
            for index, btn in enumerate(self.vector_btns):
                if index == self.lastvectorindex:
                    btn.focus = True
                    btn.draw()
                elif btn.focus:
                    btn.focus = False
                    btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def draw(self, devicename, groupname):
        if (groupname == self.groupname) and (devicename == self.devicename):
            # no change
            return
        self.devicename = devicename
        self.device = self.client[devicename]
        self.groupname = groupname
        self.window.clear()
        self.topmorewin.clear()
        self.botmorewin.clear()

        self.topmore_btn.show = bool(self.padtop)
        self.topmore_btn.draw()

        try:

            # draw the vectors in the client with this device and group

            vectorlist = [vector for vector in self.device.values() if vector.group == self.groupname]

            self.vectors = sorted(vectorlist, key=lambda x: x.name)

            # so draw the vector widget, name, label, state, with names as buttons

            self.vector_btns = []

            line = 0

            for v in self.vectors:
                # shorten the name and set it as a button
                nm = v.name[:17] + "..." if len(v.name) > 20 else v.name
                self.vector_btns.append( widgets.Button(self.window, nm, line, 1) )  # the name as a button
                self.vector_btns[-1].draw()

                lb = v.label[:27] + "..." if len(v.label) > 30 else v.label
                self.window.addstr(line, 30, lb)  # the shortenned label

                self.window.addstr(line, 70, v.state)
                line += 2


            if self.padbot >= self.lastvectorindex:
                self.botmore_btn.show = False
            else:
                self.botmore_btn.show = True
            self.botmore_btn.draw()

        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise


    def noutrefresh(self):

        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.padtop*2, 0, 8, 1, self.displaylines + 8, self.maxcols-2)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.topmorewin.noutrefresh()
        self.window.overwrite(self.stdscr, *coords)
        self.window.noutrefresh(*coords)
        self.botmorewin.noutrefresh()


    def upline(self):
        if not self.padtop:
            # already at top
            return
        self.padtop -= 1
        if not self.padtop:
            # at the top vectors
            self.topmore_btn.show = False
            self.topmore_btn.draw()
            btn = self.vector_btns[0]
            btn.focus = True
            btn.draw()
        if (not self.botmore_btn.show) and (self.padbot < self.lastvectorindex):
            self.botmore_btn.show = True
            self.botmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def downline(self):
        if self.padbot >= self.lastvectorindex:
            # already at the bottom
            return
        self.padtop += 1
        if not self.topmore_btn.show:
            self.topmore_btn.show = True
            self.topmore_btn.draw()
        if self.padbot >= self.lastvectorindex:
            self.botmore_btn.show = False
            self.botmore_btn.draw()
            btn = self.vector_btns[-1]
            btn.focus = True
            btn.draw()
        self.noutrefresh()
        curses.doupdate()



    async def input(self):
        "Get key pressed while this object has focus"
        self.stdscr.nodelay(True)
        while not self.consoleclient.stop:
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow


            if key == 10:
                if self.topmore_btn.focus:
                    self.upline()
                elif self.botmore_btn.focus:
                    self.downline()
            elif key in (32, 9, 261, 338, 258):
                # go to the next
                if self.botmore_btn.focus:
                    self.focus = False
                    return key
                elif self.topmore_btn.focus:
                    # set focus on top vector
                    self.topmore_btn.focus = False
                    btn = self.vector_btns[self.padtop]
                    btn.focus = True
                    self.topmore_btn.draw()
                    btn.draw()
                    self.noutrefresh()
                    curses.doupdate()
                else:
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    if btnindex >= self.padbot:
                        if self.botmore_btn.show:
                            self.set_bot_focus()
                        else:
                            # At the last vector
                            self.focus = False
                            return key
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex+1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex+1].draw()
                        self.noutrefresh()
                        curses.doupdate()


            elif key in (353, 260, 339, 259):
                # go to the previous
                if self.topmore_btn.focus:
                    self.focus = False
                    return key
                elif self.botmore_btn.focus:
                    # set focus on bottom vector
                    self.botmore_btn.focus = False
                    btn = self.vector_btns[self.padbot]
                    btn.focus = True
                    self.botmore_btn.draw()
                    btn.draw()
                    self.noutrefresh()
                    curses.doupdate()
                else:
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    if not btnindex:
                        # At the top vector
                        self.focus = False
                        return key
                    if btnindex == self.padtop:
                        self.set_top_focus()
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex-1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex-1].draw()
                        self.noutrefresh()
                        curses.doupdate()

        return -1
