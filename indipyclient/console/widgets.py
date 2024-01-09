
import asyncio, curses, sys

from decimal import Decimal

from curses import ascii

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


class BaseMember:

    def __init__(self, stdscr, consoleclient, window, memberswin, vector, name):

        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.window = window
        self.memberswin = memberswin
        self.vector = vector
        self.name = name
        membersdict = self.vector.members()
        self.member = membersdict[name]
        # self.member is a propertymember
        self.maxrows, self.maxcols = self.window.getmaxyx()
        self.startline = 0
        # linecount is the number of lines this widget takes up,
        # including an end empty line
        self.linecount = 4
        self.name_btn = Button(window, self.name, 0, 0)
        self._focus = False
        # if this is set to True, the input coroutine will stop
        self._close = False

    def close(self):
        "Sets _close to True, which stops the input co-routine"
        self._close = True

    def value(self):
        return self.vector[self.name]

    def reset(self):
        "Reset the widget removing any value updates, called by cancel"
        pass

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
        self.name_btn.row = self.startline+1
        self.name_btn.draw()

    async def input(self):
        "This widget is in focus, and monitors inputs"
        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            if not self.vector.enable:
                return
            key = self.stdscr.getch()
            if key == -1:
                continue
            return key
        return -1


class SwitchMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, memberswin, vector, name):
        super().__init__(stdscr, consoleclient, window, memberswin, vector, name)
        # create  ON, OFF buttons
        self.on = Button(window, 'ON', 0, 0)
        self.on.bold = True if self.value() == "On" else False
        self.on.show = False
        self.off = Button(window, 'OFF', 0, 0)
        self.off.bold = not self.on.bold
        self.off.show = False
        self.submit = Button(window, 'Submit', 0, 0)
        self.submit.show = False
        self.linecount = 3

    def reset(self):
        "Reset the widget removing any value updates, called by cancel"
        if self.vector.perm == "ro":
            return
        # Draw the on/off buttons
        self.on.bold = True if self.value() == "On" else False
        self.on.row = self.startline+1
        self.on.col = self.maxcols-15
        self.on.show = True
        self.on.draw()
        self.off.bold = not self.on.bold
        self.off.row = self.startline+1
        self.off.col = self.maxcols-10
        self.off.show = True
        self.off.draw()

    def draw(self, startline=None):
        super().draw(startline)
        # draw the On or Off value
        self.window.addstr( self.startline+1, self.maxcols-20, self.value(), curses.A_BOLD )
        # draw the label
        self.window.addstr( self.startline, 1, self.vector.memberlabel(self.name), curses.A_BOLD )
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
            if not self.vector.enable:
                return
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
                    self.memberswin.widgetsrefresh()
                    curses.doupdate()
                # ignore any other key
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
                self.memberswin.widgetsrefresh()
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
                self.memberswin.widgetsrefresh()
                curses.doupdate()
                continue
        return -1


class LightMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, memberswin, vector, name):
        super().__init__(stdscr, consoleclient, window, memberswin, vector, name)
        self.linecount = 3


    def draw(self, startline=None):
        super().draw(startline)
        # draw the light value
        lowervalue = self.value().lower()
        if lowervalue == "idle":
            text = "  Idle  "
        elif lowervalue == "ok":
            text = "  OK    "
        elif lowervalue == "busy":
            text = "  Busy  "
        elif lowervalue == "alert":
            text = "  Alert "
        else:
            return
        self.window.addstr(self.startline+1, self.maxcols-20, text, self.consoleclient.color(lowervalue))
        # draw the label
        self.window.addstr( self.startline, 1, self.vector.memberlabel(self.name), curses.A_BOLD )


#   <!ATTLIST defNumberVector
#   device %nameValue; #REQUIRED        name of Device
#   name %nameValue; #REQUIRED          name of Property
#   label %labelValue; #IMPLIED         GUI label, use name by default
#   group %groupTag; #IMPLIED           Property group membership, blank by default
#   state %propertyState; #REQUIRED     current state of Property
#   perm %propertyPerm; #REQUIRED       ostensible Client controlability
#   timeout %numberValue; #IMPLIED      worse-case time to affect, 0 default, N/A for ro
#   timestamp %timeValue #IMPLIED       moment when these data were valid
#   message %textValue #IMPLIED         commentary

