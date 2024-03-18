
import asyncio, curses, sys, pathlib, time

from decimal import Decimal

from curses import ascii

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise


def shorten(text, width=0, placeholder="..."):
    "Shorten text"
    if not width:
        return text
    if len(text)<=width:
        return text
    if width <= len(placeholder):
        return placeholder[:width]
    return text[:width - len(placeholder)] + placeholder


def drawmessage(window, message, bold=False, maxcols=None):
    """Shows message, message is either a text string, or a tuple of (timestamp, message text)"""
    window.clear()
    if not maxcols:
        maxcols = curses.COLS
    maxcols = maxcols - 5
    if not isinstance(message, str):
        message = message[0].isoformat(sep='T')[11:21] + "  " + message[1]

    if len(message) > maxcols:
        messagetoshow = "    " + shorten(message, width=maxcols, placeholder="...")
    else:
        messagetoshow = "    " + message.ljust(maxcols)

    if bold:
        window.addstr(0, 0, messagetoshow, curses.A_BOLD)
    else:
        window.addstr(0, 0, messagetoshow)


def draw_timestamp_state(consoleclient, window, vector):
    "Adds the vector timestamp, and its state to the window"
    maxrows, maxcols = window.getmaxyx()
    window.clear()

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



class Button:

    def __init__(self, window, btntext, row, col, btnlen=None, onclick=None):
        self.window = window
        self.btntext = btntext
        self.row = row
        self.col = col
        self.onclick = onclick
        self._focus = False
        self._show = True
        self.bold = False
        if btnlen:
            self.btnlen = btnlen
        else:
            # no btnlen given
            self.btnlen = len(self.btntext) + 2

        originrow, origincol = self.window.getbegyx()
        self.fieldrow = originrow+self.row
        self.startcol = origincol + self.col
        self.endcol = self.startcol + self.btnlen

    def __contains__(self, mouse):
        "Returns True if the mouse y, x are within this field"
        if not self._show:
            return False
        if mouse[0] != self.fieldrow:
            return False
        if mouse[1] < self.startcol:
            return False
        if mouse[1] < self.endcol:
            return True
        return False

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

    def text(self):
        "pad out the text to be drawn"
        if len(self.btntext) == self.btnlen-2:
            return self.btntext
        if len(self.btntext) > self.btnlen-2:
            return shorten(self.btntext, width=self.btnlen-2, placeholder="...")
        spaces = self.btnlen-2-len(self.btntext)
        front = spaces//2
        back = spaces-front
        return " "*front + self.btntext + " "*back


    def draw(self):
        if not self._show:
            self.window.addstr( self.row, self.col, " "*self.btnlen)
            return
        if self._focus:
            self.window.addstr( self.row, self.col, f"[{self.text()}]", curses.A_REVERSE)
        elif self.bold:
            self.window.addstr( self.row, self.col, f"[{self.text()}]", curses.A_BOLD)
        else:
            self.window.addstr( self.row, self.col, f"[{self.text()}]")

    def alert(self):
        "draw the button with a red background and INVALID Message"
        if not self._show:
            return
        self.window.addstr( self.row, self.col, f"[{self.text()}] INVALID!", curses.color_pair(3))

    def ok(self):
        "draw the button with a green background and OK Message"
        if not self._show:
            return
        self.window.addstr( self.row, self.col, f"[{self.text()}] OK!", curses.color_pair(1))


