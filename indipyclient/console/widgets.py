
import asyncio, curses


class Button:

    def __init__(self, stdscr, btntext, row, col):
        self.stdscr = stdscr
        self.btntext = btntext
        self.row = row
        self.col = col
        self.focus = False

    def draw(self):
        if self.focus:
            self.stdscr.addstr( self.row, self.col, "[" + self.btntext + "]", curses.A_REVERSE)
        else:
            self.stdscr.addstr( self.row, self.col, "[" + self.btntext + "]")


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

    def __init__(self, stdscr, groups):
        self.stdscr = stdscr
        self.groups = groups
        self.prev = "<<Prev]"
        self.next = "[Next>>"
        # active is a tuple of the group currently being shown
        # and the number in the current displayed list, 0 on the left
        self.active = (self.groups[0], 0)

    def draw(self):
        col = 2
        for number, group in enumerate(self.groups):
            grouptoshow = "["+group+"]"
            if number == self.active[1]:
                # active item
                self.stdscr.addstr(4, col, grouptoshow, curses.A_BOLD)
            else:
                self.stdscr.addstr(4, col, grouptoshow)
            col += len(grouptoshow) + 2
            if col+11 >= curses.COLS:
                self.stdscr.addstr(4, col, self.next)
                break


    def input():
        "Get group button pressed, or next or previous"

        self.stdscr.nodelay(True)
        while not self.consoleclient.stop:
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