#   Define one member of a number vector
#   <!ATTLIST defNumber
#   name %nameValue; #REQUIRED          name of this number element
#   label %labelValue; #IMPLIED         GUI label, or use name by default
#   format %numberFormat; #REQUIRED     printf-style format for GUI display
#   min %numberValue; #REQUIRED         minimal value
#   max %numberValue; #REQUIRED         maximum value, ignore if min == max
#   step %numberValue; #REQUIRED        allowed increments, ignore if 0


class NumberMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, memberswin, vector, name):
        super().__init__(stdscr, consoleclient, window, memberswin, vector, name)
        self.linecount = 3
        if self.vector.perm == "ro":
            self.linecount = 3
        else:
            self.linecount = 4
        # the newvalue to be edited and sent
        self._newvalue = self.vector.getformattedvalue(self.name)

    def newvalue(self):
        value = self._newvalue.strip()
        if len(value) > 16:
            value = value[:16]
        return value


    def reset(self):
        "Reset the widget removing any value updates, called by cancel"
        if self.vector.perm == "ro":
            return
        self._newvalue = self.member.getformattedvalue()
        textnewvalue = self.newvalue().ljust(16)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-21, "[" + textnewvalue+ "]" )

    def draw(self, startline=None):
        super().draw(startline)
        # draw the number value
        text = self.member.getformattedvalue().strip()
        if len(text) > 16:
            text = text[:16]
        self.window.addstr(self.startline+1, self.maxcols-20, text, curses.A_BOLD)
        # draw the label
        self.window.addstr( self.startline, 1, self.vector.memberlabel(self.name), curses.A_BOLD )
        if self.vector.perm == "ro":
            return

        # the length of the editable number field is 16
        textnewvalue = self.newvalue().ljust(16)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-21, "[" + textnewvalue+ "]" )


    async def input(self):
        "This widget is in focus, and monitors inputs"
        if self.vector.perm == "ro":
            return -1
        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            if not self.vector.enable:
                return
            key = self.stdscr.getch()
            if key == -1:
                continue
            if self.name_btn.focus:
                if key in (353, 260, 339, 338, 259, 258):  # 353 shift tab, 260 left arrow, 339 page up, 338 page down, 259 up arrow, 258 down arrow
                    # go to next or previous member widget
                    return key
                if key in (32, 9, 261, 10):     # 32 space, 9 tab, 261 right arrow, 10 return
                    # text input here
                    await self.numberinput()
                    if not self.vector.enable:
                        return
                    return 9
                # ignore any other key


    async def numberinput(self):
        "Input a number value, set it into self._newvalue as a string"
        # highlight editable field has focus
        self.name_btn.focus = False
        self.name_btn.draw()
        # set brackets of editable field in bold
        self.window.addstr( self.startline+2, self.maxcols-21, "[", curses.A_BOLD )
        self.window.addstr( self.startline+2, self.maxcols-4, "]", curses.A_BOLD )
        self.memberswin.widgetsrefresh()
        curses.doupdate()
        # set cursor visible
        curses.curs_set(1)
        # pad starts at self.stdscr row 7, col 1
                                                  # row             startcol          endcol            start text
        editstring = EditString(self.stdscr, 7+self.startline+2, 1+self.maxcols-20, 1+self.maxcols-5, self.newvalue())

        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            if not self.vector.enable:
                return
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key == 10:
                # a number self._newvalue is being submitted
                if not self.checknumber():
                    # number not valid, start again by creating a new instance of EditString and self._newvalue reset
                    editstring = EditString(self.stdscr, 7+self.startline+2, 1+self.maxcols-20, 1+self.maxcols-5, self.newvalue())
                    continue
                else:
                    # self._newvalue is correct, return with this value to be submitted
                    curses.curs_set(0)
                    return
            # key is to be inserted into the editable field, and self._newvalue updated
            value = editstring.getnumber(key)
            self._newvalue = value.strip()
            self.window.addstr( self.startline+2, self.maxcols-20, value )
            self.memberswin.widgetsrefresh()
            editstring.movecurs()
            curses.doupdate()

    def checknumber(self):
        "Return True if self._newvalue is ok"
        # self._newvalue is the new value input
        try:
            newfloat = self.member.getfloat(self._newvalue)
        except (ValueError, TypeError):
            # reset self._newvalue
            self._newvalue = self.member.getformattedvalue()
            # draw the value to be edited
            self.window.addstr( self.startline+2, self.maxcols-20, self.newvalue().ljust(16) )
            self.memberswin.widgetsrefresh()
            curses.doupdate()
            return False
        # check step, and round newfloat to nearest step value
        stepvalue = self.member.getfloat(self.member.step)
        minvalue = self.member.getfloat(self.member.min)
        if stepvalue:
            stepvalue = Decimal(str(stepvalue))
            difference = newfloat - minvalue
            newfloat = minvalue + float(int(Decimal(str(difference)) / stepvalue) * stepvalue)
        # check not less than minimum
        if newfloat < minvalue:
            # reset self._newvalue to be the minimum, and accept this
            self._newvalue = self.member.getformattedstring(minvalue)
            # draw the value to be edited
            self.window.addstr( self.startline+2, self.maxcols-20, self.newvalue().ljust(16) )
            self.memberswin.widgetsrefresh()
            curses.doupdate()
            return True
        if self.member.max != self.member.min:
            maxvalue = self.member.getfloat(self.member.max)
            if newfloat > maxvalue:
                # reset self._newvalue to be the maximum, and accept this
                self._newvalue = self.member.getformattedstring(maxvalue)
                # draw the value to be edited
                self.window.addstr( self.startline+2, self.maxcols-20, self.newvalue().ljust(16) )
                self.memberswin.widgetsrefresh()
                curses.doupdate()
                return True
        # reset self._newvalue to the correct format, and accept this
        self._newvalue = self.member.getformattedstring(newfloat)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-20, self.newvalue().ljust(16) )
        self.memberswin.widgetsrefresh()
        curses.doupdate()
        return True


