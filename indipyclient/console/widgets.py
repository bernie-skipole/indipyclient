
import asyncio, curses, sys


class Button:

    def __init__(self, window, btntext, row, col):
        self.window = window
        self.btntext = btntext
        self.row = row
        self.col = col
        self._focus = False
        self._show = True


    @property
    def show(self):
        return self._show

    @show.setter
    def show(self, value):
        # setting show False, also sets focus False
        if not value:
            self._focus = False
        self._show = value


    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if not self._show:
            # focus can only be set if show is True
            return
        self._focus = value


    def draw(self):
        if not self._show:
            self.window.addstr( self.row, self.col, " "*len(self.btntext) + "  ")
            return
        if self._focus:
            self.window.addstr( self.row, self.col, "[" + self.btntext + "]", curses.A_REVERSE)
        else:
            self.window.addstr( self.row, self.col, "[" + self.btntext + "]")



def drawmessage(window, message, bold = False, maxcols=None):
    """Shows message, message is either a text string, or a tuple of (timestamp, message text)"""
    window.clear()
    if not maxcols:
        maxcols = curses.COLS
    if isinstance(message, str):
        rxmessage = "    " + message
    else:
        rxmessage = "    " + message[0].isoformat(sep='T')[11:21] + "  " + message[1]

    if len(rxmessage) > maxcols:
        messagetoshow = rxmessage[:maxcols-1]
    else:
        messagetoshow = rxmessage + " "*(maxcols - len(rxmessage) - 1)

    if bold:
        window.addstr(0, 0, messagetoshow, curses.A_BOLD)
    else:
        window.addstr(0, 0, messagetoshow)


def draw_timestamp_state(consoleclient, window, vector, maxcols=None):
    "Adds the vector timestamp, and its state to the window"
    window.clear()
    if not maxcols:
        maxcols = curses.COLS
    state = vector.state
    timestamp = vector.timestamp.isoformat(sep='T')[11:21]
    window.addstr(0, 1, timestamp)

    lowerstate = state.lower()
    if lowerstate == "idle":
        text = "  Idle  "
    elif lowerstate == "ok":
        text = "  OK    "
    elif lowerstate == "busy":
        text = "  Busy  "
    elif lowerstate == "alert":
        text = "  Alert "
    else:
        return
    window.addstr(0, maxcols - 20, text, consoleclient.color(state))


#Define one member of a number vector
#<!ELEMENT defNumber %numberValue >
#<!ATTLIST defNumber
#name %nameValue; #REQUIRED
#label %labelValue; #IMPLIED
#format %numberFormat; #REQUIRED
#min %numberValue; #REQUIRED
#max %numberValue; #REQUIRED
#step %numberValue; #REQUIRED


class BaseMember:

    def __init__(self, window, startline):
        self.window = window
        self.startline = startline
        self.linecount
        self.col = 1


    @property
    def endline(self):
        "self.endline is the empty line after the vector"
        return self.startline + self.linecount

    def draw(self):
        self.window.addstr( self.row, self.col, "[" + self.btntext + "]")
