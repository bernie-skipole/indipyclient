
import asyncio, curses, sys


class Button:

    def __init__(self, stdscr, btntext, row, col):
        self.stdscr = stdscr
        self.btntext = btntext
        self.row = row
        self.col = col
        self._focus = False

    def draw(self):
        if self._focus:
            self.stdscr.addstr( self.row, self.col, "[" + self.btntext + "]", curses.A_REVERSE)
        else:
            self.stdscr.addstr( self.row, self.col, "[" + self.btntext + "]")

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        self._focus = value
        self.draw()
        self.stdscr.refresh()



def drawmessage(stdscr, message, bold = False):
    """Shows message on line 2, message is either a text string, or a tuple of (timestamp, message text)"""
    if isinstance(message, str):
        rxmessage = "    " + message
    else:
        rxmessage = "    " + message[0].isoformat(sep='T')[11:21] + "  " + message[1]
    if len(rxmessage) > curses.COLS:
        messagetoshow = rxmessage[:curses.COLS]
    else:
        messagetoshow = rxmessage + " "*(curses.COLS - len(rxmessage))
    if bold:
        stdscr.addstr(2, 0, messagetoshow, curses.A_BOLD)
    else:
        stdscr.addstr(2, 0, messagetoshow)



class Groups:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.groups = []
        self.prev = "<<Prev]"
        self.next = "[Next>>"
        # active is the name of the group currently being shown
        self.active = None
        # this is True, if this widget is in focus
        self._focus = False
        # this is set to the group in focus, if any
        self.groupfocus = None

        # the horizontal display of group buttons may not hold all the buttons
        # give the index of self.groups from and to
        self.from = 0
        self.to = 0
        self.nextcol = 0


    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        self._focus = value
        if value:
            self.groupfocus = self.groups[0]
        else:
            self.groupfocus = None
        self.draw()
        self.stdscr.refresh()


    def set_groups(self, groups):
        self.groups = groups.copy()
        self.from = 0
        self.to = len(self.groups) - 1
        if self.active is None:
            self.active = self.groups[0]
        elif self.active not in self.groups:
            self.active = self.groups[0]

    def draw(self):
        col = 2
        for indx, group in enumeraste(self.groups):
            if indx < self.from:
                continue
            grouptoshow = "["+group+"]"
            if self.active is None:
                self.active = self.groups[0]
            if group == self.active:
                if self.groupfocus == group:
                    # group in focus
                    self.stdscr.addstr(4, col, grouptoshow, curses.A_REVERSE)
                else:
                    # active item
                    self.stdscr.addstr(4, col, grouptoshow, curses.A_BOLD)
            else:
                if self.groupfocus == group:
                    # group in focus
                    self.stdscr.addstr(4, col, grouptoshow, curses.A_REVERSE)
                else:
                    self.stdscr.addstr(4, col, grouptoshow)
            col += len(grouptoshow) + 2
            if col+11 >= curses.COLS:
                self.nextcol = col
                self.stdscr.addstr(4, col, self.next)
                self.to = indx
                break

    def drawnext(self):

        ############# to do


    async def input(self):
        "Get group button pressed, or next or previous"
        self.stdscr.nodelay(True)
        while not self.consoleclient.stop:
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key == 10:
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
                # go to the next group
                indx = self.groups.index(self.groupfocus)
                if indx+1 >= len(self.groups):
                    return None, key
                if self.to and (indx+1 >= self.to):
                    # highlight next key
                    self.drawnext()
                    continue
                self.groupfocus = self.groups[indx+1]
                self.draw()
                self.stdscr.refresh()
                continue
            if key in (353, 260):   # 353 shift tab, 260 left arrow
                # go to the previous group
                indx = self.groups.index(self.groupfocus)
                if indx-1 < 0:
                    return None, key
                self.groupfocus = self.groups[indx-1]
                self.draw()
                self.stdscr.refresh()
                continue
            if key in (338, 258):          # 338 page down, 258 down arrow
                return None, key
        return None, -1
