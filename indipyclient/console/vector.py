
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

        # draw the bottom buttons
        self.vectors_btn.draw()
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.tstatewin.noutrefresh()
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
                self.vectors_btn.focus = True
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
                self.quit_btn.focus = True
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
                    else:
                        continue



        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"





class MembersWin:

    "Used to display the vector members"

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.window = curses.newpad(50, self.maxcols)
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.padtop = 0        # vector index number of top vector being displayed
        self.groupname = None
        self.devicename = None
        self.device = None

        # this is True, if this widget is in focus
        self._focus = False

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols-1, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.topmore_btn.show = False
        self.topmore_btn.focus = False

        # botmorewin (1 line, full row, starting at self.maxrows - 3, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols-1, self.maxrows - 3, 0)
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.botmore_btn.show = False
        self.botmore_btn.focus = False

        self.displaylines = self.maxrows - 5 - 8

        # list of vectors associated with this group
        self.vectors = []

        # list of vector buttons
        self.vector_btns = []

        # start with vectorname None, a vector to view will be chosen by this screen
        self.vectorname = None


    @property
    def padbot(self):
        "vector index number of bottom vector being displayed"
        return self.padtop + self.displaylines//2


    @property
    def lastvectorindex(self):
        "index number of last vector"
        return len(self.vectors) - 1


    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        if not value:
            self.leave_focus()
            return
        #return
        self._focus = True
        self.botmore_btn.draw()
        self.topmore_btn.draw()
        self.botmorewin.noutrefresh()
        self.topmorewin.noutrefresh()
        curses.doupdate()


    def leave_focus(self):
        "Equivalent to setting focus False"
        self._focus = False
        self.topmore_btn.focus = False
        self.botmore_btn.focus = False
        for btn in self.vector_btns:
            if btn.focus:
                btn.focus = False
                btn.draw()
        self.botmore_btn.draw()
        self.topmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def set_top_focus(self):
        if self._focus and self.topmore_btn.focus:
            # no change
            return
        self._focus = True
        if self.padtop:
            # give top button focus
            self.topmore_btn.show = True
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
            # ensure vectors do not have focus
            for btn in self.vector_btns:
                if btn.focus:
                    btn.focus = False
                    btn.draw()
        else:
            # give first vector focus
            first = True
            for btn in self.vector_btns:
                if first:
                    btn.focus = True
                    btn.draw()
                    first = False
                elif btn.focus:
                    btn.focus = False
                    btn.draw()

        self.botmore_btn.focus = False
        self.botmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def set_bot_focus(self):
        if self._focus and self.botmore_btn.focus:
            # no change
            return
        self._focus = True
        self.topmore_btn.focus = False
        self.topmore_btn.draw()
        if self.botmore_btn.show:
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
            for btn in self.vector_btns:
                if btn.focus:
                    btn.focus = False
                    btn.draw()
        else:
            # set the last vector in focus
            for index, btn in enumerate(self.vector_btns):
                if index == self.lastvectorindex:
                    btn.focus = True
                    btn.draw()
                elif btn.focus:
                    btn.focus = False
                    btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def draw(self, devicename, groupname):
        if (groupname == self.groupname) and (devicename == self.devicename):
            # no change
            return
        self.padtop = 0
        self.devicename = devicename
        self.device = self.client[devicename]
        self.groupname = groupname
        self.window.clear()
        self.topmorewin.clear()
        self.botmorewin.clear()

        self.topmore_btn.show = bool(self.padtop)
        self.topmore_btn.draw()

        try:

            # draw the vectors in the client with this device and group

            vectorlist = [vector for vector in self.device.values() if vector.group == self.groupname]

            self.vectors = sorted(vectorlist, key=lambda x: x.name)

            # so draw the vector widget, name, label, state, with names as buttons

            self.vector_btns = []

            line = 0

            for v in self.vectors:
                # shorten the name and set it as a button
                nm = v.name[:17] + "..." if len(v.name) > 20 else v.name
                self.vector_btns.append( widgets.Button(self.window, nm, line, 1) )  # the name as a button
                self.vector_btns[-1].draw()

                lb = v.label[:27] + "..." if len(v.label) > 30 else v.label
                self.window.addstr(line, 30, lb)  # the shortenned label
                lowerstate = v.state.lower()
                if lowerstate == "idle":
                    self.window.addstr(line, self.maxcols - 20, "  Idle  ", self.consoleclient.color(v.state))
                elif lowerstate == "ok":
                    self.window.addstr(line, self.maxcols - 20, "  OK    ", self.consoleclient.color(v.state))
                elif lowerstate == "busy":
                    self.window.addstr(line, self.maxcols - 20, "  Busy  ", self.consoleclient.color(v.state))
                elif lowerstate == "alert":
                    self.window.addstr(line, self.maxcols - 20, "  Alert ", self.consoleclient.color(v.state))
                line += 2


            if self.padbot >= self.lastvectorindex:
                self.botmore_btn.show = False
            else:
                self.botmore_btn.show = True
            self.botmore_btn.draw()

        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise


    def noutrefresh(self):

        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.padtop*2, 0, 8, 1, self.displaylines + 8, self.maxcols-2)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.topmorewin.noutrefresh()
        self.window.overwrite(self.stdscr, *coords)
        self.window.noutrefresh(*coords)
        self.botmorewin.noutrefresh()


    def upline(self):
        if not self.padtop:
            # already at top
            return
        self.padtop -= 1
        if not self.padtop:
            # at the top vectors
            self.topmore_btn.show = False
            self.topmore_btn.draw()
            btn = self.vector_btns[0]
            btn.focus = True
            btn.draw()
        if (not self.botmore_btn.show) and (self.padbot < self.lastvectorindex):
            self.botmore_btn.show = True
            self.botmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def downline(self):
        if self.padbot >= self.lastvectorindex:
            # already at the bottom
            return
        self.padtop += 1
        if not self.topmore_btn.show:
            self.topmore_btn.show = True
            self.topmore_btn.draw()
        if self.padbot >= self.lastvectorindex:
            self.botmore_btn.show = False
            self.botmore_btn.draw()
            btn = self.vector_btns[-1]
            btn.focus = True
            btn.draw()
        self.noutrefresh()
        curses.doupdate()



    async def input(self):
        "Get key pressed while this object has focus"
        self.stdscr.nodelay(True)
        while not self.consoleclient.stop:
            await asyncio.sleep(0)
            key = self.stdscr.getch()
            if key == -1:
                continue
            if key == 10:
                if self.topmore_btn.focus:
                    self.upline()
                elif self.botmore_btn.focus:
                    self.downline()
                else:
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    else:
                        # no vector in focus
                        continue
                    self.vectorname = self.vectors[btnindex].name
                    return 10
            if chr(key) in ("q", "Q", "m", "M", "d", "D"):
                return key
            elif key in (32, 9, 261, 338, 258):
                # go to the next
                if self.botmore_btn.focus:
                    self.focus = False
                    return key
                elif self.topmore_btn.focus:
                    # set focus on top vector
                    self.topmore_btn.focus = False
                    btn = self.vector_btns[self.padtop]
                    btn.focus = True
                    self.topmore_btn.draw()
                    btn.draw()
                    self.noutrefresh()
                    curses.doupdate()
                elif key in (338, 258):   # 338 page down, 258 down arrow
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    if btnindex >= self.padbot:
                        if not self.botmore_btn.show:
                            # At the last vector
                            self.focus = False
                            return key
                        else:
                            self.vector_btns[btnindex].focus = False
                            self.vector_btns[btnindex+1].focus = True
                            self.vector_btns[btnindex].draw()
                            self.vector_btns[btnindex+1].draw()
                            self.downline()
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex+1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex+1].draw()
                        self.noutrefresh()
                        curses.doupdate()
                else:
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    if btnindex >= self.padbot:
                        if self.botmore_btn.show:
                            self.set_bot_focus()
                        else:
                            # At the last vector
                            self.focus = False
                            return key
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex+1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex+1].draw()
                        self.noutrefresh()
                        curses.doupdate()


            elif key in (353, 260, 339, 259):
                # go to the previous
                if self.topmore_btn.focus:
                    self.focus = False
                    return key
                elif self.botmore_btn.focus:
                    # set focus on bottom vector
                    self.botmore_btn.focus = False
                    btn = self.vector_btns[self.padbot]
                    btn.focus = True
                    self.botmore_btn.draw()
                    btn.draw()
                    self.noutrefresh()
                    curses.doupdate()
                elif key in (339, 259):   # 339 page up, 259 up arrow
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    if not btnindex:
                        # At the top vector
                        self.focus = False
                        return key
                    if btnindex == self.padtop:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex-1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex-1].draw()
                        self.upline()
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex-1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex-1].draw()
                        self.noutrefresh()
                        curses.doupdate()
                else:
                    # find vector button in focus
                    btnindex = 0
                    for index, btn in enumerate(self.vector_btns):
                        if btn.focus:
                            btnindex = index
                            break
                    if not btnindex:
                        # At the top vector
                        self.focus = False
                        return key
                    if btnindex == self.padtop:
                        self.set_top_focus()
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex-1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex-1].draw()
                        self.noutrefresh()
                        curses.doupdate()

        return -1