class Text:

    def __init__(self, window, text, row, col, txtlen=None):
        self.window = window
        self.row = row
        self.col = col
        self._focus = False
        self._show = True
        if txtlen:
            # txtlen includes the two [ ] brackets
            if len(text) > txtlen-2:
                self._text = shorten(text, width=txtlen-2, placeholder="...")
            elif len(text) == txtlen-2:
                self._text = text
            else:
                self._text = text.ljust(txtlen-2)
            self.txtlen = txtlen
        else:
            # no txtlen given
            self._text = text
            self.txtlen = len(self._text) + 2
        originrow, origincol = self.window.getbegyx()
        self.fieldrow = originrow+self.row
        self.startcol = origincol + self.col
        self.endcol = self.startcol + self.txtlen

    @property
    def text(self):
        return self._text.strip()

    @text.setter
    def text(self, text):
        if len(text) > self.txtlen-2:
            self._text = shorten(text, width=self.txtlen-2, placeholder="...")
        elif len(text) == self.txtlen-2:
            self._text = text
        else:
            self._text = text.ljust(self.txtlen-2)


    def __contains__(self, mouse):
        "Returns True if the mouse y, x are within this field"
        if not self._show:
            return False
        if mouse[0] != self.fieldrow:
            return False
        if mouse[1] < self.startcol:
            return False
        if mouse[1] < self.endcol:
            return True
        return False

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
            self.window.addstr( self.row, self.col, " "*self.txtlen)
            return
        if self._focus:
            self.window.addstr( self.row, self.col, "[", curses.A_BOLD)
            self.window.addstr( self.row, self.col+1, self._text)
            self.window.addstr( self.row, self.col+self.txtlen-1, "]", curses.A_BOLD)
        else:
            self.window.addstr( self.row, self.col, "["+self._text)
            self.window.addstr( self.row, self.col+self.txtlen-1, "]")

    def editstring(self, stdscr):
        "Returns an object to edit the string"
        editor = EditString(stdscr,
                            self.fieldrow,                  # row
                            self.startcol+1,                # start col
                            self.endcol-2,                  # endcol
                            self.text )                     # the actual text
        return editor



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




class BaseMember:

    def __init__(self, stdscr, consoleclient, window, tstatewin, vector, name, namelen=0):

        self.stdscr = stdscr
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.window = window
        self.tstatewin = tstatewin
        self.vector = vector
        self.name = name
        self.maxrows, self.maxcols = self.window.getmaxyx()
        # namelen sets a button on the left with length
        # if namelen not given, or too long, sets max len of self.maxcols//2-10
        # that is, for a widow of 80, this gives button text of 30, button size = 32 (for two brackets)
        if (not namelen) or (namelen>self.maxcols//2-10):
            namelen = self.maxcols//2-10
        membersdict = self.vector.members()
        self.member = membersdict[name]
        # self.member is a propertymember
        self.startline = 0
        # linecount is the number of lines this widget takes up,
        # including an end empty line
        self.linecount = 4
        self.name_btn = Button(window, self.name, 0, 1, namelen+2)
        self._focus = False
        # if close string is set, it becomes the return value from input routines
        self._close = ""

    def close(self, value):
        self._close = value


    def windowrefresh(self):
        self.window.draw()
        self.window.noutrefresh()


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

    def draw(self, startline=None):
        if not startline is None:
            self.startline = startline
        displaylabel = shorten(self.vector.memberlabel(self.name), width=self.maxcols-5, placeholder="...")
        self.window.addstr( self.startline, 1, displaylabel, curses.A_BOLD )
        self.name_btn.row = self.startline+1
        self.name_btn.draw()


    def setkey(self, key):
        return key

    async def keyinput(self):
        """Waits for a key press,
           if self.consoleclient.stop is True, returns 'Stop',
           if screen has been resized, returns 'Resize',
           if self._close has been given a value, returns that value
           Otherwise returns the key pressed."""
        while True:
            await asyncio.sleep(0)
            if self.consoleclient.stop:
                return "Stop"
            if self._close:
                return self._close
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key == curses.KEY_RESIZE:
                return "Resize"
            if key == curses.KEY_MOUSE:
                mouse = curses.getmouse()
                # mouse is (id, x, y, z, bstate)
                if mouse[4] == curses.BUTTON1_RELEASED:
                    # return a tuple of the mouse coordinates
                    #          row     col
                    return (mouse[2], mouse[1])
                continue
            return key




class SwitchMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, tstatewin, vector, name, namelen=0):
        super().__init__(stdscr, consoleclient, window, tstatewin, vector, name, namelen)
        # create  ON, OFF buttons
        self.on = Button(window, 'ON', 0, 0)
        self.on.bold = True if self.value() == "On" else False
        self.on.show = False
        self.off = Button(window, 'OFF', 0, 0)
        self.off.bold = not self.on.bold
        self.off.show = False
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

    def setkey(self, key):
        "This widget is in focus, and deals with inputs"

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
                self.window.noutrefresh()
                curses.doupdate()
            # ignore any other key
            return
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
                return
            self.window.noutrefresh()
            curses.doupdate()
            return
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
                return key
            elif key in (32, 261):   # 32 space, 261 right arrow
                # go to name_btn
                self.off.focus = False
                self.off.draw()
                self.name_btn.focus = True
                self.name_btn.draw()
            elif key in (9, 338, 339, 258, 259):   # 9 tab, 338 page down, 258 down arrow
                # go to next widget or scroll pad
                self.off.focus = False
                self.off.draw()
                return key
            elif key in (353, 260):  # 353 shift tab, 260 left arrow
                # back to on btn
                self.off.focus = False
                self.off.draw()
                self.on.focus = True
                self.on.draw()
            else:
                return
            self.window.noutrefresh()
            curses.doupdate()



class LightMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, tstatewin, vector, name, namelen=0):
        super().__init__(stdscr, consoleclient, window, tstatewin, vector, name, namelen)
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
        # draw the value
        self.window.addstr(self.startline+1, self.maxcols-20, text, self.consoleclient.color(lowervalue))

    def setkey(self, key):
        "This widget is in focus, but is read only"
        return key


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

    def __init__(self, stdscr, consoleclient, window, tstatewin, vector, name, namelen=0):
        super().__init__(stdscr, consoleclient, window, tstatewin, vector, name, namelen)
        self.linecount = 3
        if self.vector.perm == "ro":
            self.linecount = 3
        else:
            self.linecount = 4
        # the newvalue to be edited and sent
        self._newvalue = self.vector.getformattedvalue(self.name)

                                    # window         text        row col, length of field
        self.nmbr_txt = Text(self.window, self._newvalue, self.startline+2, self.maxcols-21, txtlen=16)


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
        # draw the value to be edited
        self.nmbr_txt.text = self.newvalue() #.ljust(16)
        self.nmbr_txt.draw()
        ## self.window.noutrefresh() probably not needed ##############



    def draw(self, startline=None):
        super().draw(startline)
        # draw the number value
        text = self.member.getformattedvalue().strip()
        if len(text) > 16:
            text = text[:16]
        # draw the value
        self.window.addstr(self.startline+1, self.maxcols-20, text, curses.A_BOLD)
        if self.vector.perm == "ro":
            return
        # the length of the editable number field is 16
        textnewvalue = self.newvalue().ljust(16)
        # draw the value to be edited
        self.nmbr_txt.draw()

    def setkey(self, key):
        "This widget is in focus, and deals with inputs"
        if self.name_btn.focus:
            if key in (9, 353, 260, 339, 338, 259, 258):  # 9 tab, 353 shift tab, 260 left arrow, 339 page up, 338 page down, 259 up arrow, 258 down arrow
                # go to next or previous member widget
                return key
            if key in (32, 261, 10):     # 32 space, 9 tab, 261 right arrow, 10 return
                self.name_btn.focus = False
                self.name_btn.draw()
                # input a number here
                self.nmbr_txt.focus = True
                self.nmbr_txt.draw()
                self.window.noutrefresh()
                curses.doupdate()
                return "edit"


    async def inputfield(self):
        "Input text, set it into self._newvalue"
        # set cursor visible
        curses.curs_set(1)
        editstring = self.nmbr_txt.editstring(self.stdscr)

        while not self.consoleclient.stop:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                curses.curs_set(0)
                return key
            if isinstance(key, tuple):
                if key in self.nmbr_txt:
                    continue
                else:
                    curses.curs_set(0)
                    return key
            if key == 10:
                curses.curs_set(0)
                self.name_btn.focus = True
                self.name_btn.draw()
                self.nmbr_txt.focus = False
                self.nmbr_txt.draw()
                self.window.noutrefresh()
                curses.doupdate()
                return 9 # tab for next item
            # key is to be inserted into the editable field, and self._newpath updated
            value = editstring.getnumber(key)
            self._newvalue = value.strip()
            # set new value back into self.nmbr_txt
            self.nmbr_txt.text = value
            self.nmbr_txt.draw()
            self.window.noutrefresh()
            editstring.movecurs()
            curses.doupdate()
        curses.curs_set(0)

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
            self.windowrefresh()
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
            self.windowrefresh()
            curses.doupdate()
            return True
        if self.member.max != self.member.min:
            maxvalue = self.member.getfloat(self.member.max)
            if newfloat > maxvalue:
                # reset self._newvalue to be the maximum, and accept this
                self._newvalue = self.member.getformattedstring(maxvalue)
                # draw the value to be edited
                self.window.addstr( self.startline+2, self.maxcols-20, self.newvalue().ljust(16) )
                self.windowrefresh()
                curses.doupdate()
                return True
        # reset self._newvalue to the correct format, and accept this
        self._newvalue = self.member.getformattedstring(newfloat)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-20, self.newvalue().ljust(16) )
        self.window.noutrefresh()
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

    def __init__(self, stdscr, consoleclient, window, tstatewin, vector, name, namelen=0):
        super().__init__(stdscr, consoleclient, window, tstatewin, vector, name, namelen)
        self.linecount = 4
        if self.vector.perm == "ro":
            self.linecount = 3
        # the newvalue to be edited and sent
        self._newvalue = self.vector[self.name]

        self.textfocus = False

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
        if self.vector.perm != "wo":
            text = self.member.membervalue.strip()
            if len(text) > 30:
                text = text[:30]
            # draw the value
            self.window.addstr(self.startline+1, self.maxcols-34, text, curses.A_BOLD)

        if self.vector.perm == "ro":
            return

        # the length of the editable text field is 30
        textnewvalue = self.newvalue().ljust(30)
        # draw the value to be edited
        self.window.addstr( self.startline+2, self.maxcols-35, "[" + textnewvalue+ "]" )


    def setkey(self, key):
        "This widget is in focus, and deals with inputs"

        if self.textfocus:
            # highlight editable field has focus
            # highlight editable field has focus
            self.name_btn.focus = False
            self.name_btn.draw()
            # set brackets of editable field in bold
            self.window.addstr( self.startline+2, self.maxcols-35, "[", curses.A_BOLD )
            self.window.addstr( self.startline+2, self.maxcols-4, "]", curses.A_BOLD )
            self.window.noutrefresh()
            curses.doupdate()
            # set cursor visible
            curses.curs_set(1)
            # pad starts at self.stdscr row 7, col 1
                                                      # row             startcol          endcol            start text
            editstring = EditString(self.stdscr, 7+self.startline+2, 1+self.maxcols-34, 1+self.maxcols-5, self.newvalue())


            result = self.textinput(key, editstring)
            return result

        if self.name_btn.focus:
            if key in (353, 260, 339, 338, 259, 258):  # 353 shift tab, 260 left arrow, 339 page up, 338 page down, 259 up arrow, 258 down arrow
                # go to next or previous member widget
                return key
            if key in (32, 9, 261, 10):     # 32 space, 9 tab, 261 right arrow, 10 return
                # text input here
                self.textfocus = True



    def textinput(self, key, editstring):
        """Input text, set it into self._newvalue"
           if all ok, return 9 to move to next field"""

        if key == 10:
            curses.curs_set(0)
            self.numberfocus = False
            return 9
        # key is to be inserted into the editable field, and self._newvalue updated
        value = editstring.gettext(key)
        self._newvalue = value.strip()
        self.window.addstr( self.startline+2, self.maxcols-34, value )
        self.window.noutrefresh()
        editstring.movecurs()
        curses.doupdate()


