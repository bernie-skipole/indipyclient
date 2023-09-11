
import asyncio, curses, sys


class Button:

    def __init__(self, window, btntext, row, col):
        self.window = window
        self.btntext = btntext
        self.row = row
        self.col = col
        self.focus = False

    def draw(self):
        if self.focus:
            self.window.addstr( self.row, self.col, "[" + self.btntext + "]", curses.A_REVERSE)
        else:
            self.window.addstr( self.row, self.col, "[" + self.btntext + "]")



def drawmessage(window, message, bold = False):
    """Shows message, message is either a text string, or a tuple of (timestamp, message text)"""
    if isinstance(message, str):
        rxmessage = "    " + message
    else:
        rxmessage = "    " + message[0].isoformat(sep='T')[11:21] + "  " + message[1]

    if len(rxmessage) > curses.COLS:
        messagetoshow = rxmessage[:curses.COLS-1]
    else:
        messagetoshow = rxmessage + " "*(curses.COLS - len(rxmessage) - 1)

    if bold:
        window.addstr(0, 0, messagetoshow, curses.A_BOLD)
    else:
        window.addstr(0, 0, messagetoshow)


class Groups:

    def __init__(self, stdscr, window, consoleclient):
        self.stdscr = stdscr
        self.window = window
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
                return self.groupfocus, 10
            if chr(key) in ("q", "Q", "m", "M", "d", "D"):
                return None, key
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
                    return None, 258   # treat as 258 down arrow key
                # go to the next group
                if self.groupfocus == self.groups[-1]:
                    # At the last group, cannot go further
                    return None, key
                indx = self.groups.index(self.groupfocus)
                if self.togroup and (indx+1 > self.togroup):
                    # next choice is beyond togroup
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
                    return None, 258   # treat as 258 down arrow key
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
                if indx and (indx == self.fromgroup):
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
                if indx-1 < 0:
                    return None, key
                self.groupfocus = self.groups[indx-1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                continue
            if key in (338, 258):          # 338 page down, 258 down arrow
                return None, key
        return None, -1
