"""This displays the screen showing a list of devices, allowing one to be chosen"""


import asyncio, curses

from . import widgets

from .windows import ParentScreen

from .. import events


class DevicesScreen(ParentScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)
        self.stdscr.clear()
        curses.flushinp()

        # example - if screen 80 x 24                                      # row 0 to 23
        # then self.maxrows will be 24   set in ParentScreen

        # title window  (1 line, full row of columns, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)    # row 0
        self.titlewin.addstr(0, 0, "Devices", curses.A_BOLD)
                                                                     # row 1 empty
        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)     # row 2

        # status window (1 line, full row-4, starting at 4,4)
        self.statwin = self.stdscr.subwin(1, self.maxcols-4, 4, 4)   # row 4

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, 6, 0) # row 6
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="TopMore")
        self.topmore_btn.show = False

        # devices window                                            # row 7 blank between more and top device

        # calculate top and bottom row numbers
        self.devwintop = 8                                                          # row 8
        # ensure bottom row is an odd number at position self.maxrows - 4 or -5
        row = self.maxrows - 4             # 19
        self.devwinbot = row - row % 2   # Subtracts 1 if row is even                     # row 19 (leaving rows 20-23)

        # for 24 row window
        # device window will have row 8 to row 19, displaying 6 devices, (self.devwinbot-self.devwintop+1) // 2  = 6

        # device window                          19 - 8 + 1 = 12 rows       80            row 8      left col
        self.devwin = self.stdscr.subwin(self.devwinbot-self.devwintop+1, self.maxcols, self.devwintop, 0)

        # topindex of device being shown
        self.topindex = 0                   # so six devices will show devices with indexes 0-5

        # botmorewin (1 line, full row, starting at self.maxrows - 4, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 4, 0)      # row 20
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="BotMore")
        self.botmore_btn.show = False
                                                                                    # rows 21, 22 blank
        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        # this holds the messages and quit buttons
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)     # row 23

        # self.focus will be the name of a device in focus
        self.focus = None

        # Start with the messages_btn in focus
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 10, onclick="Messages")
        self.messages_btn.focus = True

        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2, onclick="Quit")

        # devicename to devices
        self.devices = {}
        # devicename to buttons
        self.devbuttons = {}             # devicenames are original case

    @property
    def devicename(self):
        return self.focus


    def show(self):
        "Displays the screen with list of devices"

        # draw the message
        if self.client.messages:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)

        self.devices = {devicename:device for devicename,device in self.client.items() if device.enable}

        # draw status
        if not self.devices:
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
        self.topmorewin.noutrefresh()
        self.devwin.noutrefresh()
        self.botmorewin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()

    def defocus(self):
        "Remove focus from all buttons"
        if self.focus:
            btn = self.devbuttons[self.focus]
            btn.focus = False
            btn.draw()
            self.focus = None
        elif self.topmore_btn.focus:
            self.topmore_btn.focus = False
            self.topmore_btn.draw()
        elif self.botmore_btn.focus:
            self.botmore_btn.focus = False
            self.botmore_btn.draw()
        elif self.messages_btn.focus:
            self.messages_btn.focus = False
            self.messages_btn.draw()
        elif self.quit_btn.focus:
            self.quit_btn.focus = False
            self.quit_btn.draw()

    def devwinrefresh(self):
        "Call noutrefresh on more buttons and device window"
        self.topmorewin.noutrefresh()
        self.devwin.noutrefresh()
        self.botmorewin.noutrefresh()


    def botindex(self):
        "Returns the index of the bottom device being displayed"
        # self.topindex is the top device being displayed
        bottomidx = self.topindex + (self.devwinbot-self.devwintop+1) // 2 - 1
        # example  0 + (19-8+1)//2 - 1  = 5
        # example  3 + (19-8+1)//2 - 1  = 8
        lastidx = len(self.devices)-1
        if bottomidx > lastidx:
            return lastidx
        return bottomidx


    def drawdevices(self):
        "Called by self.show/update to create and draw the device buttons"
        self.topmorewin.clear()
        self.devwin.clear()
        self.botmorewin.clear()

        if not self.devices:               # no devices
            self.focus = None
            self.topmore_btn.show = False
            self.botmore_btn.show = False
            return

        # Remove current device buttons
        self.devbuttons.clear()

        bottomidx = self.botindex()

        colnumber = self.maxcols//2 - 6

        linenumber = 0
        for idx, devicename in enumerate(self.devices):
            if idx < self.topindex:
                continue
            if idx > bottomidx:
                break
            self.devbuttons[devicename] = widgets.Button(self.devwin, devicename, linenumber, colnumber)
            linenumber += 2  # two lines per button

        # self.devbuttons is a devicename to button dictionary, but only for buttons displayed

        # Note: initially all device buttons are created with focus False
        # self.focus has the name of the device which should be in focus
        # so if it is set, set the appropriate button focus

        if self.focus:
            if self.focus in self.devbuttons:
                self.devbuttons[self.focus].focus = True
            else:
                self.focus = None

        # if self.topindex is not zero, then draw top more button
        if self.topindex:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # draw devices buttons
        for devbutton in self.devbuttons.values():
            devbutton.draw()

        # bottomidx is the index of the bottom device being displayed
        if bottomidx < len(self.devices) -1:
            self.botmore_btn.show = True
        else:
            self.botmore_btn.show = False
        self.botmore_btn.draw()


    def drawbuttons(self):
        "Called by self.show/update to draw the messages and quit buttons"
        self.buttwin.clear()

        # If a device is in focus, these buttons are not
        if self.focus or self.topmore_btn.focus or self.botmore_btn.focus:
            self.messages_btn.focus = False
            self.quit_btn.focus = False
        elif (not self.quit_btn.focus) and (not self.messages_btn.focus):
            # at least one button must be in focus
            self.messages_btn.focus = True

        self.messages_btn.draw()
        self.quit_btn.draw()


    def update(self, event):
        "Only update if global message has changed, or a new device added or deleted"
        if isinstance(event, events.Message) and event.devicename is None:
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)
            self.messwin.noutrefresh()
            curses.doupdate()
            return
        # check devices unchanged
        if isinstance(event, events.delProperty) and event.vectorname is None:
            # a device has being deleted
            self.topindex = 0
            self.defocus()
            self.show()
            return
        if event.devicename is not None:
            if event.devicename not in self.devices:
                # unknown device, check this is a definition
                if isinstance(event, events.defVector) or isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.topindex = 0
                    self.defocus()
                    self.show()


    def topmorechosen(self):
        "Update when topmore button pressed"
        if not self.topmore_btn.focus:
            return
        if not self.topindex:    # self.topindex cannot be zero
            return

        # devices is a dictionary of devicenames to devices
        # names is a list of all device names
        names = list(self.devices.keys())

        self.topindex -= 1

        if not self.topindex:
            # at the top device
            self.topmore_btn.focus = False
            self.focus = names[0]

        # drawdevices will sort out top and bottom
        # more buttons
        self.drawdevices()
        self.devwinrefresh()


    def botmorechosen(self):
        "Update when botmore button pressed"
        if not self.botmore_btn.focus:
            return

        # the aim is to increment self.topindex
        # but doing so may display last bottom device
        # which makes botmore button dissapear

        # devices is a dictionary of devicenames to devices
        # names is a list of all device names
        names = list(self.devices.keys())

        new_top_idx = self.topindex + 1

        new_bot_idx = new_top_idx + (self.devwinbot-self.devwintop) // 2 - 1
        # lastidx is the index of the last device
        lastidx = len(names)-1

        if new_bot_idx > lastidx:
            # no point incrementing topindex as it does not display any new device
            self.botmore_btn.show = False
            self.focus = names[-1]        # set focus to name of last device
        else:
            # so increment topindex
            self.topindex = new_top_idx
            if new_bot_idx == lastidx:
                # cannot increment further
                self.botmore_btn.show = False
                self.focus = names[-1]

        self.drawdevices()
        self.devwinrefresh()


# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"

        self.stdscr.nodelay(True)
        names = list(self.devices.keys())
        lastidx = len(names)-1            # index of last device

        while True:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key
            displayedbtns = list(self.devbuttons.values())
            displayednames = list(self.devbuttons.keys())
            bottomidx = self.botindex()       # index of last displayed device

            if isinstance(key, tuple):
                # mouse pressed, find if its clicked in any field
                if key in self.quit_btn:
                    if self.quit_btn.focus:
                        widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                        self.messwin.noutrefresh()
                        curses.doupdate()
                        return "Quit"
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        self.quit_btn.focus = True
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                    else:
                        # either a top or bottom more button or a device has focus
                        # and now the quit btn has been given focus
                        self.defocus()
                        self.devwinrefresh()
                        self.quit_btn.focus = True
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                if key in self.messages_btn:
                    if self.messages_btn.focus:
                        return "Messages"
                    elif self.quit_btn.focus:
                        self.quit_btn.focus = False
                        self.messages_btn.focus = True
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                    else:
                        # either a top or bottom more button or a device has focus
                        # and now the messages_btn has focus
                        self.defocus()
                        self.devwinrefresh()
                        self.messages_btn.focus = True
                        self.messages_btn.draw()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                if key in self.topmore_btn:
                    if self.topmore_btn.focus:
                        self.topmorechosen()
                    else:
                        self.defocus()
                        self.topmore_btn.focus = True
                        self.topmore_btn.draw()
                        self.devwinrefresh()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                if key in self.botmore_btn:
                    if self.botmore_btn.focus:
                        self.botmorechosen()
                    else:
                        self.defocus()
                        self.botmore_btn.focus = True
                        self.botmore_btn.draw()
                        self.devwinrefresh()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue

                # so now must check if mouse position is in any of the devices
                if key[0] > self.devwinbot:
                    # no chance of device button being pressed as mouse point
                    # is at a row greater than bottom line of the device window
                    continue

                # displayedbtns button list, but only for buttons displayed

                for idx, btn in enumerate(displayedbtns):
                    if key in btn:
                        if btn.focus:
                            # this indicates a devicename is in focus
                            # and has been clicked
                            return "Vectors"
                        else:
                            # button not in focus, so set it
                            self.defocus()
                            btn.focus = True
                            btn.draw()
                            self.focus = displayednames[idx]
                            self.devwinrefresh()
                            self.buttwin.noutrefresh()
                            curses.doupdate()
                            break
                continue

            # so not a tuple/mouse press, its a key press

            # which button has focus
            if key == 10:
                if self.quit_btn.focus:
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"
                if self.messages_btn.focus:
                    return "Messages"
                if self.topmore_btn.focus:
                    self.topmorechosen()
                    curses.doupdate()
                    continue
                if self.botmore_btn.focus:
                    self.botmorechosen()
                    curses.doupdate()
                    continue

                # If not Quit or Messages, and a device is in focus
                # return the action Vectors, whic indicates a device is chosen, and now its vectors will be shown
                if self.focus:
                    return "Vectors"
                continue


            if key in (32, 9, 261, 338, 258):   # 32 space, 9 tab, 261 right arrow, 338 page down, 258 down arrow
                # go to the next button
                if self.quit_btn.focus:
                    self.quit_btn.focus = False
                    if self.topindex:
                        # that is, if top button does not have index zero
                        self.topmore_btn.focus = True
                    else:
                        self.focus = displayednames[0]
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.quit_btn.focus = True
                    self.drawbuttons()
                    self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                elif self.topmore_btn.focus:
                    self.topmore_btn.focus = False
                    self.focus = displayednames[0]
                    self.drawdevices()
                    self.devwinrefresh()
                    curses.doupdate()
                    continue
                elif self.botmore_btn.focus:
                    self.botmore_btn.focus = False
                    self.messages_btn.focus = True
                else:
                    # one of the devices has focus
                    try:
                        indx = names.index(self.focus)
                    except ValueError:
                        continue
                    # indx here is the index on the list of all devices, not just those displayed
                    if indx == lastidx:
                        # very last device, the botmore_btn should not be shown
                        self.focus = None
                        self.messages_btn.focus = True
                    elif indx == bottomidx:
                        # last displayed device
                        if key in (338, 258):      # 338 page down, 258 down arrow
                            # display next device
                            self.topindex += 1
                            self.focus = names[indx+1]
                        else:
                            # last device on display
                            self.focus = None
                            self.botmore_btn.focus = True
                    else:
                        self.focus = names[indx+1]

            elif key in (353, 260, 339, 259):  # 353 shift tab, 260 left arrow, 339 page up, 259 up arrow
                # go to previous button
                if self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.messages_btn.focus = True
                    self.drawbuttons()
                    self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    if self.botmore_btn.show:
                        self.botmore_btn.focus = True
                    else:
                        self.focus = displayednames[-1]
                elif self.botmore_btn.focus:
                    self.botmore_btn.focus = False
                    self.focus = displayednames[-1]
                elif self.topmore_btn.focus:
                    self.topmore_btn.focus = False
                    self.quit_btn.focus = True
                elif self.focus == names[0]:
                    self.focus = None
                    self.quit_btn.focus = True
                else:
                    try:
                        indx = names.index(self.focus)
                    except ValueError:
                        continue
                    if indx == self.topindex:
                        if key in (339, 259): # 339 page up, 259 up arrow
                            self.topindex -= 1
                            self.focus = names[indx-1]
                        else:
                            self.focus = None
                            self.topmore_btn.focus = True
                    else:
                        self.focus = names[indx-1]

            else:
                # button not recognised
                continue

            # draw devices and buttons
            self.drawdevices()
            self.drawbuttons()
            self.devwinrefresh()
            self.buttwin.noutrefresh()
            curses.doupdate()
