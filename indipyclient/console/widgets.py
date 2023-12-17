
import asyncio, curses, sys

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise



class Button:

    def __init__(self, window, btntext, row, col):
        self.window = window
        self.btntext = btntext
        self.row = row
        self.col = col
        self._focus = False
        self._show = True
        self.bold = False

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
        elif self.bold:
            self.window.addstr( self.row, self.col, "[" + self.btntext + "]", curses.A_BOLD)
        else:
            self.window.addstr( self.row, self.col, "[" + self.btntext + "]")

    def alert(self):
        "draw the button with a red background and INVALID Message"
        if not self._show:
            return
        self.window.addstr( self.row, self.col, "[" + self.btntext + "] INVALID!", curses.color_pair(3))

    def ok(self):
        "draw the button with a green background and OK Message"
        if not self._show:
            return
        self.window.addstr( self.row, self.col, "[" + self.btntext + "] OK!", curses.color_pair(1))



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

    def __init__(self, stdscr, consoleclient, window, pad, vector, name):

        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.window = window
        self.pad = pad
        self.vector = vector
        self.name = name
        self.maxrows, self.maxcols = self.window.getmaxyx()
        self.startline = 0
        # linecount is the number of lines this widget takes up,
        # including an end empty line
        self.linecount = 4
        self.name_btn = Button(window, self.name, 0, 1)
        self._focus = False
        # if this is set to True, the input coroutine will stop
        self._close = False

    def close(self):
        "Sets _close to True, which stops the input co-routine"
        self._close = True

    def value(self):
        return self.vector[self.name]

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        self._focus = value
        self.name_btn.focus = value


    @property
    def endline(self):
        "self.endline is the empty line after the vector"
        return self.startline + self.linecount - 1

    def update(self, event):
        "An event affecting this widget has occurred"
        pass

    def draw(self, startline=None):
        if not startline is None:
            self.startline = startline
        self.name_btn.row = self.startline
        self.name_btn.draw()

    async def input(self):
        "This widget is in focus, and monitors inputs"
        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
            return key
        return -1


#<!ATTLIST defSwitchVector
# device %nameValue;        #REQUIRED name of Device
# name %nameValue;          #REQUIRED name of Property
# label %labelValue;        #IMPLIED  GUI label, use name by default
# group %groupTag;          #IMPLIED  Property group membership, blank by default
# state %propertyState;     #REQUIRED current state of Property
# perm %propertyPerm;       #REQUIRED ostensible Client controlability
# rule %switchRule;         #REQUIRED hint for GUI presentation
# timeout %numberValue;     #IMPLIED worse-case time, 0 default, N/A for ro
# timestamp %timeValue      #IMPLIED moment when these data were valid
# message %textValue        #IMPLIED commentary


class SwitchMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, pad, vector, name):
        super().__init__(stdscr, consoleclient, window, pad, vector, name)
        # create  ON, OFF buttons
        self.on = Button(window, 'ON', 0, 0)
        self.on.bold = True if self.value() == "On" else False
        self.on.show = False
        self.off = Button(window, 'OFF', 0, 0)
        self.off.show = False
        self.submit = Button(window, 'Submit', 0, 0)
        self.submit.show = False
        self.linecount = 3

    def update(self, event):
        "An event affecting this widget has occurred"
        self.draw()

    def draw(self, startline=None):
        super().draw(startline)
        # draw the On or Off value
        self.window.addstr( self.startline+1, self.maxcols-20, self.value(), curses.A_BOLD )
        # draw the label
        self.window.addstr( self.startline+1, 1, self.vector.memberlabel(self.name) )
        #self.window.addstr( self.endline, 1, "----")
        if self.vector.perm == "ro":
            return
        # Draw the on/off buttons
        self.on.row = self.startline+1
        self.on.col = self.maxcols-15
        self.on.show = True
        self.on.draw()
        self.off.bold = not self.on.bold
        self.off.row = self.startline+1
        self.off.col = self.maxcols-10
        self.off.show = True
        self.off.draw()


    def newvalue(self):
        if self.on.bold:
            return "On"
        return "Off"

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        self._focus = value
        self.name_btn.focus = value
        self.on.focus = False
        self.off.focus = False

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def input(self):
        "This widget is in focus, and monitors inputs"
        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
            if self.name_btn.focus:
                if key in (353, 260, 339, 338, 259, 258):  # 353 shift tab, 260 left arrow, 339 page up, 338 page down, 259 up arrow, 258 down arrow
                    # go to next or previous member widget
                    return key
                if key in (32, 9, 261, 10):     # 32 space, 9 tab, 261 right arrow, 10 return
                    # go to on button
                    self.name_btn.focus = False
                    self.on.focus = True
                    self.name_btn.draw()
                    self.on.draw()
                else:
                    # ignore any other key
                    continue
                self.pad.noutrefresh()
                curses.doupdate()
                continue
            elif self.on.focus:
                if key == 10:                  # 10 return
                    # set on key as bold, off key as standard
                    self.on.bold = True
                    self.off.bold = False
                    self.on.draw()
                    self.off.draw()
                elif key in (338, 339, 258, 259):   # 338 page down, 258 down arrow, 339 page up, 259 up arrow
                    # go to next or previous member widget
                    self.on.focus = False
                    self.on.draw()
                    self.name_btn.focus = True
                    self.name_btn.draw()
                    return key
                elif key in (353, 260): # 353 shift tab, 260 left arrow
                    # back to name_btn
                    self.name_btn.focus = True
                    self.on.focus = False
                    self.name_btn.draw()
                    self.on.draw()
                elif key in (32, 9, 261):  # 32 space, 9 tab, 261 right arrow
                    # move to off btn
                    self.on.focus = False
                    self.on.draw()
                    self.off.focus = True
                    self.off.draw()
                else:
                    continue
                self.pad.noutrefresh()
                curses.doupdate()
                continue
            elif self.off.focus:
                if key == 10:                      # 10 return
                    # set off key as bold, on key as standard
                    self.off.bold = True
                    self.on.bold = False
                    self.off.draw()
                    self.on.draw()
                elif key in (339, 259):   # 339 page up, 259 up arrow
                    # go to previous member widget or scroll pad
                    self.off.focus = False
                    self.off.draw()
                    self.name_btn.focus = True
                    self.name_btn.draw()
                    return key
                elif key == 261:   # 261 right arrow
                    # go to name_btn
                    self.off.focus = False
                    self.off.draw()
                    self.name_btn.focus = True
                    self.name_btn.draw()
                elif key in (32, 9, 338, 339, 258, 259):   # 32 space, 9 tab, 338 page down, 258 down arrow
                    # go to next widget or scroll pad
                    return key
                elif key in (353, 260):  # 353 shift tab, 260 left arrow
                    # back to on btn
                    self.off.focus = False
                    self.off.draw()
                    self.on.focus = True
                    self.on.draw()
                else:
                    continue
                self.pad.noutrefresh()
                curses.doupdate()
                continue
        return -1
