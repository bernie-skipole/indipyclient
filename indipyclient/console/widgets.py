
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
