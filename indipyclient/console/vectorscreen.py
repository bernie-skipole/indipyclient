import curses, time

from . import widgets

from .windows import ParentScreen


class VectorScreen(ParentScreen):

    "This displays the chosen vector and its members"


    def __init__(self, stdscr, control, devicename, vectorname):
        super().__init__(stdscr, control)
        self.stdscr.clear()
        curses.flushinp()


        self.devicename = devicename
        self.vectorname = vectorname

        self.device = self.client[self.devicename]
        self.vector = self.device[self.vectorname]

        # title window  (2 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(2, self.maxcols, 0, 0)
        devicetitle = widgets.shorten("Device: " + self.devicename, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(0, 1, devicetitle)
        labeltitle = widgets.shorten(self.vector.label, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(1, 1, labeltitle, curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)

        # timestamp and state window (1 line, full row, starting at 3,0)
        self.tstatewin = self.stdscr.subwin(1, self.maxcols, 3, 0)

        # window showing the members of the vector
        self.memberswin = MembersWin(self.stdscr, self.control, self.tstatewin, self.vector)

        # list areas of the screen, one of these areas has the current 'focus'
        # Members being the area showing the members associated with the vector
        # Vectors, Devices, Messages and Quit are the bottom buttons
        self.screenparts = ("Members", "Vectors", "Devices", "Messages", "Quit")

        # bottom buttons, [Vectors] [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.vectors_btn = widgets.Button(self.buttwin, "Vectors", 0, self.maxcols//2 - 20)
        self.vectors_btn.focus = True

        # as self.vectors_btn.focus is True, no editable field can have focus at this moment
        # so ensure the cursor is off
        curses.curs_set(0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10)
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 11)


    @property
    def membername(self):
        return self.memberswin.membername


    def show(self):
        "Displays the window"

        devices = [ devicename for devicename, device in self.client.items() if device.enable ]

        if self.devicename not in devices:
            widgets.drawmessage(self.messwin, f"{self.devicename} not found!", maxcols=self.maxcols)
            self.vectors_btn.draw()
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.titlewin.noutrefresh()
            self.messwin.noutrefresh()
            self.buttwin.noutrefresh()

            curses.doupdate()
            return
        self.device = self.client[self.devicename]

        vectors = [ vectorname for vectorname, vector in self.device.items() if vector.enable ]


        if self.vectorname not in vectors:
            widgets.drawmessage(self.messwin, f"{self.vectorname} not found!", maxcols=self.maxcols)
            self.vectors_btn.draw()
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.titlewin.noutrefresh()
            self.messwin.noutrefresh()
            self.buttwin.noutrefresh()

            curses.doupdate()
            return
        self.vector = self.device[self.vectorname]

        if self.vector.message:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.vector.message, maxcols=self.maxcols)

        widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)

        # draw the bottom buttons
        self.vectors_btn.draw()
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        # Draw the members widgets
        self.memberswin.draw()


        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.tstatewin.noutrefresh()
        self.buttwin.noutrefresh()
        self.memberswin.noutrefresh()

        curses.doupdate()


    def setfocus(self, newfocus):
        """Sets item in focus to newfocus
           If newfocus is one of Vectors, Messages, Quit, Devices, sets the
           new focus on the button, draws and calls self.buttwin.noutrefresh()
           and removes focus from all other buttons.
           """
        if self.memberswin.focus:
            # current focus is on the subwindows
            if newfocus != "Members":
                self.memberswin.defocus()
                self.memberswin.noutrefresh()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
                self.buttwin.noutrefresh()
            return

        # current focus must be one of the bottom buttons
        if self.vectors_btn.focus and newfocus != "Vectors":
            self.vectors_btn.focus = False
            self.vectors_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            self.buttwin.noutrefresh()
        elif self.devices_btn.focus and newfocus != "Devices":
            self.devices_btn.focus = False
            self.devices_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
            self.buttwin.noutrefresh()
        elif self.messages_btn.focus and newfocus != "Messages":
            self.messages_btn.focus = False
            self.messages_btn.draw()
            if newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
            self.buttwin.noutrefresh()
        elif self.quit_btn.focus and newfocus != "Quit":
            self.quit_btn.focus = False
            self.quit_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
            self.buttwin.noutrefresh()

    def timeout(self, event):
        "A timeout event has occurred, update the vector state"
        if self.vector.state == "Busy":
            self.vector.state = "Alert"
            self.vector.timestamp = event.timestamp
            widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)
            widgets.drawmessage(self.messwin, "Timeout", bold=True) #, maxcols=8)
            self.tstatewin.noutrefresh()
            self.messwin.noutrefresh()
            curses.doupdate()

    def update(self, event):
        "An event affecting this vector has occurred, re-draw the screen"

        self.titlewin.clear()

        devicetitle = widgets.shorten("Device: " + self.devicename, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(0, 1, devicetitle)
        labeltitle = widgets.shorten(self.vector.label, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(1, 1, labeltitle, curses.A_BOLD)

        self.messwin.clear()
        self.tstatewin.clear()
        self.buttwin.clear()
        # self.memberswin does not need a clear() call, as its window is cleared in its draw method

        self.show()
        # calling self.show in turn calls button and members draw and noutrefresh methods

        # after an update, the cursor may need putting back into an editable field
        if self.memberswin.focus:
            index = self.memberswin.widgetindex_in_focus()
            if index is not None:
                widget = self.memberswin.memberwidgets[index]
                if hasattr(widget, "edit_txt"):
                    if widget.edit_txt.focus:
                        widget.edit_txt.movecurs()
                        curses.doupdate()


    def check_bottom_btn(self, key):
        """Takes action if a bottom button is pressed
           returns action Quit etc... if a key action is to be taken
           returns None if this method has dealt with the action, and the calling
           routine can continue and obtain another key.
           Returns the key, if the key has not been handled and
           has to be checked further"""

        if isinstance(key, tuple):
            # mouse pressed, find if its clicked in any
            # of the bottom buttons
            if key in self.quit_btn:
                if self.quit_btn.focus:
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"
                else:
                    # focus is elsewhere
                    self.setfocus("Quit")
                curses.doupdate()
                return
            if key in self.messages_btn:
                if self.messages_btn.focus:
                    return "Messages"
                else:
                    self.setfocus("Messages")
                curses.doupdate()
                return
            if key in self.devices_btn:
                if self.devices_btn.focus:
                    return "Devices"
                else:
                    self.setfocus("Devices")
                curses.doupdate()
                return
            if key in self.vectors_btn:
                if self.vectors_btn.focus:
                    return "Vectors"
                else:
                    self.setfocus("Vectors")
                curses.doupdate()
                return
        elif self.vectors_btn.focus or self.devices_btn.focus or self.messages_btn.focus or self.quit_btn.focus:
            # not a tuple, but one of the buttons is in focus, so check if a relevant key pressed
            if key in (32, 9, 261, 338, 258):   # go to next button
                if self.vectors_btn.focus:
                    self.vectors_btn.focus = False
                    self.devices_btn.focus = True
                elif self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.messages_btn.focus = True
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.quit_btn.focus = True
                elif self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.memberswin.set_topfocus()
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                return
            elif key in (353, 260, 339, 259):   # go to prev button
                if self.vectors_btn.focus:
                    self.vectors_btn.focus = False
                    self.memberswin.set_botfocus()
                elif self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.vectors_btn.focus = True
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.devices_btn.focus = True
                elif self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.messages_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                return
            elif key == 10:
                if self.vectors_btn.focus:
                    return "Vectors"
                elif self.devices_btn.focus:
                    return "Devices"
                elif self.messages_btn.focus:
                    return "Messages"
                elif self.quit_btn.focus:
                    return "Quit"
            else:
                # key is a key press, not a mouse tuple, and a bottom
                # button is in focus but the key is not one that initiates
                # any action, so return None to indicate it can be ignored
                return
        # if mouse, it is not clicked on any bottom button
        # if a key, then no bottom button is in focus
        # so just return the key
        return key


    async def inputs(self):
        "Gets inputs from the screen"
        # two loops formed here, one for the entire screen
        # and one for an editable field
        # result tracks the results of tests to see if an editable field loop is needed
        result = None

        self.stdscr.nodelay(True)
        while True:
            if result:
                key = result
                result = None
            else:
                key = await self.keyinput()
                # self.keyinput returns either key, or a tuple or "Stop" or "Resize"

            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key

            key = self.check_bottom_btn(key)
            if not key:
                continue
            if key in ("Vectors", "Devices", "Messages", "Quit"):
                return key

            # At this point, key could be a mouse tuple, or a keystroke
            # But not clicked on any of the bottom buttons
            # So could be mouse clicked away from anything, or on something in memberswin
            # or maybe memberswin has the focus, and the keystroke should be handled there

            if isinstance(key, tuple):
                # mouse pressed, find if its clicked in any of the MembersWin fields
                result = await self.memberswin.handlemouse(key)
                # result is None if fully handled,
                # or is 'edit' if mouse clicked in an editable field in MembersWin
                # or is 'focused' if mouse clicked on a previously unfocused button
                # could also be one of "submitted", "next", "previous" if clicked
                # on a focused submit, or top or bottom widget
                if not result:
                    # Handled, continue with while loop and get next key
                    continue


            # At this point, result is None if key is a keystroke,
            # or result is value returned by memberswin.handlemouse(key)

            if (result == "focused") or (result == "edit"):
                # a field in self.memberswin has been set into focus
                # ensure bottom buttons are defocused
                self.vectors_btn.focus = False
                self.vectors_btn.draw()
                self.devices_btn.focus = False
                self.devices_btn.draw()
                self.messages_btn.focus = False
                self.messages_btn.draw()
                self.quit_btn.focus = False
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()

            if result == "focused":
                # A button has been set to focus, nothing more to do
                # continue and get the next key
                result = None
                continue

            if (not result) and (not self.memberswin.focus):
                # if keystroke, then only of interest if memberswin has focus
                continue

            if not result:
                # key is a keystroke, and memberswin has focus, handle it
                result = await self.memberswin.setkey(key)
                # this returns "edit" if an editable field has been given focus
                # could also be "submitted", "next", "previous" or a keystroke such
                # as 9 for tab

            while result == "edit":
                # An editable field is in focus
                result = await self.memberswin.inputfield()


            if result in ("Resize", "Messages", "Devices", "Vectors", "Member", "Stop"):
                return result

            if result == "submitted":
                self.vector.state = 'Busy'
                # The vector has been submitted, draw vector state which is now busy
                widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)
                self.tstatewin.noutrefresh()
                self.vectors_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                result = None
            elif result == "next":   # go to next button
                self.memberswin.defocus() # removes focus and calls draw and noutrefresh on memberswin
                self.vectors_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                result = None
            elif result == "previous":   # go to prev button
                self.memberswin.defocus() # removes focus and calls draw and noutrefresh on memberswin
                self.quit_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                result = None




# MembersWin is created within VectorScreen


class MembersWin():

    "Used to display the vector members"


    def __init__(self, stdscr, control, tstatewin, vector):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.control = control
        self.client = control.client
        self.tstatewin = tstatewin
        self.vector = vector
        self.vectorname = vector.name

        # topmore button at index 5
        topindex = 5

        # top more btn on 6th line ( coords 0 to 5 )
        # bot more btn on line (self.maxrows - 3) + 1
        # displaylines = (self.maxrows - 2) - 6  - 1


        # members window
        memwintop = topindex + 2                               # row index 7
        memwinbot = self.maxrows - 4                           # row index 20

        # botmorerow is one below the members window
        botmorerow = memwinbot + 1                             # row index 21
        self.displaylines = memwinbot - memwintop + 1

        # topmorewin (1 line, full row, starting at topindex, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, topindex, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="TopMore")
        self.topmore_btn.show = False

        # members window
        self.memwin = self.stdscr.subwin(self.displaylines, self.maxcols, memwintop, 0)

        # topindex of member being shown
        self.topindex = 0                   # so six members will show members with indexes 0-5

        # dictionary of member name to member this vector owns
        members_dict = self.vector.members()

        # list of member names in alphabetic order
        self.membernames = sorted(members_dict.keys())

        # namelen is length of name button
        namelen = max(len(name) for name in self.membernames)

        # create the member widgets
        self.memberwidgets = []
        for name in self.membernames:
            if self.vector.vectortype == "SwitchVector":
                self.memberwidgets.append(widgets.SwitchMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "LightVector":
                self.memberwidgets.append(widgets.LightMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "NumberVector":
                self.memberwidgets.append(widgets.NumberMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "TextVector":
                self.memberwidgets.append(widgets.TextMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "BLOBVector":
                self.memberwidgets.append(widgets.BLOBMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))


        # Sets list of displayed widgets, self.displayed
        self.displayedwidgets()


        # note a widget has two indexes, its index in self.memberwidgets and its index in self.displayed

        # displayedindex = memberwidgetsindex - self.topindex  limited by size of self.displayed
        # memberwidgetsindex = displayedindex + self.topindex

        # this is True, if this widget is in focus
        self.focus = False

        # botmorewin = 1 line height, columns just over half of self.maxrows, to give room on the right for submitwin
        # starting at y = columns - 11, x = 0)
        botmorewincols = self.maxcols//2 + 4
        self.botmorewin = self.stdscr.subwin(1, botmorewincols, botmorerow, 0)
        if self.vector.perm == 'ro':
            self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, botmorewincols-11)
        else:
            self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, botmorewincols-20)
        self.botmore_btn.show = False
        self.botmore_btn.focus = False

        # submitwin holding submit_btn and cancel_btn, located to the right of botmorewin
        # submitwin = 1 line height, starting at y=botmorerow, x = botmorewincols + 1
        # width = self.maxcols -x - 2
        self.submitwin = self.stdscr.subwin(1, self.maxcols - botmorewincols - 3, botmorerow, botmorewincols + 1)
        self.submit_btn = widgets.Button(self.submitwin, "Submit", 0, 0)
        self.cancel_btn = widgets.Button(self.submitwin, "Cancel", 0, 12)
        if (self.vector.perm == 'ro') or (self.vector.vectortype == "BLOBVector"):
            self.submit_btn.show = False
            self.cancel_btn.show = False
        else:
            self.submit_btn.show = True
            self.cancel_btn.show = True

        # keep these in a list for easy reference
        self.controlbtns = [ self.topmore_btn, self.botmore_btn, self.submit_btn, self.cancel_btn]

        # this will be set to a widgets awitable input field if it gets focus
        self._inputfield = None

        # this will be set to a membername if a member is chosen
        self.membername = None


    def displayedwidgets(self):
        "Sets list of widgets displayed"
        self.displayed = []
        line = 0
        for widget in self.memberwidgets[self.topindex:]:
            if line+widget.linecount > self.displaylines:
                break
            self.displayed.append(widget)
            line += widget.linecount


    def defocus(self):
        "Removes focus from all buttons"
        self.focus = False
        for widget in self.displayed:
            if widget.focus:
                widget.focus = False
                widget.draw()
                self.memwin.noutrefresh()
                return
        for btn in self.controlbtns:
            if btn.focus:
                btn.focus = False
                btn.draw()
                btn.window.noutrefresh()
                return


    def set_topfocus(self):
        "Sets topmore_btn focus, or if not shown, sets top widget focus"
        self.defocus()
        self.focus = True
        if self.topindex:
            # self.topindex is not zero, so topmore button must be shown
            # and with focus set
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
            self.topmorewin.noutrefresh()
        else:
            # self.topindex is zero, so top member widget must have focus
            # and with focus set
            widget = self.displayed[0]
            widget.focus = True
            widget.draw()
            self.memwin.noutrefresh()


    def set_botfocus(self):
        """Sets cancel_btn focus, or if not shown
           sets botmore_btn focus, or if not shown,
           sets bottom widget focus"""
        self.defocus()
        self.focus = True

        if self.cancel_btn.show:
            self.cancel_btn.focus = True
            self.cancel_btn.draw()
            self.submitwin.noutrefresh()
            return

        # no submit/cancel button, so either bottom widget is set in focus
        # or bottom more button is set in focus

        if self.botmore_btn.show:
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
            self.botmorewin.noutrefresh()
            return

        # set focus on bottom member widget
        widget = self.displayed[-1]
        widget.focus = True
        widget.draw()
        self.memwin.noutrefresh()



    def draw(self):
        "Clears and draws the screen, but does not call noutrefresh or curses.doupdate()"
        self.memwin.clear()

        # draw the member widgets being displayed
        line = 0
        for memberwidget in self.displayed:
            memberwidget.draw(line)
            line = line+memberwidget.linecount

        if self.topindex:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # Is the bottom widget being displayed?
        # displayedindex = memberwidgetsindex - self.topindex  limited by size of self.displayed
        # memberwidgetsindex = displayedindex + self.topindex

        # displayedindex of last widget displayed
        displayedindex = len(self.displayed) - 1
        memberwidgetsindex = displayedindex + self.topindex

        if memberwidgetsindex == len(self.memberwidgets) -1:
            # very last widget
            self.botmore_btn.show = False
        else:
            self.botmore_btn.show = True
        self.botmore_btn.draw()

        self.submit_btn.draw()
        self.cancel_btn.draw()


    def noutrefresh(self):
        """Refresh this objects entire window, including widgets,
           top and bottom buttons, and submt and cancel buttons"""
        self.topmorewin.noutrefresh()
        self.memwin.noutrefresh()
        self.botmorewin.noutrefresh()
        self.submitwin.noutrefresh()


    def widgetindex_in_focus(self):
        "Returns the memberwidget index which has focus, or None"
        for index,widget in enumerate(self.memberwidgets):
            if widget.focus:
                return index


    def displayed_widgetindex_in_focus(self):
        "Returns the self.displayed index which has focus, or None"
        for index,widget in enumerate(self.displayed):
            if widget.focus:
                return index


    async def inputfield(self):
        "Returns None, or result of awaitable widget.inputfield"
        if self.vector.perm == "ro":
            return
        if self._inputfield is None:
            return
        result = await self._inputfield()
        if not result:
            return
        if result in ("Resize", "Messages", "Devices", "Vectors", "Stop", "submitted", "next", "previous"):
            return result
        if isinstance(result, tuple):
            # a mouse press, go to outer loop with result set
            return result
        # inputfield has returned a keystroke
        # which is now tested again with setkey(key)
        handlekey = await self.setkey(result)
        return handlekey


    async def handlemouse(self, key):
        "Handles a mouse input"
        if key in self.topmore_btn:
            if self.topmore_btn.focus:
                # same as pressing enter on the focused button
                await self.setkey(10)
                return
            else:
                # key is on topmore_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.topmore_btn.focus = True
                self.topmore_btn.draw()
                self.topmorewin.noutrefresh()
                return "focused"

        if key in self.botmore_btn:
            if self.botmore_btn.focus:
                # same as pressing enter on the focused button
                await self.setkey(10)
                return
            else:
                # key is on botmore_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.botmore_btn.focus = True
                self.botmore_btn.draw()
                self.botmorewin.noutrefresh()
                return "focused"

        if key in self.submit_btn:
            if self.submit_btn.focus:
                # same as pressing enter on the focused button
                result = await self.setkey(10)  # this may return "submitted"
                return result
            else:
                # key is on submit_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.submit_btn.focus = True
                self.submit_btn.draw()
                self.submitwin.noutrefresh()
                return "focused"

        if key in self.cancel_btn:
            if self.cancel_btn.focus:
                # same as pressing enter on the focused button
                await self.setkey(10)
                return
            else:
                # key is on cancel_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.cancel_btn.focus = True
                self.cancel_btn.draw()
                self.submitwin.noutrefresh()
                return "focused"

        # next check - has the mouse key been pressed on a widget
        result = None
        windex = None
        editfocus = False
        for index, widget in enumerate(self.displayed):
            if hasattr(widget, 'edit_txt') and widget.edit_txt.focus:
                editfocus = True
            result = await widget.handlemouse(key)
            # result is "focused' or 'edit' if mouse landed on a field
            if result:
                windex = index
                break
        else:
            # mouse landed outside of any field, if an editable field
            # is already in focus, return edit
            if editfocus:
                return "edit"


        if result == "set_on":  ###
            # special case of a switch widget being turned on
            # set all other widgets Off
            for widget in self.memberwidgets:
                if not widget.focus:
                    widget.on.bold = False
                    widget.off.bold = True
                    widget.on.draw()
                    widget.off.draw()
            self.memwin.noutrefresh()
            return "focused"

        if result:
            # remove focus from any other button
            for index, widget in enumerate(self.displayed):
                if index == windex:
                    continue
                if widget.focus:
                    widget.focus = False
                    widget.draw()
                    break
            # so widget focus has been drawn
            self.memwin.noutrefresh()
            for btn in self.controlbtns:
                if btn.focus:
                    btn.focus = False
                    btn.draw()
                    btn.window.noutrefresh()
                    break
            # and indicate this window has focus
            self.focus = True

        if result == "Member":
            widget = self.displayed[windex]
            self.membername = widget.name
            return "Member"

        if result == "edit":
            widget = self.displayed[windex]
            self._inputfield = widget.inputfield
            # and if an editable field is chosen, show the cursor
            curses.curs_set(1)

        return result



    async def setkey(self, key):
        "Handles a key stroke"

        for index, widget in enumerate(self.displayed):
            if widget.focus:
                # a widget is in focus
                if self.vector.perm == "ro":
                    if (key == 10) and widget.name_btn.focus:
                        # a ro widget accepts a enter key on the name button
                        self.membername = widget.name
                        return "Member"
                    break
                result = await widget.setkey(key)
                if result == "editup":                  # up arrow pressed in editable field
                    return self.editup(index, widget)
                elif result == "editdown":              # down arrow pressed in editable field
                    return self.editdown(index, widget)
                elif result == "sendup":                  # up arrow pressed in blob send button
                    return self.sendup(index, widget)
                elif result == "senddown":              # down arrow pressed in blob send button
                    return self.senddown(index, widget)
                elif result == "onup":                  # up arrow pressed in switch on button
                    return self.onup(index, widget)
                elif result == "ondown":              # down arrow pressed in switch on button
                    return self.ondown(index, widget)
                elif result == "offup":                  # up arrow pressed in switch off button
                    return self.offup(index, widget)
                elif result == "offdown":              # down arrow pressed in switch off button
                    return self.offdown(index, widget)
                elif result == "edit":                  # an editable field has been chosen
                    # this sets an input awaitable
                    self._inputfield = widget.inputfield
                    return result
                else:
                    self._inputfield = None
                if result == "Member":
                    self.membername = widget.name
                    return "Member"
                if result == "set_on":  ###
                    # special case of a switch widget being turned on
                    # set all other widgets Off
                    for widget in self.memberwidgets:
                        if not widget.focus:
                            widget.on.bold = False
                            widget.off.bold = True
                            widget.on.draw()
                            widget.off.draw()
                    self.memwin.noutrefresh()
                    curses.doupdate()
                    return
                if result:
                    # if the widget returns a key. then continue with
                    # checking it
                    key = result
                    break
                # the widget has handled the key, and returns None
                # to indicate no further checks required.
                return

        if key == 10:
            # Enter key pressed
            if self.topmore_btn.focus:
                # scroll the window down
                self.topindex -= 1
                self.displayedwidgets()
                if not self.topindex:
                    # self.topindex is now zero, so self.topmore_btn will not be shown
                    # and the top widget should get focus
                    topwidget = self.displayed[0]
                    topwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return
            elif self.botmore_btn.focus:
                # scroll the window up
                self.topindex += 1
                self.displayedwidgets()
                # displayedindex of last widget displayed
                displayedindex = len(self.displayed) - 1
                memberwidgetsindex = displayedindex + self.topindex
                if memberwidgetsindex == len(self.memberwidgets) -1:
                    # the last widget is being displayed, so self.botmore_btn will not be shown
                    # and the bottom widget should get focus
                    botwidget = self.memberwidgets[-1]
                    botwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return
            elif self.vector.perm == "ro":
                # can scroll up or down, with more buttons,
                # but nothing to submit, so Enter key ignored
                return
            elif self.submit_btn.focus:
                submitit = await submitvector(self.vector, self.memberwidgets)
                if submitit:
                    # vector has been submitted, remove focus from this window
                    self.focus = False
                    self.submit_btn.focus = False
                    self.submit_btn.ok()   # draw submit button in green with ok
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    time.sleep(0.3)      # blocking, to avoid screen being changed while this time elapses
                    self.submitwin.clear()
                    self.submit_btn.draw()
                    self.cancel_btn.draw()
                    self.submitwin.noutrefresh()
                    # curses.doupdate() - not needed, called by vector window on submission
                    return "submitted"
                else:
                    # error condition
                    self.submit_btn.alert()
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    time.sleep(0.3)        # blocking, to avoid screen being changed while this time elapses
                    self.submitwin.clear()
                    self.submit_btn.draw()
                    self.cancel_btn.draw()
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    return
            elif self.cancel_btn.focus:
                # Cancel chosen, reset all widgets, removing any value changes
                for memberwidget in self.displayed:
                    memberwidget.reset()
                self.memwin.noutrefresh()
                curses.doupdate()
                return
            else:
                # Enter pressed, but none of the above have handled it
                return

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

        if key in (32, 9, 261, 338, 258):   # go to next button
            if self.cancel_btn.focus:
                # last in this window
                return "next"
            if self.submit_btn.focus:
                self.submit_btn.focus = False
                self.cancel_btn.focus = True
                self.submit_btn.draw()
                self.cancel_btn.draw()
                self.submitwin.noutrefresh()
                curses.doupdate()
                return
            if self.botmore_btn.focus:
                if self.submit_btn.show:
                    self.botmore_btn.focus = False
                    self.botmore_btn.draw()
                    self.submit_btn.focus = True
                    self.submit_btn.draw()
                    self.botmorewin.noutrefresh()
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    return
                else:
                    return "next"
            # get the top widget being displayed
            if self.topmore_btn.focus:
                self.topmore_btn.focus = False
                self.topmore_btn.draw()
                nextwidget = self.displayed[0]
                nextwidget.focus = True
                nextwidget.draw()
                self.topmorewin.noutrefresh()
                self.memwin.noutrefresh()
                curses.doupdate()
                return

            if (displayedindex := self.displayed_widgetindex_in_focus()) is not None:
                # A widget is in focus
                widget = self.displayed[displayedindex]
                if displayedindex != len(self.displayed) - 1:
                    # the displayed widget is not the last widget on the list of displayed widgets
                    # so simply set the next widget into focus
                    widget.focus = False
                    widget.draw()
                    nextwidget = self.displayed[displayedindex+1]
                    nextwidget.focus = True
                    nextwidget.draw()
                    self.memwin.noutrefresh()
                    curses.doupdate()
                    return
                # The widget in focus is the last of the displayed widgets
                # Either scroll up, or jump to more ....
                widgetindex = displayedindex + self.topindex
                if widgetindex == len(self.memberwidgets) -1:
                    # This is the last widget, the more button will not be shown, but the submit button may be
                    if self.submit_btn.show:
                        widget.focus = False
                        widget.draw()
                        self.submit_btn.focus = True
                        self.submit_btn.draw()
                        self.memwin.noutrefresh()
                        self.submitwin.noutrefresh()
                        curses.doupdate()
                        return
                    # last widget and the submit is not shown
                    return "next"
                # last displayed widgets, but there are further widgets to be shown
                if key == 9:
                    # tab key pressed, set the botmore button in focus
                    widget.focus = False
                    widget.draw()
                    self.botmore_btn.focus = True
                    self.botmore_btn.draw()
                    self.memwin.noutrefresh()
                    self.botmorewin.noutrefresh()
                    curses.doupdate()
                    return
                # next required, but not tab and not last widget,
                # so scroll the window up
                widget.focus = False
                widget.draw()
                self.topindex += 1
                self.displayedwidgets()
                nextwidget = self.displayed[-1]
                nextwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

        if key in (353, 260, 339, 259):   # go to prev button

            if self.cancel_btn.focus:
                # go to submit button
                self.cancel_btn.focus = False
                self.submit_btn.focus = True
                self.cancel_btn.draw()
                self.submit_btn.draw()
                self.submitwin.noutrefresh()
                curses.doupdate()
                return
            if self.submit_btn.focus:
                self.submit_btn.focus = False
                self.submit_btn.draw()
                self.submitwin.noutrefresh()
                if self.botmore_btn.show:
                    self.botmore_btn.focus = True
                    self.botmore_btn.draw()
                    self.botmorewin.noutrefresh()
                    curses.doupdate()
                    return
                # set bottom displayed widget into focus
                widget = self.displayed[-1]
                widget.focus = True
                widget.draw()
                self.memwin.noutrefresh()
                curses.doupdate()
                return
            if self.botmore_btn.focus:
                # set bottom displayed widget into focus
                self.botmore_btn.focus = False
                self.botmore_btn.draw()
                self.botmorewin.noutrefresh()
                widget = self.displayed[-1]
                widget.focus = True
                widget.draw()
                self.memwin.noutrefresh()
                curses.doupdate()
                return
            if self.topmore_btn.focus:
                # top button of this window
                return "previous"
            # So now check if a member button is in focus
            if (displayedindex := self.displayed_widgetindex_in_focus()) is not None:
                # A widget is in focus
                widget = self.displayed[displayedindex]
                if displayedindex:
                    # not zero, so focus can just move up one
                    widget.focus = False
                    widget.draw()
                    prevwidget = self.displayed[displayedindex-1]
                    prevwidget.focus = True
                    prevwidget.draw()
                    self.memwin.noutrefresh()
                    curses.doupdate()
                    return
                # showing top widget of the displayed widgets
                # Either scroll down, or jump to more ....
                # self.topindex is the widget index
                if not self.topindex:
                    # This is the first widget, the more button will not be shown
                    return "previous"
                # top displayed widgets, but more can be shown, if shift-tab pressed,
                # jump to topmore
                if key == 353:
                    # shift tab key pressed, set the topmore button in focus
                    widget.focus = False
                    widget.draw()
                    self.topmore_btn.focus = True
                    self.topmore_btn.draw()
                    self.memwin.noutrefresh()
                    self.topmorewin.noutrefresh()
                    curses.doupdate()
                    return
                # prev required, but not shift-tab and not first widget,
                # so scroll the window down
                widget.focus = False
                widget.draw()
                self.topindex -= 1
                self.displayedwidgets()
                prevwidget = self.displayed[0]
                prevwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return

    def editup(self, displayedindex, widget):
        "A widget edit field has requested next up"
        # this sets an input awaitable
        self._inputfield = None
        widget.focus = False
        widget.draw()
        if displayedindex:
            # not zero, so focus can just move up one
            prevwidget = self.displayed[displayedindex-1]
            prevwidget.set_edit_focus()
            self._inputfield = prevwidget.inputfield
            self.memwin.noutrefresh()
            curses.doupdate()
            return "edit"
        # showing top widget of the displayed widgets
        # Either scroll down, or jump to more ....
        # self.topindex is the widget index
        if not self.topindex:
            # This is the first widget, the more button will not be shown
            self.memwin.noutrefresh()
            curses.doupdate()
            return "previous"
        # top displayed widgets, but more can be shown
        # so scroll the window down
        self.topindex -= 1
        self.displayedwidgets()
        prevwidget = self.displayed[0]
        prevwidget.set_edit_focus()
        self._inputfield = prevwidget.inputfield
        self.draw()
        self.noutrefresh()
        curses.doupdate()
        return "edit"


    def editdown(self, displayedindex, widget):
        "A widget edit field has requested next down"
        # this sets an input awaitable
        self._inputfield = None
        widget.focus = False
        widget.draw()
        if displayedindex != len(self.displayed) - 1:
            # the displayed widget is not the last widget on the list of displayed widgets
            # so simply set the next widget into focus
            nextwidget = self.displayed[displayedindex+1]
            nextwidget.set_edit_focus()
            self._inputfield = nextwidget.inputfield
            self.memwin.noutrefresh()
            curses.doupdate()
            return "edit"
        # The widget in focus is the last of the displayed widgets
        # Either scroll up, or jump to more ....
        widgetindex = displayedindex + self.topindex
        if widgetindex == len(self.memberwidgets) -1:
            # This is the last widget, the more button will not be shown, but the submit button may be
            if self.submit_btn.show:
                self.submit_btn.focus = True
                self.submit_btn.draw()
                self.memwin.noutrefresh()
                self.submitwin.noutrefresh()
                curses.doupdate()
                return
            # last widget and the submit is not shown
            self.memwin.noutrefresh()
            curses.doupdate()
            return "next"
        else:
            # last displayed widgets, but there are further widgets to be shown
            # so scroll the window up
            self.topindex += 1
            self.displayedwidgets()
            nextwidget = self.displayed[-1]
            nextwidget.set_edit_focus()
            self._inputfield = nextwidget.inputfield
            self.draw()
            self.noutrefresh()
            curses.doupdate()
            return "edit"

    def sendup(self, displayedindex, widget):
        "A blob send button has up arrow pressed"
        widget.focus = False
        widget.draw()
        if displayedindex:
            # not zero, so focus can just move up one
            prevwidget = self.displayed[displayedindex-1]
            prevwidget.set_send_focus()
            self.memwin.noutrefresh()
            curses.doupdate()
            return
        # showing top widget of the displayed widgets
        # Either scroll down, or jump to more ....
        # self.topindex is the widget index
        if not self.topindex:
            # This is the first widget, the more button will not be shown
            self.memwin.noutrefresh()
            curses.doupdate()
            return "previous"
        # top displayed widgets, but more can be shown
        # so scroll the window down
        self.topindex -= 1
        self.displayedwidgets()
        prevwidget = self.displayed[0]
        prevwidget.set_send_focus()
        self.draw()
        self.noutrefresh()
        curses.doupdate()
        return

    def senddown(self, displayedindex, widget):
        "A blob send button has down arrow pressed"
        widget.focus = False
        widget.draw()
        if displayedindex != len(self.displayed) - 1:
            # the displayed widget is not the last widget on the list of displayed widgets
            # so simply set the next widget into focus
            nextwidget = self.displayed[displayedindex+1]
            nextwidget.set_send_focus()
            self.memwin.noutrefresh()
            curses.doupdate()
            return
        # The widget in focus is the last of the displayed widgets
        # Either scroll up, or jump to more ....
        widgetindex = displayedindex + self.topindex
        if widgetindex == len(self.memberwidgets) -1:
            # This is the last widget
            self.memwin.noutrefresh()
            curses.doupdate()
            return "next"
        else:
            # last displayed widgets, but there are further widgets to be shown
            # so scroll the window up
            self.topindex += 1
            self.displayedwidgets()
            nextwidget = self.displayed[-1]
            nextwidget.set_send_focus()
            self.draw()
            self.noutrefresh()
            curses.doupdate()
            return

    def onup(self, displayedindex, widget):
        "A switch on button has up arrow pressed"
        widget.focus = False
        widget.draw()
        if displayedindex:
            # not zero, so focus can just move up one
            prevwidget = self.displayed[displayedindex-1]
            prevwidget.set_on_focus()
            self.memwin.noutrefresh()
            curses.doupdate()
            return
        # showing top widget of the displayed widgets
        # Either scroll down, or jump to more ....
        # self.topindex is the widget index
        if not self.topindex:
            # This is the first widget, the more button will not be shown
            self.memwin.noutrefresh()
            curses.doupdate()
            return "previous"
        # top displayed widgets, but more can be shown
        # so scroll the window down
        self.topindex -= 1
        self.displayedwidgets()
        prevwidget = self.displayed[0]
        prevwidget.set_on_focus()
        self.draw()
        self.noutrefresh()
        curses.doupdate()
        return

    def ondown(self, displayedindex, widget):
        "A switch on button has down arrow pressed"
        widget.focus = False
        widget.draw()
        if displayedindex != len(self.displayed) - 1:
            # the displayed widget is not the last widget on the list of displayed widgets
            # so simply set the next widget into focus
            nextwidget = self.displayed[displayedindex+1]
            nextwidget.set_on_focus()
            self.memwin.noutrefresh()
            curses.doupdate()
            return
        # The widget in focus is the last of the displayed widgets
        # Either scroll up, or jump to more ....
        widgetindex = displayedindex + self.topindex
        if widgetindex == len(self.memberwidgets) -1:
            self.submit_btn.focus = True
            self.submit_btn.draw()
            self.memwin.noutrefresh()
            self.submitwin.noutrefresh()
            curses.doupdate()
            return
        else:
            # last displayed widgets, but there are further widgets to be shown
            # so scroll the window up
            self.topindex += 1
            self.displayedwidgets()
            nextwidget = self.displayed[-1]
            nextwidget.set_on_focus()
            self.draw()
            self.noutrefresh()
            curses.doupdate()
            return

    def offup(self, displayedindex, widget):
        "A switch off button has up arrow pressed"
        widget.focus = False
        widget.draw()
        if displayedindex:
            # not zero, so focus can just move up one
            prevwidget = self.displayed[displayedindex-1]
            prevwidget.set_off_focus()
            self.memwin.noutrefresh()
            curses.doupdate()
            return
        # showing top widget of the displayed widgets
        # Either scroll down, or jump to more ....
        # self.topindex is the widget index
        if not self.topindex:
            # This is the first widget, the more button will not be shown
            self.memwin.noutrefresh()
            curses.doupdate()
            return "previous"
        # top displayed widgets, but more can be shown
        # so scroll the window down
        self.topindex -= 1
        self.displayedwidgets()
        prevwidget = self.displayed[0]
        prevwidget.set_off_focus()
        self.draw()
        self.noutrefresh()
        curses.doupdate()
        return

    def offdown(self, displayedindex, widget):
        "A switch off button has down arrow pressed"
        widget.focus = False
        widget.draw()
        if displayedindex != len(self.displayed) - 1:
            # the displayed widget is not the last widget on the list of displayed widgets
            # so simply set the next widget into focus
            nextwidget = self.displayed[displayedindex+1]
            nextwidget.set_off_focus()
            self.memwin.noutrefresh()
            curses.doupdate()
            return
        # The widget in focus is the last of the displayed widgets
        # Either scroll up, or jump to more ....
        widgetindex = displayedindex + self.topindex
        if widgetindex == len(self.memberwidgets) -1:
            self.submit_btn.focus = True
            self.submit_btn.draw()
            self.memwin.noutrefresh()
            self.submitwin.noutrefresh()
            curses.doupdate()
            return
        else:
            # last displayed widgets, but there are further widgets to be shown
            # so scroll the window up
            self.topindex += 1
            self.displayedwidgets()
            nextwidget = self.displayed[-1]
            nextwidget.set_off_focus()
            self.draw()
            self.noutrefresh()
            curses.doupdate()
            return


async def submitvector(vector, memberwidgets):
    "Checks and submits the vector, if ok returns True, if not returns False"
    if vector.vectortype == "SwitchVector":
        members = {member.name:member.newvalue() for member in memberwidgets}
        # members is a dictionary of membername : member value ('On' or 'Off')
        # check if switches obey the switch rules 'OneOfMany','AtMostOne','AnyOfMany'
        oncount = sum(value == 'On' for value in members.values())
        if (vector.rule == 'OneOfMany') and oncount != 1:
            # one, and only one must be set
            return False
        if (vector.rule == 'AtMostOne') and oncount > 1:
            # one, or none can be set, but not more than 1
            return False
        await vector.send_newSwitchVector(members=members)
        return True
    elif vector.vectortype == "NumberVector":
        members = {member.name:member.newvalue().strip() for member in memberwidgets}
        # members is a dictionary of membername : member value (new number string)
        await vector.send_newNumberVector(members=members)
        return True
    elif vector.vectortype == "TextVector":
        members = {member.name:member.newvalue().strip() for member in memberwidgets}
        # members is a dictionary of membername : member value (new text string)
        await vector.send_newTextVector(members=members)
        return True
    # BLOBVector's are not called with submit button
    # each member has its own send button
    # LightVectors are ro and cannot be submitted
    return False
