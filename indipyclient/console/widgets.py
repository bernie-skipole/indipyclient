
import asyncio, curses, sys


class Button:

    def __init__(self, window, btntext, row, col):
        self.window = window
        self.btntext = btntext
        self.row = row
        self.col = col
        self._focus = False
        self.show = True


    @property
    def focus(self):
        if not self._focus:
            return False
        if not self.show:
            self._focus = False
        return self._focus

    @focus.setter
    def focus(self, value):
        if not self.show:
            self._focus = False
            return
        self._focus = value


    def draw(self):
        if not self.show:
            return
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


