
import asyncio, curses, sys

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise




from . import widgets


from .. import events

#<!ELEMENT defNumberVector (defNumber+) >
#<!ATTLIST defNumberVector
#device %nameValue; #REQUIRED
#name of Device
#name %nameValue; #REQUIRED
#name of Property
#label %labelValue; #IMPLIED
#GUI label, use name by default
#group %groupTag; #IMPLIED
#Property group membership, blank by default
#state %propertyState; #REQUIRED
#current state of Property
#perm %propertyPerm; #REQUIRED
#ostensible Client controlability
#timeout %numberValue; #IMPLIED
#worse-case time to affect, 0 default, N/A for ro
#timestamp %timeValue #IMPLIED
#moment when these data were valid
#message %textValue #IMPLIED
#commentary



class VectorScreen:

    def __init__(self, stdscr, consoleclient, devicename, vectorname):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.devicename = devicename
        self.vectorname = vectorname

        self.device = self.client[self.devicename]
        self.vector = self.device[self.vectorname]

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 1, self.devicename)
        self.titlewin.addstr(1, 1, self.vectorname + " : " + self.vector.group)
        self.titlewin.addstr(2, 1, self.vector.label, curses.A_BOLD)

        # messages window (1 line, full row, starting at 3,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 3, 0)

        # timestamp and state window (1 line, full row, starting at 4,0)
        self.tstatewin = self.stdscr.subwin(1, self.maxcols, 4, 0)

        try:
            # window showing the members of the vector
            self.members = MembersWin(self.stdscr, self.consoleclient, self.vector)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # bottom buttons, [Vectors] [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.vectors_btn = widgets.Button(self.buttwin, "Vectors", 0, self.maxcols//2 - 20)
        self.vectors_btn.focus = True
        self.focus = "Vectors"

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10)
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 11)


    def show(self):
        "Displays the window"

        if self.vector.message:
            widgets.drawmessage(self.messwin, self.vector.message, maxcols=self.maxcols)

        widgets.draw_timestamp_state(self.consoleclient, self.tstatewin, self.vector, maxcols=self.maxcols)

        # Draw the members widgets
        self.members.draw()

        # draw the bottom buttons
        self.vectors_btn.draw()
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.tstatewin.noutrefresh()
        self.members.noutrefresh()
        self.buttwin.noutrefresh()

        curses.doupdate()
        return

    def update(self, event):
        pass


# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow


    def check_bottom_btn(self, key):
        """If a bottom btn in focus moves to the next and returns None
           or if enter pressed returns the button string"""
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
                self.members.set_topfocus()
            else:
                return
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
                self.members.set_botfocus()
            elif self.devices_btn.focus:
                self.devices_btn.focus = False
                self.vectors_btn.focus = True
            elif self.messages_btn.focus:
                self.messages_btn.focus = False
                self.devices_btn.focus = True
            elif self.quit_btn.focus:
                self.quit_btn.focus = False
                self.messages_btn.focus = True
            else:
                return
            self.buttwin.clear()
            self.vectors_btn.draw()
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()
            self.buttwin.noutrefresh()
            curses.doupdate()
            return

        if chr(key) == "v" or chr(key) == "V":
            return "Vectors"
        if chr(key) == "d" or chr(key) == "D":
            return "Devices"
        if chr(key) == "m" or chr(key) == "M":
            return "Messages"
        if chr(key) == "q" or chr(key) == "Q":
            return "Quit"

        if key == 10:
            if self.vectors_btn.focus:
                return "Vectors"
            elif self.devices_btn.focus:
                return "Devices"
            elif self.messages_btn.focus:
                return "Messages"
            elif self.quit_btn.focus:
                return "Quit"



    async def inputs(self):
        "Gets inputs from the screen"

        try:
            self.stdscr.nodelay(True)
            while (not self.consoleclient.stop) and (self.consoleclient.screen is self):
                await asyncio.sleep(0)
                key = self.stdscr.getch()

                if key == -1:
                    continue

                if self.vectors_btn.focus or self.devices_btn.focus or self.messages_btn.focus or self.quit_btn.focus:
                    result = self.check_bottom_btn(key)
                    if result:
                        return result

                if self.members.focus:
                    # focus has been given to the members window which monitors its own inputs
                    key = await self.members.input()
                    if key in (32, 9, 261, 338, 258):   # go to next button
                        self.members.set_nofocus()
                        self.vectors_btn.focus = True
                        self.buttwin.clear()
                        self.vectors_btn.draw()
                        self.devices_btn.draw()
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                        curses.doupdate()
                    if key in (353, 260, 339, 259):   # go to prev button
                        self.members.set_nofocus()
                        self.quit_btn.focus = True
                        self.buttwin.clear()
                        self.vectors_btn.draw()
                        self.devices_btn.draw()
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                        curses.doupdate()



        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"