# <!ATTLIST defTextVector
# device %nameValue; #REQUIRED   name of Device
# name %nameValue; #REQUIRED     name of Property
# label %labelValue; #IMPLIED    GUI label, use name by default
# group %groupTag; #IMPLIED      Property group membership, blank by default
# state %propertyState; #REQUIRED  current state of Property
# perm %propertyPerm; #REQUIRED    ostensible Client controlability
# timeout %numberValue; #IMPLIED   worse-case time to affect, 0 default, N/A for ro
# timestamp %timeValue #IMPLIED    moment when these data were valid
# message %textValue #IMPLIED      commentary

# Define one member of a text vector
# <!ELEMENT defText %textValue >
# <!ATTLIST defText
# name %nameValue; #REQUIRED
# label %labelValue; #IMPLIED

class TextMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, memberswin, vector, name):
        super().__init__(stdscr, consoleclient, window, memberswin, vector, name)
        self.linecount = 3
        if self.vector.perm == "ro":
            self.linecount = 3
        else:
            self.linecount = 4
        # the newvalue to be edited and sent
        self._newvalue = self.vector[self.name]

    def newvalue(self):
        value = self._newvalue.strip()
        if len(value) > 30:
            value = value[:30]
        return value


    def reset(self):
        "Reset the widget removing any value updates, called by cancel"
        if self.vector.perm == "ro":
            return
        self._newvalue = self.member.membervalue
        textnewvalue = self.newvalue().ljust(30)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-35, "[" + textnewvalue+ "]" )

    def draw(self, startline=None):
        super().draw(startline)
        # draw the text
        text = self.member.membervalue.strip()
        if len(text) > 30:
            text = text[:30]
        self.window.addstr(self.startline+1, self.maxcols-34, text, curses.A_BOLD)
        # draw the label
        self.window.addstr( self.startline, 1, self.vector.memberlabel(self.name), curses.A_BOLD )
        if self.vector.perm == "ro":
            return

        # the length of the editable text field is 30
        textnewvalue = self.newvalue().ljust(30)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-35, "[" + textnewvalue+ "]" )


    async def input(self):
        "This widget is in focus, and monitors inputs"
        if self.vector.perm == "ro":
            return -1
        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            if not self.vector.enable:
                return
            key = self.stdscr.getch()
            if key == -1:
                continue
            if self.name_btn.focus:
                if key in (353, 260, 339, 338, 259, 258):  # 353 shift tab, 260 left arrow, 339 page up, 338 page down, 259 up arrow, 258 down arrow
                    # go to next or previous member widget
                    return key
                if key in (32, 9, 261, 10):     # 32 space, 9 tab, 261 right arrow, 10 return
                    # text input here
                    await self.textinput()
                    if not self.vector.enable:
                        return
                    return 9
                # ignore any other key


    async def textinput(self):
        "Input text, set it into self._newvalue"
        # highlight editable field has focus
        self.name_btn.focus = False
        self.name_btn.draw()
        # set brackets of editable field in bold
        self.window.addstr( self.startline+2, self.maxcols-35, "[", curses.A_BOLD )
        self.window.addstr( self.startline+2, self.maxcols-4, "]", curses.A_BOLD )
        self.memberswin.widgetsrefresh()
        curses.doupdate()
        # set cursor visible
        curses.curs_set(1)
        # pad starts at self.stdscr row 7, col 1
                                                  # row             startcol          endcol            start text
        editstring = EditString(self.stdscr, 7+self.startline+2, 1+self.maxcols-34, 1+self.maxcols-5, self.newvalue())

        while (not self.consoleclient.stop) and (not self._close):
            await asyncio.sleep(0)
            if not self.vector.enable:
                return
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key == 10:
                # aself._newvalue is being submitted
                if not self.checktext():
                    # text not valid, start again by creating a new instance of EditString and self._newvalue reset
                    editstring = EditString(self.stdscr, 7+self.startline+2, 1+self.maxcols-34, 1+self.maxcols-5, self.newvalue())
                    continue
                else:
                    # self._newvalue is correct, return with this value to be submitted
                    curses.curs_set(0)
                    return
            # key is to be inserted into the editable field, and self._newvalue updated
            value = editstring.gettext(key)
            self._newvalue = value.strip()
            self.window.addstr( self.startline+2, self.maxcols-34, value )
            self.memberswin.widgetsrefresh()
            editstring.movecurs()
            curses.doupdate()

    def checktext(self):
        "Return True if self._newvalue is ok"
        return True
        # reset self._newvalue to the correct format, and accept this
        self._newvalue = self.member.membervalue.strip()
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-34, self.newvalue().ljust(16) )
        self.memberswin.widgetsrefresh()
        curses.doupdate()
        return True