# Define a property that holds one or more Binary Large Objects, BLOBs.
# <!ELEMENT defBLOBVector (defBLOB+) >
# <!ATTLIST defBLOBVector
# device %nameValue; #REQUIRED       name of Device
# name %nameValue; #REQUIRED         name of Property
# label %labelValue; #IMPLIED        GUI label, use name by default
# group %groupTag; #IMPLIED          Property group membership, blank by default
# state %propertyState; #REQUIRED    current state of Property
# perm %propertyPerm; #REQUIRED      ostensible Client controlability
# timeout %numberValue; #IMPLIED     worse-case time to affect, 0 default, N/A for ro
# timestamp %timeValue #IMPLIED      moment when these data were valid
# message %textValue #IMPLIED        commentary

# Define one member of a BLOB vector. Unlike other defXXX elements, this does not contain an
# initial value for the BLOB.
# <!ELEMENT defBLOB EMPTY >
# <!ATTLIST defBLOB
# name %nameValue; #REQUIRED          name of this BLOB element
# label %labelValue; #IMPLIED         GUI label, or use name by default



class BLOBMember(BaseMember):

    def __init__(self, stdscr, consoleclient, window, tstatewin, vector, name, namelen=0):
        super().__init__(stdscr, consoleclient, window, tstatewin, vector, name, namelen)
        self.linecount = 4
        if self.vector.perm == "ro":
            self.linecount = 3
        # the filename to be edited and sent
        self._newvalue = ""
        # length of editable field, start with nominal 40
        self.fieldlength = 40
        if self.vector.perm != "ro":
            # set a button on the right
            self.send_btn = Button(window, "Send", 0, self.maxcols-9, 6)
        self.fileinput = False


    def filename(self):
        "Returns filename of last file received and saved"
        nametuple = (self.vector.devicename, self.vector.name, self.name)
        if nametuple in self.consoleclient.BLOBfiles:
            return self.consoleclient.BLOBfiles[nametuple].name
        else:
            return ""

    def newvalue(self):
        if not self._newvalue:
            return ""
        value = self._newvalue.strip()
        textlength = self.fieldlength - 2  # for the [] brackets
        if len(value) > textlength:
            value = value[:textlength]
        return value

    def reset(self):
        "Reset the widget removing any value updates, called by cancel"
        if self.vector.perm == "ro":
            return
        self._newvalue = ""
        textlength = self.fieldlength - 2  # for the [] brackets
        if not self._newvalue:
            textnewvalue = " "*textlength
        else:
            textnewvalue = self.newvalue().ljust(textlength)
        # draw the value to be edited
        self.window.addstr( self.startline+2, 20, "[" + textnewvalue+ "]" )

    def draw(self, startline=None):
        super().draw(startline)

        # draw the received file
        if self.vector.perm != "wo":
            # Set the length of the received filename to fit on the screen
            rxfilenamelength = self.maxcols//2 - 2
            rxfile = self.filename()
            if not rxfile:
                rxfile = " "*rxfilenamelength
            else:
                rxfile = shorten(rxfile, width=rxfilenamelength, placeholder="...")
            # draw the value
            self.window.addstr(self.startline+1, self.maxcols//2, rxfile, curses.A_BOLD)

        if self.vector.perm == "ro":
            return

        # Draw the editable field
        self.window.addstr( self.startline+2, 1, "Filepath to send:" )  # 18 characters from start from start

        # draw field 20 from start to 10 from end
        self.fieldlength = self.maxcols-30

        textnewvalue = self.newvalue().ljust(self.fieldlength-2)
        # draw the field and value to be edited
        self.window.addstr( self.startline+2, 20, "[" + textnewvalue+ "]" )

        # send button
        self.send_btn.row = self.startline+2
        self.send_btn.draw()



    def setkey(self, key):
        "This widget is in focus, and deals with inputs"

        if self.fileinput:
            # text input here
            # highlight editable field has focus
            self.name_btn.focus = False
            self.name_btn.draw()
            self.send_btn.focus = False
            self.send_btn.draw()
            # set brackets of editable field in bold
            self.window.addstr( self.startline+2, 20, "[", curses.A_BOLD )
            self.window.addstr( self.startline+2, 19 + self.fieldlength, "]", curses.A_BOLD )
            self.windowrefresh()
            curses.doupdate()
            # set cursor visible
            curses.curs_set(1)
            # pad starts at self.stdscr row 7, col 1
                                                      # row       startcol          endcol            start text
            editstring = EditString(self.stdscr, 7+self.startline+2, 22, 19 + self.fieldlength, self.newvalue())


            result = self.textinput(key, editstring)
            # after text input, set send button focus
            self.send_btn.focus = True
            self.send_btn.draw()
            self.windowrefresh()
            curses.doupdate()



        if self.name_btn.focus:
            if key in (353, 260, 339, 338, 259, 258):  # 353 shift tab, 260 left arrow, 339 page up, 338 page down, 259 up arrow, 258 down arrow
                # go to next or previous member widget
                return key
            if key in (32, 9, 261, 10):     # 32 space, 9 tab, 261 right arrow, 10 return
                self.fileinput = True
                return
        if self.send_btn.focus:
            if key == 10:
                # submit
                self.send_btn.focus = False
                self.send_btn.draw()
                self.name_btn.focus = True
                self.name_btn.draw()
                self.window.noutrefresh()
                curses.doupdate()
                try:
                    filepath = pathlib.Path(self._newvalue).expanduser().resolve()
                    blobformat = ''.join(filepath.suffixes)
                    members = {self.name : (filepath, 0, blobformat)}
                    self.vector.send_newBLOBVector(members=members)
                except Exception:
                    self.window.addstr( self.startline+2, 1, "!! Invalid !!    ", curses.color_pair(3) )
                    self.windowrefresh()
                    curses.doupdate()
                else:
                    self.window.addstr( self.startline+2, 1, " - Sending -     ", curses.color_pair(1) )
                    self.vector.state = 'Busy'
                    draw_timestamp_state(self.consoleclient, self.tstatewin, self.vector)
                    self.tstatewin.noutrefresh()
                    self.windowrefresh()
                    curses.doupdate()
                time.sleep(0.4)      # blocking, to avoid screen being changed while this time elapses
                self.window.addstr( self.startline+2, 1, "Filepath to send:" )
                self.windowrefresh()
                curses.doupdate()
                return
            elif key in (353, 260, 339, 259):  # 353 shift tab, 260 left arrow, 339 page up, 259 up arrow
                # back to name button
                self.send_btn.focus = False
                self.send_btn.draw()
                self.name_btn.focus = True
                self.name_btn.draw()
                self.windowrefresh()
                curses.doupdate()
                return
            else:
                # on to next widget
                self.send_btn.focus = False
                self.send_btn.draw()
                return 9


    def textinput(self, key, editstring):
        "Input text, set it into self._newvalue"
        if key == 10:
            curses.curs_set(0)
            self.fileinput = False
            return
        # key is to be inserted into the editable field, and self._newvalue updated
        value = editstring.gettext(key)
        self._newvalue = value.strip()
        self.window.addstr( self.startline+2, 21, value )
        self.window.noutrefresh()
        editstring.movecurs()
        curses.doupdate()
