
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

        # self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")  # still to do
        self.screenparts = ("Groups", "Devices", "Messages", "Quit")

        # groups button window (1 line, full row, starting at 4,0)
        self.groupbuttonswin = self.stdscr.subwin(1, self.maxcols, 4, 0)

        # groups list
        self.groups = []
        self.group_btns = widgets.GroupButtons(self.stdscr, self.groupbuttonswin, self.consoleclient)


        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols-1, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.topmore_btn.show = True

        # window showing the vectors of the active group
        self.vectors = Vectors(self.stdscr, self.consoleclient)

        # botmorewin (1 line, full row, starting at self.maxrows - 3, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols-1, self.maxrows - 3, 0)
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.botmore_btn.show = True

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

        try:

            self.topmore_btn.draw()

            # Draw the device vector widgets, as given by self.activegroup
            self.vectors.draw(self.devicename, self.activegroup)

            self.botmore_btn.draw()

        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise


        # draw the bottom buttons
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.groupbuttonswin.noutrefresh()

        self.topmorewin.noutrefresh()
        self.vectors.refresh()
        self.botmorewin.noutrefresh()

        self.buttwin.noutrefresh()

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

                self.groupbuttonswin.noutrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()
        except asyncio.CancelledError:
            raise
        except Exception:
            return "Quit"


class Vectors:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.window = curses.newpad(50, self.maxcols)
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.padtop = 0
        self.groupname = None
        self.devicename = None
        self.device = None

    def refresh(self):

        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.padtop, 0, 8, 1, self.maxrows - 5, self.maxcols-2)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.window.overwrite(self.stdscr, *coords)
        self.window.noutrefresh(*coords)

    def draw(self, devicename, groupname):
        if (groupname == self.groupname) and (devicename == self.devicename):
            # no change
            return
        self.devicename = devicename
        self.device = self.client[devicename]
        self.groupname = groupname
        self.window.clear()

        try:

            for line in range(50):
                testchr = chr(97 + line)
                teststr = testchr*(self.maxcols-1)
                self.window.addstr(line, 0, teststr)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise


        # draw the vectors in the client with this device and group
        #line = 1
        #for name, vector in self.device.items():
            #if vector.group != self.groupname:
            #    continue
            ## so draw the vector widget
            #self.window.addstr(0, line, name)
            #line += 2