class EditString():

    def __init__(self, stdscr, row, startcol, endcol, text):
        "Class to input text"
        self.stdscr = stdscr
        self.row = row
        self.startcol = startcol
        self.endcol = endcol
        self.length = endcol - startcol + 1
        self.text = text.strip()
        if len(self.text) > self.length:
            self.text = self.text[:self.length]
        # put curser at end of text
        self.stringpos = len(self.text)

        # pad text with right hand spaces
        self.text = self.text.ljust(self.length)
        self.movecurs()

    def insertch(self, ch):
        "Insert a character at stringpos"
        if self.stringpos >= self.length:
            # stringpos must be less than the length
            return
        self.text = self.text[:self.stringpos] + ch + self.text[self.stringpos:-1]
        self.stringpos += 1

    def delch(self):
        "delete character at stringpos-1"
        if not self.stringpos:
            # stringpos must be greater than zero
            return
        self.text = self.text[:self.stringpos-1] + self.text[self.stringpos:] + " "
        self.stringpos -= 1

    def movecurs(self):
        self.stdscr.move(self.row, self.startcol+self.stringpos)
        self.stdscr.refresh()

    def gettext(self, key):
        "called with each keypress, returns new text"
        if ascii.isprint(key):
            if self.stringpos >= self.length:
                # at max length, return
                return self.text
            ch = chr(key)
            self.insertch(ch)
        elif key>255:
            # control character
            if ((key == curses.KEY_DC) or (key == curses.KEY_BACKSPACE)) and self.stringpos:
                # delete character (self.stringpos cannot be zero)
                self.delch()
            elif (key == curses.KEY_LEFT) and self.stringpos:
                # move cursor left (self.stringpos cannot be zero)
                self.stringpos -= 1
            elif (key == curses.KEY_RIGHT) and (self.stringpos < self.length):
                # move cursor right
                self.stringpos += 1
        return self.text

    def getnumber(self, key):
        "called with each keypress, returns new number string"
        if ascii.isdigit(key):
            if self.stringpos >= self.length:
                # at max length, return
                return self.text
            ch = chr(key)
            self.insertch(ch)
        elif ascii.isprint(key):
            if self.stringpos >= self.length:
                # at max length, return
                return self.text
            ch = chr(key)
            if ch in (".", " ", ":", ";", "-", "+"):
                self.insertch(ch)
        elif key>255:
            # control character
            if ((key == curses.KEY_DC) or (key == curses.KEY_BACKSPACE)) and self.stringpos:
                # delete character (self.stringpos cannot be zero)
                self.delch()
            elif (key == curses.KEY_LEFT) and self.stringpos:
                # move cursor left (self.stringpos cannot be zero)
                self.stringpos -= 1
            elif (key == curses.KEY_RIGHT) and (self.stringpos < self.length):
                # move cursor right
                self.stringpos += 1
        return self.text