class MembersWin:

    "Used to display the vector members"

    def __init__(self, stdscr, consoleclient, vector):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()


        self.window = curses.newpad(50, self.maxcols)
        self.consoleclient = consoleclient
        self.client = consoleclient.client

        self.vector = vector
        self.vectorname = vector.name

        # pad lines depends on members, note this can be re-sized
        # using window.resize(nlines, ncols)

        self.topline = 0

        # dictionary of member name to member this vector owns
        members_dict = self.vector.members()

        # list of member names in alphabetic order
        self.membernames = sorted(members_dict.keys())

        # number of lines in a pad, assume four lines per member, with a minimum of 50
        self.padlines = max(50, len(self.membernames)*4)

        self.window = curses.newpad(self.padlines, self.maxcols)

        # create the member widgets
        try:
            self.memberwidgets = []
            for name in self.membernames:
                if self.vector.vectortype == "SwitchVector":
                    self.memberwidgets.append(widgets.SwitchMember(self.window, self.vector, name))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # this is True, if this widget is in focus
        self.focus = False

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols-1, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.topmore_btn.show = True
        self.topmore_btn.focus = False

        # botmorewin (1 line, full row, starting at self.maxrows - 3, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols-1, self.maxrows - 3, 0)
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.botmore_btn.show = True
        self.botmore_btn.focus = False

        # top more btn on 7th line ( coords 0 to 6 )
        # bot more btn on line (self.maxrows - 3) + 1
        # displaylines = (self.maxrows - 2) - 7  - 1

        self.displaylines = self.maxrows - 10

    def set_nofocus(self):
        self.focus = False
        for widget in self.memberwidgets:
            if widget.focus:
                widget.focus = False
                widget.draw()
                self.noutrefresh()
                return
        self.topmore_btn.focus = False
        self.botmore_btn.focus = False
        self.topmorewin.clear()
        self.botmorewin.clear()
        self.topmore_btn.draw()
        self.botmore_btn.draw()
        self.topmorewin.noutrefresh()
        self.botmorewin.noutrefresh()

    def set_topfocus(self):
        self.focus = True
        self.botmore_btn.focus = False
        self.botmore_btn.draw()
        self.botmorewin.noutrefresh()

        if self.topline:
            # self.topline is not zero, so topmore button must be shown
            # and with focus set
            self.topmore_btn.show = True
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
            self.topmorewin.noutrefresh()
        else:
            # self.topline is zero, so top member widget must be shown
            # and with focus set
            widget = self.memberwidgets[0]
            widget.focus = True
            self.draw()
            self.noutrefresh()


    def set_botfocus(self):
        self.focus = True
        self.topmore_btn.focus = False
        self.topmore_btn.draw()
        self.topmorewin.noutrefresh()

        botindex = self.widgetindex_bottom_displayed()
        if botindex == len(self.memberwidgets)-1:
            # last widget is displayed
            # set focus on bottom member widget
            widget = self.memberwidgets[botindex]
            widget.focus = True
            self.draw()
            self.noutrefresh()
        else:
            self.botmore_btn.show = True
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
            self.botmorewin.noutrefresh()


    def draw(self):
        self.window.clear()

        # self.memberwidgets is the list of widgets
        # get the number of lines the widgets take
        lines = 0
        for widget in self.memberwidgets:
            lines += widget.linecount

        # pad may need increasing if extra members have been added
        padlines = max(self.padlines, lines)
        if padlines != self.padlines:
            self.padlines = padlines
            self.window.resize(self.padlines, self.maxcols)
            self.topline = 0

        # draw the member widgets

        try:
            line = 0
            for memberwidget in self.memberwidgets:
                memberwidget.draw(line)
                line = memberwidget.endline + 1
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # Is the top of the pad being displayed?
        if self.topline:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # Is the bottom widget being displayed?
        botindex = self.widgetindex_bottom_displayed()
        if botindex == len(self.memberwidgets) -1:
            self.botmore_btn.show = False
        else:
            self.botmore_btn.show = True
        self.botmore_btn.draw()


    def noutrefresh(self):

        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.topline, 0, 7, 1, self.maxrows - 4, self.maxcols-2)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.topmorewin.noutrefresh()
        self.window.overwrite(self.stdscr, *coords)
        self.window.noutrefresh(*coords)
        self.botmorewin.noutrefresh()


    def widgetindex_in_focus(self):
        "Returns the memberwidget index which has focus, or None"
        for index,widget in enumerate(self.memberwidgets):
            if widget.focus:
                return index


    def widgetindex_bottom_displayed(self):
        "Return the memberwidget index being displayed at bottom of window"
        for index,widget in enumerate(self.memberwidgets):
            if widget.endline == self.topline + self.displaylines - 1:
                return index
            if widget.endline > self.topline + self.displaylines - 1:
                return index-1
        else:
            return len(self.memberwidgets) - 1


    def widgetindex_top_displayed(self):
        "Return the memberwidget index being displayed at top of window"
        for index,widget in enumerate(self.memberwidgets):
            if widget.startline >= self.topline:
                return index

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow


    async def input(self):
        "This window is in focus"
        self.stdscr.nodelay(True)
        while not self.consoleclient.stop:
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key in (32, 9, 261, 338, 258):   # go to next button
                if self.botmore_btn.focus:
                    return key
                # get the top widget being displayed
                topwidgetindex = self.widgetindex_top_displayed()
                if self.topmore_btn.focus:
                    self.topmore_btn.focus = False
                    self.topmore_btn.draw()
                    nextwidget = self.memberwidgets[topwidgetindex]
                    nextwidget.focus = True
                    nextwidget.draw()
                    self.noutrefresh()
                    curses.doupdate()
                    continue
                elif (widgetindex := self.widgetindex_in_focus()) is not None:
                    widget = self.memberwidgets[widgetindex]
                    # widget is the widget currently in focus
                    if widgetindex == len(self.memberwidgets) -1:
                        # last widget, so go on to the vector button by returning from this members window
                        widget.focus = False
                        widget.draw()
                        self.noutrefresh()
                        return key
                    if self.memberwidgets[widgetindex+1].endline > self.topline + self.displaylines - 1:
                        # next widget is still not displayed
                        if key == 9:
                            # tab key pressed, go to bottom more button
                            widget.focus = False
                            widget.draw()
                            self.botmore_btn.focus = True
                            self.botmore_btn.draw()
                            self.botmorewin.noutrefresh()
                        else:
                            # page/arrow pressed, scroll the window up
                            self.topline += 1
                            if not self.topmore_btn.show:
                                # top more button should be displayed
                                self.topmore_btn.show = True
                                self.topmore_btn.draw()
                                self.topmorewin.noutrefresh()
                            if self.botmore_btn.show:
                                botindex = self.widgetindex_bottom_displayed()
                                if botindex == len(self.memberwidgets)-1:
                                    # bottom more button should not be displayed
                                    self.botmore_btn.show = False
                                    self.botmore_btn.draw()
                                    self.botmorewin.noutrefresh()
                    else:
                        # set next widget in focus
                        widget.focus = False
                        widget.draw()
                        nextwidget = self.memberwidgets[widgetindex+1]
                        nextwidget.focus = True
                        nextwidget.draw()
                        # if nextwidget is the last widget, then do not show self.botmore_btn
                        if widgetindex+1 == len(self.memberwidgets)-1:
                            self.botmore_btn.show = False
                            self.botmorewin.clear()
                    self.noutrefresh()
                    curses.doupdate()
                    continue
            if key in (353, 260, 339, 259):   # go to prev button
                if self.topmore_btn.focus:
                    return key
                # get the bottom widget being displayed
                bottomwidgetindex = self.widgetindex_bottom_displayed()
                if self.botmore_btn.focus:
                    self.botmore_btn.focus = False
                    self.botmore_btn.draw()
                    prevwidget = self.memberwidgets[bottomwidgetindex]
                    prevwidget.focus = True
                    prevwidget.draw()
                    self.noutrefresh()
                    curses.doupdate()
                    continue
                elif (widgetindex := self.widgetindex_in_focus()) is not None:
                    widget = self.memberwidgets[widgetindex]
                    if widgetindex == 0:
                        # The topmost widget is in focus, remove focus
                        widget.focus = False
                        widget.draw()
                        self.topline = 0
                        # First widget, so go on to the quit button by returning from this members window
                        self.noutrefresh()
                        return key
                    if (not self.topline) and (widgetindex == 1):
                        # topline is zero, and set first widget in focus
                        widget.focus = False
                        widget.draw()
                        prevwidget = self.memberwidgets[0]
                        prevwidget.focus = True
                        prevwidget.draw()
                    elif self.memberwidgets[widgetindex-1].startline < self.topline:
                        # widget previous to current in focus widget is not fully displayed
                        if key == 353:
                            # shift tab pressed, jump to top more button
                            widget.focus = False
                            widget.draw()
                            self.topmore_btn.focus = True
                            self.topmore_btn.draw()
                            self.topmorewin.noutrefresh()
                        else:
                            # scroll the window down
                            self.topline -= 1
                            if not self.topline:
                                # if topline is zero, topmore button should not be shown
                                self.topmore_btn.show = False
                                self.topmore_btn.draw()
                                self.topmorewin.noutrefresh()
                            if not self.botmore_btn.show:
                                botindex = self.widgetindex_bottom_displayed()
                                if botindex != len(self.memberwidgets)-1:
                                    # bottom more button should be displayed
                                    self.botmore_btn.show = True
                                    self.botmore_btn.draw()
                                    self.botmorewin.noutrefresh()
                    else:
                        # set prev widget in focus
                        widget.focus = False
                        widget.draw()
                        prevwidget = self.memberwidgets[widgetindex-1]
                        prevwidget.focus = True
                        prevwidget.draw()
                    self.noutrefresh()
                    curses.doupdate()
                    continue
