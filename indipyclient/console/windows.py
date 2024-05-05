
import asyncio, curses, sys, os, pathlib, time

from . import widgets

from .. import events



class ParentScreen:

    def __init__(self, stdscr, control):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.control = control
        self.client = control.client
        self.fields = []  # list of fields in the screen
        # if close string is set, it becomes the return value from input routines
        self._close = ""

    def close(self, value):
        self._close = value

    def defocus(self):
        for fld in self.fields:
            if fld.focus:
                fld.focus = False
                fld.draw()
                break

    def devicenumber(self):
        "Returns the number of enabled devices"
        return self.client.enabledlen()

    async def keyinput(self):
        """Waits for a key press,
           if self.control.stop is True, returns 'Stop',
           if screen has been resized, returns 'Resize',
           if self._close has been given a value, returns that value
           Otherwise returns the key pressed."""
        while True:
            await asyncio.sleep(0)
            if self.control.stop:
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


class ConsoleClientScreen(ParentScreen):

    "Parent to windows which are set in self.control.screen"

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)
        self.stdscr.clear()

    async def keyinput(self):
        """Waits for a key press,
           if self.control.screen is not self, returns 'Stop'
           if self.control.stop is True, returns 'Stop',
           if screen has been resized, returns 'Resize',
           if self._close has been given a value, returns that value
           Otherwise returns the key pressed."""
        while self.control.screen is self:
            await asyncio.sleep(0)
            if self.control.stop:
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
                    #         row        col
                    return (mouse[2], mouse[1])
                continue
            return key
        return "Stop"


class TooSmall(ConsoleClientScreen):

    def update(self, event):
        pass

    def show(self):
        self.stdscr.clear()
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.stdscr.addstr(2, self.maxcols//2-6, "Terminal too")
        self.stdscr.addstr(3, self.maxcols//2-2, "small")
        self.stdscr.addstr(4, self.maxcols//2-6, "Please resize")
        self.stdscr.noutrefresh()
        curses.doupdate()

    async def inputs(self):
        "Gets inputs from the screen"
        self.stdscr.nodelay(True)
        while True:
            key = await self.keyinput()
            if key in ("Resize", "Stop"):
                return key



class MessagesScreen(ConsoleClientScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)

        self.disconnectionflag = False

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Messages", curses.A_BOLD)

        # messages window (8 lines, full row - 4, starting at 4,3)
        self.messwin = self.stdscr.subwin(8, self.maxcols-4, 4, 3)

        # info window 6 lines, width 70
        self.infowin = self.stdscr.subwin(6, 70, self.maxrows-8, self.maxcols//2 - 35)
        self.infowin.addstr(0, 14, "All Timestamps are UTC")
        self.infowin.addstr(1, 0, "Once connected, choose 'Devices' and press Enter. Then use")
        self.infowin.addstr(2, 0, "mouse or Tab/Shift-Tab to move between fields, Enter to select,")
        self.infowin.addstr(3, 0, "and Arrow/Page keys to show further fields where necessary.")
        self.infowin.addstr(5, 5, "Enable/Disable Received BLOB's:")

        self.enable_btn = widgets.Button(self.infowin, "Enabled", 5, 38, onclick="EnableBLOBs")
        self.disable_btn = widgets.Button(self.infowin, "Disabled", 5, 48, onclick="DisableBLOBs")
        if self.control.blobenabled:
            self.enable_btn.bold = True
            self.disable_btn.bold = False
        else:
            self.enable_btn.bold = False
            self.disable_btn.bold = True

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10, onclick="Devices")
        self.devices_btn.focus = False
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2, onclick="Quit")
        self.quit_btn.focus = True

        self.fields = [self.enable_btn,
                       self.disable_btn,
                       self.devices_btn,
                       self.quit_btn]

    @property
    def connected(self):
        return self.control.connected

    def showunconnected(self):
        "Called by control on disconnection"
        if self.control.connected:
            self.disconnectionflag = False
            return
        if self.disconnectionflag:
            # already showing a disconnected status
            return
        # disconnectionflag is false, but the client is disconnected
        # so update buttons and titlewin, and set flag True, so the update
        # does not keep repeating
        self.disconnectionflag = True
        self.titlewin.addstr(2, 0, "Not Connected")
        self.titlewin.noutrefresh()
        if not self.quit_btn.focus:
            # defocus everything
            self.defocus()
            # and set quit into focus
            self.quit_btn.focus = True
            self.quit_btn.draw()
            self.infowin.noutrefresh()
            self.buttwin.noutrefresh()
        curses.doupdate()


    def show(self):
        "Displays title, info string and list of messages on a start screen"
        self.enable_btn.focus = False
        self.disable_btn.focus = False

        if self.control.blobenabled:
            self.enable_btn.bold = True
            self.disable_btn.bold = False
        else:
            self.enable_btn.bold = False
            self.disable_btn.bold = True

        if self.connected:
            self.disconnectionflag = False
            self.titlewin.addstr(2, 0, "Connected    ")
            self.devices_btn.focus = True
            self.quit_btn.focus = False
        else:
            self.disconnectionflag = True
            self.titlewin.addstr(2, 0, "Not Connected")
            self.devices_btn.focus = False
            self.quit_btn.focus = True

        # draw messages
        self.messwin.clear()
        messages = self.client.messages
        lastmessagenumber = len(messages) - 1
        mlist = reversed([ t.isoformat(sep='T')[11:21] + "  " + m for t,m in messages ])
        for count, message in enumerate(mlist):
            displaytext = widgets.shorten(message, width=self.maxcols-10, placeholder="...")
            if count == lastmessagenumber:
                # highlight the last, current message
                self.messwin.addstr(count, 0, displaytext, curses.A_BOLD)
            else:
                self.messwin.addstr(count, 0, displaytext)

        # draw buttons
        self.enable_btn.draw()
        self.disable_btn.draw()
        self.devices_btn.draw()
        self.quit_btn.draw()

        # refresh these sub-windows and update physical screen
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.infowin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()


    def update(self, event):
        "Only update if message has changed"
        if not isinstance(event, events.Message):
            return
        self.messwin.clear()
        messages = self.client.messages
        lastmessagenumber = len(messages) - 1
        mlist = reversed([ t.isoformat(sep='T')[11:21] + "  " + m for t,m in messages ])
        for count, message in enumerate(mlist):
            displaytext = widgets.shorten(message, width=self.maxcols-10, placeholder="...")
            if count == lastmessagenumber:
                # highlight the last, current message
                self.messwin.addstr(count, 0, displaytext, curses.A_BOLD)
            else:
                self.messwin.addstr(count, 0, displaytext)

        # check if connected or not
        if self.connected:
            self.titlewin.addstr(2, 0, "Connected    ")
        else:
            self.titlewin.addstr(2, 0, "Not Connected")

        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        curses.doupdate()


    def disableBLOBs(self):
        self.control.blobenabled = False
        self.client.report("Warning! BLOBs disabled")
        self.control.send_disableBLOB()
        self.enable_btn.bold = False
        self.disable_btn.bold = True
        self.enable_btn.draw()
        self.disable_btn.draw()
        self.infowin.noutrefresh()
        curses.doupdate()


    async def inputs(self):
        "Gets inputs from the screen"

        self.stdscr.nodelay(True)
        while True:
            key = await self.keyinput()

            if key == "Resize":
                return key

            if not self.connected:
                # only accept quit
                if not self.quit_btn.focus:
                    # defocus everything
                    self.defocus()
                    # and set quit into focus
                    self.quit_btn.focus = True
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                    self.infowin.noutrefresh()
                    curses.doupdate()
                elif key == 10:
                    return "Quit"
                elif isinstance(key, tuple) and (key in self.quit_btn):
                    return "Quit"
                continue

            if key in ("Devices", "Vectors", "Stop"):
                return key

            if isinstance(key, tuple):
                for fld in self.fields:
                    if key in fld:
                        if fld.focus:
                            # focus already set - return the button onclick
                            value = fld.onclick
                            if value == "DisableBLOBs":
                                self.disableBLOBs()
                                break
                            else:
                                return value
                        # focus not set, defocus the one currently
                        # in focus
                        self.defocus()
                        # and set this into focus
                        fld.focus = True
                        fld.draw()
                        self.buttwin.noutrefresh()
                        self.infowin.noutrefresh()
                        curses.doupdate()
                        break
                continue

            # 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

            if key in (32, 9, 261, 338, 258):
                # go to next button
                if self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.quit_btn.focus = True
                    self.devices_btn.draw()
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                elif self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                    self.enable_btn.focus = True
                    self.enable_btn.draw()
                    self.infowin.noutrefresh()
                elif self.enable_btn.focus:
                    self.enable_btn.focus = False
                    self.disable_btn.focus = True
                    self.enable_btn.draw()
                    self.disable_btn.draw()
                    self.infowin.noutrefresh()
                elif self.disable_btn.focus:
                    self.disable_btn.focus = False
                    self.disable_btn.draw()
                    self.infowin.noutrefresh()
                    self.devices_btn.focus = True
                    self.devices_btn.draw()
                    self.buttwin.noutrefresh()
                curses.doupdate()

            elif key in (353, 260, 339, 259):
                # go to the previous button
                if self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.devices_btn.focus = True
                    self.devices_btn.draw()
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                elif self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.devices_btn.draw()
                    self.buttwin.noutrefresh()
                    self.disable_btn.focus = True
                    self.disable_btn.draw()
                    self.infowin.noutrefresh()
                elif self.disable_btn.focus:
                    self.disable_btn.focus = False
                    self.disable_btn.draw()
                    self.enable_btn.focus = True
                    self.enable_btn.draw()
                    self.infowin.noutrefresh()
                elif self.enable_btn.focus:
                    self.enable_btn.focus = False
                    self.enable_btn.draw()
                    self.infowin.noutrefresh()
                    self.quit_btn.focus = True
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                curses.doupdate()

            elif key == 10:
                # Enter has been pressed, check which field has focus
                for fld in self.fields:
                    if fld.focus:
                        value = fld.onclick
                        if value == "DisableBLOBs":
                            self.disableBLOBs()
                            break
                        else:
                            return value


class EnableBLOBsScreen(ConsoleClientScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "BLOBs Folder", curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)

        # path window (10 lines, full row-4, starting at 4,4)
        self.pathwin = self.stdscr.subwin(11, self.maxcols-4, 4, 4)

        thiscol = self.maxcols//2 - 30

        self.pathwin.addstr(2, thiscol, "The INDI spec allows BLOB's to be received, by device or")
        self.pathwin.addstr(3, thiscol, "by device and property. This client is a simplification")
        self.pathwin.addstr(4, thiscol, "and enables or disables all received BLOB's.")
        self.pathwin.addstr(5, thiscol, "To enable BLOB's ensure the path below is set to a valid")
        self.pathwin.addstr(6, thiscol, "folder where BLOBs will be put, and press submit.")

        if self.control.blobfolder is None:
            self._newpath = ''
        else:
            self._newpath = str(self.control.blobfolder)

                                    # window         text        row col, length of field
        self.path_txt = widgets.Text(self.pathwin, self._newpath, 8, 0, txtlen=self.maxcols-8)

        self.submit_btn = widgets.Button(self.pathwin, "Submit", 10, self.maxcols//2 - 3, onclick="Submit")

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 15, onclick="Devices")
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 5, onclick="Messages")
        self.messages_btn.focus = True
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 6, onclick="Quit")

        self.fields = [self.path_txt,
                       self.submit_btn,
                       self.devices_btn,
                       self.messages_btn,
                       self.quit_btn]


    def show(self):
        "Displays the screen"

        # draw the message
        if self.client.messages:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)

        if self.control.blobenabled:
            self.pathwin.addstr(0, 0, "BLOBs are enabled  ", curses.A_BOLD)
        else:
            self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)

        # draw the input fields
        for fld in self.fields:
            fld.draw()

        # refresh these sub-windows and update physical screen
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.pathwin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()


    def update(self, event):
        "Only update if global message has changed"
        if isinstance(event, events.Message):
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)
            self.messwin.noutrefresh()
            curses.doupdate()


    def submit(self):
        self._newpath = self.path_txt.text.strip()
        blobfolder = None
        if self._newpath:
            try:
                blobfolder = pathlib.Path(self._newpath).expanduser().resolve()
            except Exception:
                self.control.blobenabled = False
                self.control.send_disableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
                self.client.report("Warning! Unable to parse BLOB folder")
                self.submit_btn.focus = False
                self.messages_btn.focus = True
                return
            if blobfolder.is_dir():
                self.control.blobfolder = blobfolder
                self._newpath = str(blobfolder)
                self.path_txt.text = self._newpath
                self.path_txt.draw()
                self.control.blobenabled = True
                self.control.send_enableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are enabled  ", curses.A_BOLD)
                self.client.report("BLOB folder is set")
            else:
                self.control.blobenabled = False
                self.control.send_disableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
                self.client.report("Warning! BLOB folder is not a directory")
        else:
            self.control.blobenabled = False
            self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
            self.client.report("Warning! BLOB folder is invalid")
            self.control.send_disableBLOB()
        self.submit_btn.focus = False
        self.messages_btn.focus = True


    async def inputs(self):
        "Gets inputs from the screen"

        self.stdscr.nodelay(True)
        while True:
            if self.path_txt.focus:
                # text input here
                key = await self.textinput()
            else:
                key = await self.keyinput()

            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key

            if isinstance(key, tuple):
                for fld in self.fields:
                    if key in fld:
                        if fld.focus:
                            # focus already set - return the button onclick
                            value = fld.onclick
                            if value == "Submit":
                                self.submit()
                                self.submit_btn.draw()
                                self.messages_btn.draw()
                                self.buttwin.noutrefresh()
                                self.pathwin.noutrefresh()
                                curses.doupdate()
                                break
                            else:
                                return value
                        # focus not set, defocus the one currently
                        # in focus
                        self.defocus()
                        # and set this into focus
                        fld.focus = True
                        fld.draw()
                        self.pathwin.noutrefresh()
                        self.buttwin.noutrefresh()
                        curses.doupdate()
                        break
                continue

            if key == 10:
                if self.quit_btn.focus:
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"
                elif self.messages_btn.focus:
                    return "Messages"
                elif self.devices_btn.focus:
                    return "Messages"
                elif self.submit_btn.focus:
                    self.submit()

            elif key in (32, 9, 261, 338, 258):
                # go to the next button
                if self.path_txt.focus:
                    self.path_txt.focus = False
                    self.submit_btn.focus = True
                    self.path_txt.draw()
                elif self.submit_btn.focus:
                    self.submit_btn.focus = False
                    self.devices_btn.focus = True
                elif self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.messages_btn.focus = True
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.quit_btn.focus = True
                elif self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.path_txt.focus = True
                    self.path_txt.draw()

            elif key in (353, 260, 339, 259):
                # go to previous button
                if self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.messages_btn.focus = True
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.devices_btn.focus = True
                elif self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.submit_btn.focus = True
                elif self.submit_btn.focus:
                    self.submit_btn.focus = False
                    self.path_txt.focus = True
                    self.path_txt.draw()
                elif self.path_txt.focus:
                    self.path_txt.focus = False
                    self.quit_btn.focus = True
                    self.path_txt.draw()
            else:
                # button not recognised
                continue

            # draw buttons
            self.submit_btn.draw()
            self.messages_btn.draw()
            self.devices_btn.draw()
            self.quit_btn.draw()
            self.buttwin.noutrefresh()
            self.pathwin.noutrefresh()
            curses.doupdate()



    async def textinput(self):
        "Input text, set it into self._newvalue"
        # set cursor visible
        curses.curs_set(1)
        editstring = self.path_txt.editstring(self.stdscr)

        while not self.control.stop:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                curses.curs_set(0)
                return key
            if isinstance(key, tuple):
                if key in self.path_txt:
                    continue
                else:
                    curses.curs_set(0)
                    return key
            if key == 10:
                curses.curs_set(0)
                return 9
            # key is to be inserted into the editable field, and self._newpath updated
            value = editstring.gettext(key)
            self._newpath = value.strip()
            # set new value back into self.path_txt
            self.path_txt.text = value
            self.path_txt.draw()
            self.pathwin.noutrefresh()
            editstring.movecurs()
            curses.doupdate()
        curses.curs_set(0)


class DevicesScreen(ConsoleClientScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)

        # assume screen 80 x 24                                      # row 0 to 23
        # self.maxrows = 24

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)    # row 0
        self.titlewin.addstr(0, 0, "Devices", curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)     # row 2

        # status window (1 line, full row-4, starting at 4,4)
        self.statwin = self.stdscr.subwin(1, self.maxcols-4, 4, 4)   # row 4

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, 6, 0) # row 6
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="TopMore")
        self.topmore_btn.show = False

        # devices window                                            # row 7 blank between more and top device

        # calculate top and bottom row numbers
        self.devwintop = 8                                                          # row 8
        # ensure bottom row is an odd number at position self.maxrows - 4 or -5
        row = self.maxrows - 4             # 19
        self.devwinbot = row - row % 2   # Subtracts 1 if row is even                     # row 19 (leaving rows 20-23)

        # for 24 row window
        # device window will have row 8 to row 19, displaying 6 devices, (self.devwinbot-self.devwintop+1) // 2  = 6

        # device window                          19 - 8 + 1 = 12 rows       80            row 8      left col
        self.devwin = self.stdscr.subwin(self.devwinbot-self.devwintop+1, self.maxcols, self.devwintop, 0)

        # topindex of device being shown
        self.topindex = 0                   # so six devices will show devices with indexes 0-5

        # botmorewin (1 line, full row, starting at self.maxrows - 4, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 4, 0)      # row 20
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="BotMore")
        self.botmore_btn.show = False
                                                                                    # rows 21, 22 blank
        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        # this holds the messages and quit buttons
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)     # row 23

        # self.focus will be the name of a device in focus
        self.focus = None

        # Start with the messages_btn in focus
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 10, onclick="Messages")
        self.messages_btn.focus = True

        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2, onclick="Quit")

        # devicename to devices
        self.devices = {}
        # devicename to buttons
        self.devbuttons = {}             # devicenames are original case


    def show(self):
        "Displays the screen with list of devices"

        # draw the message
        if self.client.messages:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)

        self.devices = {devicename:device for devicename,device in self.client.items() if device.enable}

        # draw status
        if not self.devices:
            self.statwin.addstr(0, 0, "No devices have been discovered")
        else:
            self.statwin.addstr(0, 0, "Choose a device:               ")

        # draw device buttons, and if necessary the 'more' buttons
        self.drawdevices()

        # draw messages and quit buttons
        self.drawbuttons()

        # refresh these sub-windows and update physical screen
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.statwin.noutrefresh()
        self.topmorewin.noutrefresh()
        self.devwin.noutrefresh()
        self.botmorewin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()

    def defocus(self):
        "Remove focus from all buttons, and re-draw the button which had focus"
        if self.focus:
            btn = self.devbuttons[self.focus]
            btn.focus = False
            btn.draw()
            self.focus = None
        elif self.topmore_btn.focus:
            self.topmore_btn.focus = False
            self.topmore_btn.draw()
        elif self.botmore_btn.focus:
            self.botmore_btn.focus = False
            self.botmore_btn.draw()
        elif self.messages_btn.focus:
            self.messages_btn.focus = False
            self.messages_btn.draw()
        elif self.quit_btn.focus:
            self.quit_btn.focus = False
            self.quit_btn.draw()

    def devwinrefresh(self):
        "Call noutrefresh on more buttons and device window"
        self.topmorewin.noutrefresh()
        self.devwin.noutrefresh()
        self.botmorewin.noutrefresh()


    def botindex(self):
        "Returns the index of the bottom device being displayed"
        # self.topindex is the top device being displayed
        bottomidx = self.topindex + (self.devwinbot-self.devwintop+1) // 2 - 1
        # example  0 + (19-8+1)//2 - 1  = 5
        # example  3 + (19-8+1)//2 - 1  = 8
        lastidx = len(self.devices)-1
        if bottomidx > lastidx:
            return lastidx
        return bottomidx


    def drawdevices(self):
        "Called by self.show/update to create and draw the device buttons"
        self.topmorewin.clear()
        self.devwin.clear()
        self.botmorewin.clear()

        if not self.devices:               # no devices
            self.focus = None
            self.topmore_btn.show = False
            self.botmore_btn.show = False
            return

        # Remove current device buttons
        self.devbuttons.clear()

        bottomidx = self.botindex()

        colnumber = self.maxcols//2 - 6

        linenumber = 0
        for idx, devicename in enumerate(self.devices):
            if idx < self.topindex:
                continue
            if idx > bottomidx:
                break
            self.devbuttons[devicename] = widgets.Button(self.devwin, devicename, linenumber, colnumber, onclick=devicename.lower())
            linenumber += 2  # two lines per button

        # self.devbuttons is a devicename to button dictionary, but only for buttons displayed

        # Note: initially all device buttons are created with focus False
        # self.focus has the name of the device which should be in focus
        # so if it is set, set the appropriate button focus

        if self.focus:
            if self.focus in self.devbuttons:
                self.devbuttons[self.focus].focus = True
            else:
                self.focus = None

        # if self.topindex is not zero, then draw top more button
        if self.topindex:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # draw devices buttons
        for devbutton in self.devbuttons.values():
            devbutton.draw()

        # bottomidx is the index of the bottom device being displayed
        if bottomidx < len(self.devices) -1:
            self.botmore_btn.show = True
        else:
            self.botmore_btn.show = False
        self.botmore_btn.draw()


    def drawbuttons(self):
        "Called by self.show/update to draw the messages and quit buttons"
        self.buttwin.clear()

        # If a device is in focus, these buttons are not
        if self.focus or self.topmore_btn.focus or self.botmore_btn.focus:
            self.messages_btn.focus = False
            self.quit_btn.focus = False
        elif (not self.quit_btn.focus) and (not self.messages_btn.focus):
            # at least one button must be in focus
            self.messages_btn.focus = True

        self.messages_btn.draw()
        self.quit_btn.draw()


    def update(self, event):
        "Only update if global message has changed, or a new device added or deleted"
        if isinstance(event, events.Message) and event.devicename is None:
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)
            self.messwin.noutrefresh()
            curses.doupdate()
            return
        # check devices unchanged
        if isinstance(event, events.delProperty) and event.vectorname is None:
            # a device has being deleted
            self.topindex = 0
            self.defocus()
            self.show()
            return
        if event.devicename is not None:
            if event.devicename not in self.devices:
                # unknown device, check this is a definition
                if isinstance(event, events.defVector) or isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.topindex = 0
                    self.defocus()
                    self.show()


    def topmorechosen(self):
        "Update when topmore button pressed"
        if not self.topmore_btn.focus:
            return
        if not self.topindex:    # self.topindex cannot be zero
            return

        # devices is a dictionary of devicenames to devices
        # names is a list of all device names
        names = list(self.devices.keys())

        self.topindex -= 1

        if not self.topindex:
            # at the top device
            self.topmore_btn.focus = False
            self.focus = names[0]

        # drawdevices will sort out top and bottom
        # more buttons
        self.drawdevices()
        self.devwinrefresh()


    def botmorechosen(self):
        "Update when botmore button pressed"
        if not self.botmore_btn.focus:
            return

        # the aim is to increment self.topindex
        # but doing so may display last bottom device
        # which makes botmore button dissapear

        # devices is a dictionary of devicenames to devices
        # names is a list of all device names
        names = list(self.devices.keys())

        new_top_idx = self.topindex + 1

        new_bot_idx = new_top_idx + (self.devwinbot-self.devwintop) // 2 - 1
        # lastidx is the index of the last device
        lastidx = len(names)-1

        if new_bot_idx > lastidx:
            # no point incrementing topindex as it does not display any new device
            self.botmore_btn.show = False
            self.focus = names[-1]        # set focus to name of last device
        else:
            # so increment topindex
            self.topindex = new_top_idx
            if new_bot_idx == lastidx:
                # cannot increment further
                self.botmore_btn.show = False
                self.focus = names[-1]

        self.drawdevices()
        self.devwinrefresh()


# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"

        self.stdscr.nodelay(True)
        names = list(self.devices.keys())
        lastidx = len(names)-1            # index of last device

        while True:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key
            displayedbtns = list(self.devbuttons.values())
            displayednames = list(self.devbuttons.keys())
            bottomidx = self.botindex()       # index of last displayed device

            if isinstance(key, tuple):
                # mouse pressed, find if its clicked in any field
                if key in self.quit_btn:
                    if self.quit_btn.focus:
                        widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                        self.messwin.noutrefresh()
                        curses.doupdate()
                        return "Quit"
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        self.quit_btn.focus = True
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                    else:
                        # either a top or bottom more button or a device has focus
                        self.defocus()
                        self.devwinrefresh()
                        self.quit_btn.focus = True
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                if key in self.messages_btn:
                    if self.messages_btn.focus:
                        return "Messages"
                    elif self.quit_btn.focus:
                        self.quit_btn.focus = False
                        self.messages_btn.focus = True
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                    else:
                        # either a top or bottom more button or a device has focus
                        self.defocus()
                        self.devwinrefresh()
                        self.messages_btn.focus = True
                        self.messages_btn.draw()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                if key in self.topmore_btn:
                    if self.topmore_btn.focus:
                        self.topmorechosen()
                    else:
                        self.defocus()
                        self.topmore_btn.focus = True
                        self.topmore_btn.draw()
                        self.devwinrefresh()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                if key in self.botmore_btn:
                    if self.botmore_btn.focus:
                        self.botmorechosen()
                    else:
                        self.defocus()
                        self.botmore_btn.focus = True
                        self.botmore_btn.draw()
                        self.devwinrefresh()
                        self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue

                # so now must check if mouse position is in any of the devices
                if key[0] > self.devwinbot:
                    # no chance of device button being pressed as mouse point
                    # is at a row greater than bottom line of the device window
                    continue

                # displayedbtns button list, but only for buttons displayed

                for idx, btn in enumerate(displayedbtns):
                    if key in btn:
                        if btn.focus:
                            return btn.onclick
                        else:
                            # button not in focus, so set it
                            self.defocus()
                            btn.focus = True
                            btn.draw()
                            self.focus = displayednames[idx]
                            self.devwinrefresh()
                            self.buttwin.noutrefresh()
                            curses.doupdate()
                            break
                continue

            # so not a tuple/mouse press, its a key press

            # which button has focus
            if key == 10:
                if self.quit_btn.focus:
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"
                if self.messages_btn.focus:
                    return "Messages"
                if self.topmore_btn.focus:
                    self.topmorechosen()
                    curses.doupdate()
                    continue
                if self.botmore_btn.focus:
                    self.botmorechosen()
                    curses.doupdate()
                    continue

                # If not Quit or Messages, return the lower case name
                # of the device in focus
                if self.focus:
                    return self.focus.lower()
                continue


            if key in (32, 9, 261, 338, 258):   # 32 space, 9 tab, 261 right arrow, 338 page down, 258 down arrow
                # go to the next button
                if self.quit_btn.focus:
                    self.quit_btn.focus = False
                    if self.topindex:
                        # that is, if top button does not have index zero
                        self.topmore_btn.focus = True
                    else:
                        self.focus = displayednames[0]
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.quit_btn.focus = True
                    self.drawbuttons()
                    self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                elif self.topmore_btn.focus:
                    self.topmore_btn.focus = False
                    self.focus = displayednames[0]
                    self.drawdevices()
                    self.devwinrefresh()
                    curses.doupdate()
                    continue
                elif self.botmore_btn.focus:
                    self.botmore_btn.focus = False
                    self.messages_btn.focus = True
                else:
                    # one of the devices has focus
                    try:
                        indx = names.index(self.focus)
                    except ValueError:
                        continue
                    # indx here is the index on the list of all devices, not just those displayed
                    if indx == lastidx:
                        # very last device, the botmore_btn should not be shown
                        self.focus = None
                        self.messages_btn.focus = True
                    elif indx == bottomidx:
                        # last displayed device
                        if key in (338, 258):      # 338 page down, 258 down arrow
                            # display next device
                            self.topindex += 1
                            self.focus = names[indx+1]
                        else:
                            # last device on display
                            self.focus = None
                            self.botmore_btn.focus = True
                    else:
                        self.focus = names[indx+1]

            elif key in (353, 260, 339, 259):  # 353 shift tab, 260 left arrow, 339 page up, 259 up arrow
                # go to previous button
                if self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.messages_btn.focus = True
                    self.drawbuttons()
                    self.buttwin.noutrefresh()
                    curses.doupdate()
                    continue
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    if self.botmore_btn.show:
                        self.botmore_btn.focus = True
                    else:
                        self.focus = displayednames[-1]
                elif self.botmore_btn.focus:
                    self.botmore_btn.focus = False
                    self.focus = displayednames[-1]
                elif self.topmore_btn.focus:
                    self.topmore_btn.focus = False
                    self.quit_btn.focus = True
                elif self.focus == names[0]:
                    self.focus = None
                    self.quit_btn.focus = True
                else:
                    try:
                        indx = names.index(self.focus)
                    except ValueError:
                        continue
                    if indx == self.topindex:
                        if key in (339, 259): # 339 page up, 259 up arrow
                            self.topindex -= 1
                            self.focus = names[indx-1]
                        else:
                            self.focus = None
                            self.topmore_btn.focus = True
                    else:
                        self.focus = names[indx-1]

            else:
                # button not recognised
                continue

            # draw devices and buttons
            self.drawdevices()
            self.drawbuttons()
            self.devwinrefresh()
            self.buttwin.noutrefresh()
            curses.doupdate()


class ChooseVectorScreen(ConsoleClientScreen):

    def __init__(self, stdscr, control, devicename, group=None):
        super().__init__(stdscr, control)

        # devicename is the actual devicename given by the device (not set to lower case)
        self.devicename = devicename

        # group, if given is the startup group displayed

        # start with vectorname None, a vector to view will be chosen by this screen
        self.vectorname = None

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)                  # row 0
        devicetitle = widgets.shorten("Device: " + self.devicename, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(0, 0, devicetitle, curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)                   # row 2
        self.lastmessage = ""

        # list areas of the screen, one of these areas has the current 'focus'
        # Groups being the horizontal line of group names associated with a device
        # Vectors being the area showing the vectors associated with a device and group
        # and Devices, Messages and Quit are the bottom buttons
        self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")

        # groups list
        self.groupwin = GroupWin(self.stdscr, self.control, self.devicename, active=group)         # row 4
        # this creates its own window (1 line, full row, starting at 4,0)

        # window showing the vectors of the active group
        self.vectorswin = VectorListWin(self.stdscr, self.control, self.devicename)    # topmore row 6


        # bottom buttons, [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)              # row 23
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.device = None
        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 15)
        self.devices_btn.focus = True
        self.focus = "Devices"

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 5)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 6)


    def show(self):
        "Displays device vectors choosable by group"

        devices = [ devicename for devicename, device in self.client.items() if device.enable ]

        if self.devicename not in devices:
            widgets.drawmessage(self.messwin, f"{self.devicename} not found!", maxcols=self.maxcols)
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.titlewin.noutrefresh()
            self.messwin.noutrefresh()
            self.buttwin.noutrefresh()

            curses.doupdate()
            return

        self.device = self.client[self.devicename]
        if self.device.messages:
            self.lastmessage = self.device.messages[0]
            widgets.drawmessage(self.messwin, self.lastmessage, maxcols=self.maxcols)

        # draw horizontal list of groups
        self.groupwin.draw(self.devicename)

        # Draw the device vector widgets, as given by self.groupwin.active
        self.vectorswin.draw(self.devicename, self.groupwin.active )

        # draw the bottom buttons
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.groupwin.noutrefresh()
        self.vectorswin.noutrefresh()
        self.buttwin.noutrefresh()

        curses.doupdate()


    def setfocus(self, newfocus):
        """Sets self.focus to newfocus
           If newfocus is one of Messages, Quit, Devices, sets the
           new focus on the button, draws and calls self.buttwin.noutrefresh()
           and removes focus from all other buttons.
           If self.focus is Groups or Vectors, and the newfocus is the same
           then returns unchanged, otherwise calls defocus on the window.
           So leaves it to the subwindow to set new focus
           """
        if self.focus == "Groups" or self.focus == "Vectors":
            # current self.focus is on the subwindows
            if self.focus == "Groups" and newfocus != "Groups":
                self.groupwin.defocus()
                self.groupwin.noutrefresh()
            elif self.focus == "Vectors" and newfocus != "Vectors":
                self.vectorswin.defocus()
                self.vectorswin.noutrefresh()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
                self.buttwin.noutrefresh()
            self.focus = newfocus
            return

        # current self.focus must be one of the bottom buttons
        if self.focus == "Devices" and newfocus != "Devices":
            self.devices_btn.focus = False
            self.devices_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            self.buttwin.noutrefresh()
        elif self.focus == "Messages" and newfocus != "Messages":
            self.messages_btn.focus = False
            self.messages_btn.draw()
            if newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            self.buttwin.noutrefresh()
        elif self.focus == "Quit" and newfocus != "Quit":
            self.quit_btn.focus = False
            self.quit_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            self.buttwin.noutrefresh()
        self.focus = newfocus


    def timeout(self, event):
        "A timeout event has occurred, update the vector state"
        if event.vector.state == "Busy":
            event.vector.state = "Alert"
            event.vector.timestamp = event.timestamp
            self.vectorswin.draw(self.devicename, self.groupwin.active )
            self.vectorswin.noutrefresh()
            curses.doupdate()


    def update(self, event):
        "Change anything that has been updated"
        if self.device.messages:
            if self.device.messages[0] != self.lastmessage:
                self.lastmessage = self.device.messages[0]
                widgets.drawmessage(self.messwin, self.lastmessage, maxcols=self.maxcols)
                self.messwin.noutrefresh()

        # draw the groups
        self.groupwin.draw(self.devicename)
        self.groupwin.noutrefresh()

        # Draw the device vector widgets, as given by self.groupwin.active
        self.vectorswin.draw(self.devicename, self.groupwin.active )
        self.vectorswin.noutrefresh()
        curses.doupdate()


    async def inputs(self):
        "Gets inputs from the screen"

        self.stdscr.nodelay(True)
        while True:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key

            if isinstance(key, tuple):
                # mouse pressed, find if its clicked in any field
                # check all areas of the screen
                if key in self.quit_btn:
                    if self.quit_btn.focus:
                        widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                        self.messwin.noutrefresh()
                        curses.doupdate()
                        return "Quit"
                    else:
                        # focus is elsewhere
                        self.setfocus("Quit")
                    curses.doupdate()
                    continue
                if key in self.messages_btn:
                    if self.messages_btn.focus:
                        return "Messages"
                    else:
                        self.setfocus("Messages")
                    curses.doupdate()
                    continue
                if key in self.devices_btn:
                    if self.devices_btn.focus:
                        return "Devices"
                    else:
                        self.setfocus("Devices")
                    curses.doupdate()
                    continue

                # check if mouse key in groupwin
                result = self.groupwin.setkey(key)
                if result == "Newfocus":
                    # focus has been set onto a new group
                    # must remove focus from other parts of the screen
                    self.setfocus("Groups")
                    curses.doupdate()
                    continue
                if result == "NewGroup":
                    # must update the screen with a new group
                    self.show()
                    continue

                if not result:
                    continue
                # otherwise mouse not pressed in a group, so self.groupwin.setkey(key)
                # just returns the key
                key = result

                # check if mouse key pressed in vectorswin
                result = self.vectorswin.setkey(key)
                if result == "Newfocus":
                    # focus has been set onto a new vector
                    # must remove focus from other parts of the screen
                    self.setfocus("Vectors")
                    curses.doupdate()
                    continue
                if result == "NewVector":
                    newvector = self.vectorswin.active
                    if newvector in self.device:
                        # newvector is a vector name, check if it is enabled
                        if self.device[newvector].enable:
                            self.vectorname = newvector
                            return "Vectors"

                # mouse press not on a field
                continue

            # so not a tuple/mouse press, its a key press

            if self.focus == "Groups":
                # focus has been given to the GroupWin
                result = self.groupwin.setkey(key)
                if result == "NewGroup":
                    # must update the screen with a new group
                    # which is available as self.groupwin.active
                    self.show()
                    continue
                if not result:
                    continue
                key = result
                # key could be a down arrow for next item
                # but will not be 10 as Enter will be actioned within self.groupwin.setkey(key)

            elif self.focus == "Vectors":
                # focus has been given to VectorListWin
                result = self.vectorswin.setkey(key)
                if not result:
                    continue
                if result == "NewVector":
                    newvector = self.vectorswin.active
                    if newvector in self.device:
                        # newvector is a vector name, check if it is enabled
                        if self.device[newvector].enable:
                            self.vectorname = newvector
                            return "Vectors"
                        else:
                            continue
                    else:
                        continue
                key = result
                # key could be a down arrow for next item
                # but will not be 10 as Enter will be actioned within self.vectorswin.setkey(key)

            if key == 10:
                # enter key pressed
                if self.focus == "Quit":
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                # return the focus value of whichever item was in focus when enter was pressed
                return self.focus

            if key in (32, 9, 261, 338, 258):
                # go to the next widget
                if self.focus == "Quit":
                    if len(self.groupwin.groups()) == 1:
                        newfocus = "Vectors"
                    else:
                        newfocus = "Groups"
                else:
                    indx = self.screenparts.index(self.focus)
                    newfocus = self.screenparts[indx+1]
            elif key in (353, 260, 339, 259):
                # go to previous button
                if self.focus == "Groups":
                    newfocus = "Quit"
                elif self.focus == "Vectors":
                    if len(self.groupwin.groups()) == 1:
                        newfocus = "Quit"
                    else:
                        newfocus = "Groups"
                else:
                    indx = self.screenparts.index(self.focus)
                    newfocus = self.screenparts[indx-1]
            else:
                # key not recognised
                continue

            if self.focus == "Vectors":
                self.vectorswin.defocus()
            elif self.focus == "Groups":
                self.groupwin.defocus()
            elif self.focus == "Devices":
                self.devices_btn.focus = False
            elif self.focus == "Messages":
                self.messages_btn.focus = False
            elif self.focus == "Quit":
                self.quit_btn.focus = False
            if newfocus == "Vectors":
                if key in (32, 9, 261, 338, 258):
                    # next button
                    self.vectorswin.set_top_focus()
                else:
                    self.vectorswin.set_bot_focus()
            elif newfocus == "Groups":
                self.groupwin.set_left_focus()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
            elif newfocus == "Messages":
                self.messages_btn.focus = True
            elif newfocus == "Quit":
                self.quit_btn.focus = True
            self.focus = newfocus

            # so buttons have been set with the appropriate focus
            # now draw them
            self.groupwin.draw(self.devicename)
            self.vectorswin.draw(self.devicename, self.groupwin.active, change=True)
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.vectorswin.noutrefresh()
            self.groupwin.noutrefresh()
            self.buttwin.noutrefresh()
            curses.doupdate()



# This class GroupBtns defines the position of group buttons on the row
# and stores values used to check if any change has occurred

class GroupBtns:

    def __init__(self, device, maxcols, focus, rightfocus, leftfocus, leftidx, active):
        "get the groups this device contains, use a set to avoid duplicates"
        self.maxcols = maxcols

        # these are used to store previous values to check if there is any change
        self.focus = focus
        self.rightfocus = rightfocus  # True if rightmore has focus
        self.leftfocus = leftfocus    # True if leftmore has focus
        self.leftidx = leftidx        # index of leftmost button
        self.active = active          # the currently active group

        groupset = {vector.group for vector in device.values() if vector.enable}
        if not groupset:
            groupset = set("default")

        # self.groups is a list of group names
        self.groups = sorted(list(groupset))

        # self.positions is a list of tuples (col, btnlen)
        self.positions = []

        # If there is only one group, text is displayed rather than buttons
        if len(self.groups) == 1:
            self.text = widgets.shorten(f" Groups : {self.groups[0]}", width=self.maxcols-6, placeholder="...")
            self.scroll = False
            return
        elif len(self.groups) == 2:
            btnlen = self.maxwidth()
            self.text = "Groups : "
            self.positions = [(9, btnlen), (10+btnlen, btnlen)]
            self.scroll = False
            return

        btnlen = self.maxwidth()
        self.text = ""
        self.positions = [(9, btnlen)]
        for grp in self.groups:
            prevcol = self.positions[-1][0]
            nextcol = prevcol + btnlen + 1
            if nextcol >= self.maxcols - 9 - btnlen:
                break
            self.positions.append((nextcol, btnlen))

        if len(self.groups) <= len(self.positions):
            # if all the groups can fit on the row, there is no scrolling
            self.scroll = False
        else:
            self.scroll = True



    def __eq__(self, other):
        if self.active is None:
            return False
        if self.maxcols != other.maxcols:
            return False
        if self.groups != other.groups:
            return False
        if self.focus != other.focus:
            return False
        if self.rightfocus != other.rightfocus:
            return False
        if self.leftfocus != other.leftfocus:
            return False
        if self.leftidx != other.leftidx:
            return False
        if self.active != other.active:
            return False
        # if all the above are equal
        return True

    def maxwidth(self):
        "calculate width of buttons"
        # =<[prev]=[btn]=[btn]=....               =[next]>=
        #     9                                      8
        btnspace = self.maxcols - 9 - 8                           # 80-9-8 is 63
        # assume three buttons
        maxbtn = btnspace//3 - 1  # -1 for space between buttons     # 21-1 = 18
        maxtext = max(len(grp) for grp in self.groups)
        # choose whichever is smaller
        if maxbtn >= maxtext+2:
            width = maxtext + 2     # 2 for the [] brackets
        else:
            width = maxbtn
        return width



# The following two windows, GroupWin and VectorListWin are sub windows of ChooseVectorScreen

class GroupWin(ParentScreen):

    def __init__(self, stdscr, control, devicename, active=None):
        super().__init__(stdscr, control)

        # window (1 line, full row, starting at 4,0)
        self.window = self.stdscr.subwin(1, self.maxcols, 4, 0)   # this window on row 4

        self.devicename = devicename
        device = self.client[self.devicename]

        # grps is a class that calculates button positions along the row
        # Note, the final argument active is set to None to ensure the first call to draw()
        # detects active has changed, and initiates a window draw.
        self.grps = GroupBtns(device, self.maxcols, None, False, False, 0, None)
        groups = self.grps.groups

        # active is the name of the group currently being shown
        # it cannot be None
        if (active is None) or (not active in groups):
            self.active = groups[0]
        else:
            self.active = active

        # group names to buttons
        self.grpbuttons = {}             # group names are original case

        # this is set to the group name in focus, if any
        self.focus = None
        self.rightfocus = False  # True if rightmore has focus
        self.leftfocus = False   # True if leftmore has focus

        self.rightmore_btn = widgets.Button(self.window, "next", 0, self.maxcols-8, onclick="Next")
        self.rightmore_btn.show = False

        self.leftmore_btn = widgets.Button(self.window, "prev", 0, 2, onclick="Previous")
        self.leftmore_btn.show = False

        self.leftidx = 0          # group index of leftmost button
                                  # that is, groups[self.leftidx] is the group of the leftmost button



    def groups(self):
        "self.groups() returns a list of group names"
        return self.grps.groups

    def noutrefresh(self):
        "Call noutrefresh on group window"
        self.window.noutrefresh()

    def defocus(self):
        "Remove focus from all buttons, and draw"
        if not self.grpbuttons:
            return
        if self.focus:
            btn = self.grpbuttons[self.focus]
            btn.focus = False
            btn.draw()
            self.focus = None
        elif self.leftmore_btn.focus:
            self.leftmore_btn.focus = False
            self.leftmore_btn.draw()
            self.leftfocus = False
        elif self.rightmore_btn.focus:
            self.rightmore_btn.focus = False
            self.rightmore_btn.draw()
            self.rightfocus = False

    def set_left_focus(self):
        """Sets left, right, focus flags but does not draw
           or set button values"""
        if not self.grpbuttons:
            return
        names = list(self.grpbuttons.keys())
        if len(names) == 1:
            # no focus with only one group
            return
        if self.leftmore_btn.show:
            self.leftfocus = True
            self.focus = None
        else:
            self.focus = names[0]
        self.rightfocus = False

    def set_right_focus(self):
        """Sets left, right, focus flags but does not draw
           or set button values"""
        if not self.grpbuttons:
            return
        names = list(self.grpbuttons.keys())
        if len(names) == 1:
            # no focus with only one group
            return
        if self.rightmore_btn.show:
            self.rightfocus = True
            self.focus = None
        else:
            self.focus = names[-1]
        self.leftfocus = False


    def draw(self, devicename=None):
        "Draw the line of group buttons"
        if devicename:
            self.devicename = devicename

        device = self.client[self.devicename]

        # grps calculates button positions along the row
        # and stores values for comparison with previous values
        newgrps = GroupBtns(device,
                            self.maxcols,
                            self.focus,
                            self.rightfocus,
                            self.leftfocus,
                            self.leftidx,
                            self.active)

        if self.grps == newgrps:
            # no change, do not draw
            return
        else:
            self.grps = newgrps

        # clear the line
        self.window.clear()
        # initially buttons are not shown
        self.rightmore_btn.show = False
        self.leftmore_btn.show = False

        # groups is a list of group names
        groups = self.grps.groups

        if not self.active in groups:
            self.active = groups[0]

        self.grpbuttons = {}

        if len(groups) == 1:
            self.window.addstr(0, 0, self.grps.text, curses.A_BOLD)
            self.focus = None
            self.rightfocus = False
            self.leftfocus = False
            self.grps.focus = None
            self.grps.rightfocus = False
            self.grps.leftfocus = False
            # no buttons
            return
        elif len(groups) == 2:
            self.window.addstr(0, 0, self.grps.text)
            self.rightfocus = False
            self.leftfocus = False


        buttonmaxidx = len(self.grps.positions)-1
        btnidx = 0
        for idx in range(self.leftidx, len(groups)):
            if btnidx > buttonmaxidx:
                self.rightmore_btn.show = True
                if self.rightfocus:
                    self.rightmore_btn.focus = True
                break
            col,btnlen = self.grps.positions[btnidx]
            btnidx += 1
            groupname = groups[idx]
            self.grpbuttons[groupname] = widgets.Button(self.window, groupname, 0, col, btnlen, onclick=groupname.lower())
            if self.focus == groupname:
                self.grpbuttons[groupname].focus = True
            if self.active == groupname:
                self.grpbuttons[groupname].bold = True

        if self.focus not in self.grpbuttons:
            # it could be that the group has been deleted
            self.focus = None

        for btn in self.grpbuttons.values():
            btn.draw()

        if self.grps.scroll:
            if self.leftidx:
                self.leftmore_btn.show = True
                if self.leftfocus:
                    self.leftmore_btn.focus = True
                self.leftmore_btn.draw()
            if self.rightmore_btn.show:
                self.rightmore_btn.draw()

        if not self.leftmore_btn.focus:
            self.leftfocus = False

        if not self.rightmore_btn.focus:
            self.rightfocus = False

        # after drawing, set these values into self.grps
        self.grps.focus = self.focus
        self.grps.rightfocus = self.rightfocus
        self.grps.leftfocus = self.leftfocus
        self.grps.leftidx = self.leftidx
        self.grps.active = self.active


    def has_focus(self):
        "Returns True if any button has focus"
        if not self.grpbuttons:
            return False
        if self.focus or self.leftfocus or self.rightfocus:
            return True
        else:
            return False


    def setkey(self, key):

        if not self.grpbuttons:
            return key

        if isinstance(key, tuple):
            # mouse pressed, find if its clicked in any field
            if (key in self.leftmore_btn) and self.leftmore_btn.focus:
                key = 10
            elif (key in self.rightmore_btn) and self.rightmore_btn.focus:
                key = 10
            else:
                for button in self.grpbuttons.values():
                    if key in button:
                        # mouse has been pressed in this button
                        if button.focus:
                            # mouse has been pressed on a focused button, equivalent to pressing
                            # enter and choosing the button
                            key = 10
                        break

            # so key is 10 if mouse pressed in a focused field
            # but is still a tuple for mouse clicked somewhere else
            if key != 10:
                # Check if mouse pressed on an unfocussed button
                # so defocus everything else, and focus the new button
                if key in self.leftmore_btn:
                    self.defocus()
                    self.leftfocus = True
                    self.draw()
                    self.window.noutrefresh()
                    return "Newfocus"
                if key in self.rightmore_btn:
                    self.defocus()
                    self.rightfocus = True
                    self.draw()
                    self.window.noutrefresh()
                    return "Newfocus"
                for name, button in self.grpbuttons.items():
                    if key in button:
                        # mouse has been pressed in this button
                        self.defocus()
                        self.focus = name
                        self.draw()
                        self.window.noutrefresh()
                        return "Newfocus"

                # still a tuple, not on any key
                return key

        # at this point, key is not a tuple

        if not self.has_focus():
            # a focus must be set somewhere before any key can be accepted
            return key

        btns = list(self.grpbuttons.keys())

        if key == 10:

            if self.leftfocus:
                # Enter has been pressed when the left 'Prev' button has focus
                if self.leftidx:
                    self.leftidx -= 1
                else:
                    # should never get here
                    return
                if not self.leftidx:
                    # the leftmore btn will vanish
                    self.leftfocus = False
                    self.focus = self.groups()[0]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                return

            if self.rightfocus:
                # Enter has been pressed when the right 'Next' button has
                # focus
                self.leftidx += 1
                if self.leftidx + len(self.grps.positions) == len(self.groups()):
                    # At the last, rightmore button will vanish
                    self.rightfocus = False
                    self.focus = self.groups()[-1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                return

            # to get here, self.focus must be equal to one of the buttons

            # set this focused button as the active button,
            # and return a flag to indicate a new group button has been chosen
            if self.active == self.focus:
                # no change
                return
            # set a change of the active group
            self.active = self.focus
            self.draw()
            self.window.noutrefresh()
            # no need to do curses.doupdate(), as this triggers a new vector window
            return "NewGroup"

        if key in (32, 9, 261):   # space, tab, right arrow; moving along the buttons to the right
            if self.leftfocus:
                # remove focus from left button, and set it on first group button
                self.leftfocus = False
                self.focus = btns[0]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                return
            if self.rightfocus:
                self.rightfocus = False
                self.draw()
                self.window.noutrefresh()
                return 258   # treat as 258 down arrow key
            # is focus at the last button
            if self.focus == btns[-1]:
                # At the last group
                if self.rightmore_btn.show:
                    # there are further groups to the right
                    if key == 261:   # right arrow, scroll groups
                        self.focus = self.groups()[self.leftidx + len(self.grps.positions)]
                        self.leftidx += 1
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        return
                    else:
                        # tab or space, move to rightmore button
                        self.rightfocus = True
                        self.focus = None
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        return
                else:
                    # no rightmore button, so at the very last group
                    return key
            # go to the next group
            indx = btns.index(self.focus)
            # get the new group button in focus
            self.focus = btns[indx+1]
            self.draw()
            self.window.noutrefresh()
            curses.doupdate()
            return
        if key in (353, 260):   # 353 shift tab, 260 left arrow
            if self.rightfocus:
                # group to the left of the rightmore button, now has focus
                self.rightfocus = False
                self.focus = btns[-1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                return
            if self.leftfocus:
                self.leftfocus = False
                self.draw()
                self.window.noutrefresh()
                return key

            # is focus at the first button
            if self.focus == btns[0]:
                # At the first group
                if self.leftmore_btn.show:
                    # there are further groups to the left
                    if key == 260:   # left arrow, scroll groups
                        self.leftidx -= 1
                        self.focus = self.groups()[self.leftidx]
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        return
                    else:
                        # shift tab, move to leftmore button
                        self.leftfocus = True
                        self.focus = None
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        return
                else:
                    # no leftmore button, so at the very first group
                    return key

            # go to the previous group
            indx = btns.index(self.focus)
            # get the new group button in focus
            self.focus = btns[indx-1]
            self.draw()
            self.window.noutrefresh()
            curses.doupdate()
            return


        if key in (338, 339, 258, 259):          # 338 page down, 339 page up, 258 down arrow, 259 up arrow
            return key
        return


class VectorListWin(ParentScreen):


        # topmore row 6
        # botmore row self.maxrows - 4 row 20


    def __init__(self, stdscr, control, devicename):
        super().__init__(stdscr, control)


        self.groupname = None
        self.devicename = devicename
        self.device = None

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, 6, 0) # row 6
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="TopMore")
        self.topmore_btn.show = False

        # vectors window                                            # row 7 blank between more and top vector

        # calculate top and bottom row numbers
        self.vecwintop = 8                                                          # row 8
        # ensure bottom row is an odd number at position self.maxrows - 4 or -5
        row = self.maxrows - 4             # 19
        self.vecwinbot = row - row % 2   # Subtracts 1 if row is even                     # row 19 (leaving rows 20-23)

        # for 24 row window
        # vector window will have row 8 to row 19, displaying 6 vectors, (self.vecwinbot-self.vecwintop+1) // 2  = 6

        # vector window                          19 - 8 + 1 = 12 rows       80            row 8      left col
        self.window = self.stdscr.subwin(self.vecwinbot-self.vecwintop+1, self.maxcols, self.vecwintop, 0)

        # topindex of vector being shown
        self.topindex = 0                   # so six vectors will show vectors with indexes 0-5

        # botmorewin (1 line, full row, starting at self.maxrows - 4, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 4, 0)      # row 20
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="BotMore")
        self.botmore_btn.show = False

        # self.focus will be the name of a vector in focus
        self.focus = None

        # vectornames to vectors in the current group
        self.vectors = {}
        # vectornames to buttons
        self.vecbuttons = {}             # vectornames are original case

        # vector names to vector states of vectors in the current group
        self.vectorstates = {}

        # self.active will be the vector name chosen
        self.active = None


    def noutrefresh(self):
        "Call noutrefresh on more buttons and vector window"
        self.topmorewin.noutrefresh()
        self.window.noutrefresh()
        self.botmorewin.noutrefresh()


    def botindex(self):
        "Returns the index of the bottom vector being displayed"
        # self.topindex is the top vector being displayed
        bottomidx = self.topindex + (self.vecwinbot-self.vecwintop+1) // 2 - 1
        # example  0 + (19-8+1)//2 - 1  = 5
        # example  3 + (19-8+1)//2 - 1  = 8
        lastidx = len(self.vectors)-1
        if bottomidx > lastidx:
            return lastidx
        return bottomidx


    def defocus(self):
        "Remove focus from all buttons, and re-draw the button which had focus"
        if self.focus:
            btn = self.vecbuttons[self.focus]
            btn.focus = False
            btn.draw()
            self.focus = None
        elif self.topmore_btn.focus:
            self.topmore_btn.focus = False
            self.topmore_btn.draw()
        elif self.botmore_btn.focus:
            self.botmore_btn.focus = False
            self.botmore_btn.draw()


    def set_top_focus(self):
        names = list(self.vecbuttons.keys())
        self.defocus()
        if self.topmore_btn.show:
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
        else:
            self.focus = names[0]
            self.vecbuttons[self.focus].draw()


    def set_bot_focus(self):
        names = list(self.vecbuttons.keys())
        self.defocus()
        if self.botmore_btn.show:
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
        else:
            self.focus = names[-1]
            self.vecbuttons[self.focus].draw()


    def draw(self, devicename, groupname, change=False):

        # change is a flag to indicate the window needs to be redrawn

        if (groupname != self.groupname) or (devicename != self.devicename):
            self.topindex = 0
            change = True

        self.devicename = devicename
        self.device = self.client[devicename]
        self.groupname = groupname

        vectornames = [vector.name for vector in self.device.values() if vector.group == self.groupname and vector.enable]
        vectornames.sort()

        if not change:
            currentnames = list(self.vectors.keys())
            if vectornames != currentnames:
                # A change has occurred
                change = True


        # Check if any vector state has changed
        oldstates = list(self.vectorstates.values())

        # vectornames to vectors
        self.vectors = { vectorname:self.device[vectorname] for vectorname in vectornames }
        # vectornames to states
        self.vectorstates = { vector.name:vector.state.lower() for vector in self.vectors.values() }

        newstates = list(self.vectorstates.values())

        if oldstates != newstates:
            # A change has occurred
            change = True

        if not change:
            # no change, therefore do not draw
            return

        # A change to the vectors listed, or to a vector state has occurred
        # proceed to draw the screen

        self.window.clear()
        self.topmorewin.clear()
        self.botmorewin.clear()

        # Remove current vector buttons
        self.vecbuttons.clear()

        bottomidx = self.botindex()

        # draw the vectors in the client with this device and group

        linenumber = 0
        for idx, vectorname in enumerate(self.vectors):
            if idx < self.topindex:
                continue
            if idx > bottomidx:
                break
            # set vectorname as a button, restrict length of name to 20 characters
            self.vecbuttons[vectorname] = widgets.Button(self.window, vectorname, linenumber, 1, 22, onclick=vectorname.lower())
            label = self.vectors[vectorname].label
            lb = label[:27] + "..." if len(label) > 30 else label
            self.window.addstr(linenumber, 30, lb)  # the shortenned label
            lowerstate = self.vectorstates[vectorname].lower()
            if lowerstate == "idle":
                self.window.addstr(linenumber, self.maxcols - 20, "  Idle  ", self.control.color(lowerstate))
            elif lowerstate == "ok":
                self.window.addstr(linenumber, self.maxcols - 20, "  OK    ", self.control.color(lowerstate))
            elif lowerstate == "busy":
                self.window.addstr(linenumber, self.maxcols - 20, "  Busy  ", self.control.color(lowerstate))
            elif lowerstate == "alert":
                self.window.addstr(linenumber, self.maxcols - 20, "  Alert ", self.control.color(lowerstate))
            linenumber += 2  # two lines per button

        # self.vecbuttons is a vectorname to button dictionary, but only for buttons displayed

        # Note: initially all vector buttons are created with focus False
        # self.focus has the name of the vector which should be in focus
        # so if it is set, set the appropriate button focus

        if self.focus:
            if self.focus in self.vecbuttons:
                self.vecbuttons[self.focus].focus = True
            else:
                self.focus = None

        # if self.topindex is not zero, then draw top more button
        if self.topindex:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # draw vector buttons
        for vecbutton in self.vecbuttons.values():
            vecbutton.draw()

        # bottomidx is the index of the bottom vector being displayed
        if bottomidx < len(self.vectors) -1:
            self.botmore_btn.show = True
        else:
            self.botmore_btn.show = False
        self.botmore_btn.draw()


    def topmorechosen(self):
        """Update when topmore button which should already be in focus is pressed
           to scroll vectors"""
        if not self.topmore_btn.focus:
            return
        if not self.topindex:    # self.topindex cannot be zero
            return

        # names is a list of all vector names
        names = list(self.vectors.keys())

        self.topindex -= 1

        if not self.topindex:
            # at the top device
            self.topmore_btn.focus = False
            self.focus = names[0]

        # draw will sort out top and bottom
        # more buttons
        self.draw(self.devicename, self.groupname, change=True)
        self.noutrefresh()


    def botmorechosen(self):
        """Update when botmore button which should already be in focus is pressed
           to scroll vectors"""
        if not self.botmore_btn.focus:
            return

        # the aim is to increment self.topindex
        # but doing so may display last bottom vector
        # which makes botmore button dissapear

        # vectors is a dictionary of vectornames to vectors
        # names is a list of all vector names
        names = list(self.vectors.keys())

        new_top_idx = self.topindex + 1

        new_bot_idx = new_top_idx + (self.vecwinbot-self.vecwintop) // 2 - 1
        # lastidx is the index of the last vector
        lastidx = len(names)-1

        if new_bot_idx <= lastidx:
            # so increment topindex
            self.topindex = new_top_idx
            if new_bot_idx == lastidx:
                # cannot increment further
                self.botmore_btn.show = False
                self.focus = names[-1]
        else:
            # no point incrementing topindex as it does not display any new vector
            self.botmore_btn.show = False
            self.focus = names[-1]        # set focus to name of last device

        self.draw(self.devicename, self.groupname, change=True)
        self.noutrefresh()


    def setkey(self, key):

        names = list(self.vectors.keys())
        lastidx = len(names)-1            # index of last vector

        displayedbtns = list(self.vecbuttons.values())
        displayednames = list(self.vecbuttons.keys())
        bottomidx = self.botindex()       # index of last displayed vector


        if isinstance(key, tuple):
            # mouse pressed, find if its clicked in any field
            if (key in self.topmore_btn) and self.topmore_btn.focus:
                self.topmorechosen()
                curses.doupdate()
                return    # returning None indicates no further action needed

            if (key in self.botmore_btn) and self.botmore_btn.focus:
                self.botmorechosen()
                curses.doupdate()
                return    # returning None indicates no further action needed

            for button in self.vecbuttons.values():
                if key in button:
                    # mouse has been pressed in this button
                    if button.focus:
                        self.active = self.focus
                        return "NewVector"

            # So check if mouse pressed on any unfocussed button
            if key in self.topmore_btn:
                self.set_top_focus()
                self.noutrefresh()
                curses.doupdate()
                return "Newfocus"

            if key in self.botmore_btn:
                self.set_bot_focus()
                self.noutrefresh()
                curses.doupdate()
                return "Newfocus"

            for name, button in self.vecbuttons.items():
                if key in button:
                    # mouse has been pressed in this button
                    self.defocus()
                    button.focus = True
                    button.draw()
                    self.focus = name
                    self.noutrefresh()
                    curses.doupdate()
                    return "Newfocus"

            # to get here, the mouse tuple is not on any button
            return key

        # so from here, only deal with key presses

        if key == 10:
            if self.topmore_btn.focus:
                self.topmorechosen()
                curses.doupdate()
            elif self.botmore_btn.focus:
                self.botmorechosen()
                curses.doupdate()
            elif self.focus:
                self.active = self.focus
                return "NewVector"

        elif key in (32, 9, 261, 338, 258):
            # go to the next
            if self.botmore_btn.focus:
                self.botmore_btn.focus = False
                self.draw(self.devicename, self.groupname, change=True)
                self.noutrefresh()
                curses.doupdate()
                return key
            elif self.topmore_btn.focus:
                self.topmore_btn.focus = False
                self.focus = displayednames[0]
            else:
                # one of the vectors has focus
                try:
                    indx = names.index(self.focus)
                except ValueError:
                    return
                # indx here is the index on the list of all devices, not just those displayed
                if indx == lastidx:
                    # very last device, the botmore_btn should not be shown
                    self.focus = None
                    self.draw(self.devicename, self.groupname, change=True)
                    self.noutrefresh()
                    curses.doupdate()
                    return key
                elif indx == bottomidx:
                    # last displayed device
                    if key in (338, 258):      # 338 page down, 258 down arrow
                        # display next device
                        self.topindex += 1
                        self.focus = names[indx+1]
                    else:
                        # last device on display
                        self.focus = None
                        self.botmore_btn.focus = True
                else:
                    self.focus = names[indx+1]


        elif key in (353, 260, 339, 259):  # 353 shift tab, 260 left arrow, 339 page up, 259 up arrow
            # go to previous button
            if self.botmore_btn.focus:
                self.botmore_btn.focus = False
                self.focus = displayednames[-1]
            elif self.topmore_btn.focus:
                self.topmore_btn.focus = False
                self.draw(self.devicename, self.groupname, change=True)
                self.noutrefresh()
                curses.doupdate()
                return key
            elif self.focus == names[0]:
                self.focus = None
                self.draw(self.devicename, self.groupname, change=True)
                self.noutrefresh()
                curses.doupdate()
                return key
            else:
                try:
                    indx = names.index(self.focus)
                except ValueError:
                    return
                if indx == self.topindex:
                    if key in (339, 259): # 339 page up, 259 up arrow
                        self.topindex -= 1
                        self.focus = names[indx-1]
                    else:
                        self.focus = None
                        self.topmore_btn.focus = True
                else:
                    self.focus = names[indx-1]

        self.draw(self.devicename, self.groupname, change=True)
        self.noutrefresh()
        curses.doupdate()



class VectorScreen(ConsoleClientScreen):

    "This displays the chosen vector and its members"


    def __init__(self, stdscr, control, devicename, vectorname):
        super().__init__(stdscr, control)

        self.devicename = devicename
        self.vectorname = vectorname

        self.device = self.client[self.devicename]
        self.vector = self.device[self.vectorname]

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        devicetitle = widgets.shorten("Device: " + self.devicename, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(0, 1, devicetitle)
        vectortitle = widgets.shorten("Vector: " + self.vectorname, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(1, 1, vectortitle)
        labeltitle = widgets.shorten(self.vector.label, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(2, 1, labeltitle, curses.A_BOLD)

        # messages window (1 line, full row, starting at 3,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 3, 0)

        # timestamp and state window (1 line, full row, starting at 4,0)
        self.tstatewin = self.stdscr.subwin(1, self.maxcols, 4, 0)

        # window showing the members of the vector
        self.memberswin = MembersWin(self.stdscr, self.control, self.tstatewin, self.vector)

        # list areas of the screen, one of these areas has the current 'focus'
        # Members being the area showing the members associated with the vector
        # Vectors, Devices, Messages and Quit are the bottom buttons
        self.screenparts = ("Members", "Vectors", "Devices", "Messages", "Quit")

        # bottom buttons, [Vectors] [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.vectors_btn = widgets.Button(self.buttwin, "Vectors", 0, self.maxcols//2 - 20)
        self.vectors_btn.focus = True

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10)
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 11)


    def show(self):
        "Displays the window"

        devices = [ devicename for devicename, device in self.client.items() if device.enable ]

        if self.devicename not in devices:
            widgets.drawmessage(self.messwin, f"{self.devicename} not found!", maxcols=self.maxcols)
            self.vectors_btn.draw()
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.titlewin.noutrefresh()
            self.messwin.noutrefresh()
            self.buttwin.noutrefresh()

            curses.doupdate()
            return
        self.device = self.client[self.devicename]

        vectors = [ vectorname for vectorname, vector in self.device.items() if vector.enable ]


        if self.vectorname not in vectors:
            widgets.drawmessage(self.messwin, f"{self.vectorname} not found!", maxcols=self.maxcols)
            self.vectors_btn.draw()
            self.devices_btn.draw()
            self.messages_btn.draw()
            self.quit_btn.draw()

            self.titlewin.noutrefresh()
            self.messwin.noutrefresh()
            self.buttwin.noutrefresh()

            curses.doupdate()
            return
        self.vector = self.device[self.vectorname]

        if self.vector.message:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.vector.message, maxcols=self.maxcols)

        widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)

        # draw the bottom buttons
        self.vectors_btn.draw()
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        # Draw the members widgets
        self.memberswin.draw()


        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.tstatewin.noutrefresh()
        self.buttwin.noutrefresh()
        self.memberswin.noutrefresh()

        curses.doupdate()


    def setfocus(self, newfocus):
        """Sets item in focus to newfocus
           If newfocus is one of Vectors, Messages, Quit, Devices, sets the
           new focus on the button, draws and calls self.buttwin.noutrefresh()
           and removes focus from all other buttons.
           """
        if self.memberswin.focus:
            # current focus is on the subwindows
            if newfocus != "Members":
                self.memberswin.defocus()
                self.memberswin.noutrefresh()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
                self.buttwin.noutrefresh()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
                self.buttwin.noutrefresh()
            return

        # current focus must be one of the bottom buttons
        if self.vectors_btn.focus and newfocus != "Vectors":
            self.vectors_btn.focus = False
            self.vectors_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            self.buttwin.noutrefresh()
        elif self.devices_btn.focus and newfocus != "Devices":
            self.devices_btn.focus = False
            self.devices_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
            self.buttwin.noutrefresh()
        elif self.messages_btn.focus and newfocus != "Messages":
            self.messages_btn.focus = False
            self.messages_btn.draw()
            if newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            elif newfocus == "Quit":
                self.quit_btn.focus = True
                self.quit_btn.draw()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
            self.buttwin.noutrefresh()
        elif self.quit_btn.focus and newfocus != "Quit":
            self.quit_btn.focus = False
            self.quit_btn.draw()
            if newfocus == "Messages":
                self.messages_btn.focus = True
                self.messages_btn.draw()
            elif newfocus == "Devices":
                self.devices_btn.focus = True
                self.devices_btn.draw()
            elif newfocus == "Vectors":
                self.vectors_btn.focus = True
                self.vectors_btn.draw()
            self.buttwin.noutrefresh()

    def timeout(self, event):
        "A timeout event has occurred, update the vector state"
        if self.vector.state == "Busy":
            self.vector.state = "Alert"
            self.vector.timestamp = event.timestamp
            widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)
            widgets.drawmessage(self.messwin, "Timeout", bold=True) #, maxcols=8)
            self.tstatewin.noutrefresh()
            self.messwin.noutrefresh()
            curses.doupdate()

    def update(self, event):
        "An event affecting this vector has occurred, re-draw the screen"

        self.titlewin.clear()

        devicetitle = widgets.shorten("Device: " + self.devicename, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(0, 1, devicetitle)
        vectortitle = widgets.shorten("Vector: " + self.vectorname, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(1, 1, vectortitle)
        labeltitle = widgets.shorten(self.vector.label, width=self.maxcols-5, placeholder="...")
        self.titlewin.addstr(2, 1, labeltitle, curses.A_BOLD)

        self.messwin.clear()
        self.tstatewin.clear()
        self.buttwin.clear()
        # self.memberswin does not need a clear() call, as its window is cleared in its draw method

        self.show()
        # calling self.show in turn calls button and members draw and noutrefresh methods

        # after an update, the cursor may need putting back into an editable field
        if self.memberswin.focus:
            index = self.memberswin.widgetindex_in_focus()
            if not index is None:
                widget = self.memberswin.memberwidgets[index]
                if hasattr(widget, "edit_txt"):
                    if widget.edit_txt.focus:
                        editstring = widget.edit_txt.editstring(self.stdscr)
                        editstring.movecurs()
                        curses.doupdate()


    def check_bottom_btn(self, key):
        """Takes action if a bottom button is pressed
           returns action Quit etc... if a key action is to be taken
           returns None if this method has dealt with the action, and the calling
           routine can continue and obtain another key.
           Returns the key, if the key has not been handled and
           has to be checked further"""

        if isinstance(key, tuple):
            # mouse pressed, find if its clicked in any
            # of the bottom buttons
            if key in self.quit_btn:
                if self.quit_btn.focus:
                    widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                    self.messwin.noutrefresh()
                    curses.doupdate()
                    return "Quit"
                else:
                    # focus is elsewhere
                    self.setfocus("Quit")
                curses.doupdate()
                return
            if key in self.messages_btn:
                if self.messages_btn.focus:
                    return "Messages"
                else:
                    self.setfocus("Messages")
                curses.doupdate()
                return
            if key in self.devices_btn:
                if self.devices_btn.focus:
                    return "Devices"
                else:
                    self.setfocus("Devices")
                curses.doupdate()
                return
            if key in self.vectors_btn:
                if self.vectors_btn.focus:
                    return "Vectors"
                else:
                    self.setfocus("Vectors")
                curses.doupdate()
                return
        elif self.vectors_btn.focus or self.devices_btn.focus or self.messages_btn.focus or self.quit_btn.focus:
            # not a tuple, but one of the buttons is in focus, so check if a relevant key pressed
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
                    self.memberswin.set_topfocus()
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
                    self.memberswin.set_botfocus()
                elif self.devices_btn.focus:
                    self.devices_btn.focus = False
                    self.vectors_btn.focus = True
                elif self.messages_btn.focus:
                    self.messages_btn.focus = False
                    self.devices_btn.focus = True
                elif self.quit_btn.focus:
                    self.quit_btn.focus = False
                    self.messages_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                return
            elif key == 10:
                if self.vectors_btn.focus:
                    return "Vectors"
                elif self.devices_btn.focus:
                    return "Devices"
                elif self.messages_btn.focus:
                    return "Messages"
                elif self.quit_btn.focus:
                    return "Quit"
            else:
                # key is a key press, not a mouse tuple, and a bottom
                # button is in focus but the key is not one that initiates
                # any action, so return None to indicate it can be ignored
                return
        # if mouse, it is not clicked on any bottom button
        # if a key, then no bottom button is in focus
        # so just return the key
        return key

    async def inputs(self):
        "Gets inputs from the screen"

        # two loops formed here, one for the entire screen
        # and one for an editable field
        # result tracks the results of tests to see if an editable field loop is needed
        result = None

        self.stdscr.nodelay(True)
        while True:
            if result:
                key = result
                result = None
            else:
                key = await self.keyinput()

            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key

            key = self.check_bottom_btn(key)
            if not key:
                continue
            if key in ("Vectors", "Devices", "Messages", "Quit"):
                return key

            # At this point, key could be a mouse tuple, or a keystroke
            # But not clicked on any of the bottom buttons
            # So could be mouse clicked away from anything, or on something in memberswin
            # or maybe memberswin has the focus, and the keystroke should be handled there

            if isinstance(key, tuple):
                # mouse pressed, find if its clicked in any of the MembersWin fields
                result = self.memberswin.handlemouse(key)
                # result is None if fully handled,
                # or is 'edit' if mouse clicked in an editable field in MembersWin
                # or is 'focused' if mouse clicked on a previously unfocused button
                # could also be one of "submitted", "next", "previous" if clicked
                # on a focused submit, or top or bottom widget
                if not result:
                    # Handled, continue with while loop and get next key
                    continue

            # At this point, result is None if key is a keystroke,
            # or result is value returned by memberswin.handlemouse(key)

            if (result == "focused") or (result == "edit"):
                # a field in self.memberswin has been set into focus
                # ensure bottom buttons are defocused
                self.vectors_btn.focus = False
                self.vectors_btn.draw()
                self.devices_btn.focus = False
                self.devices_btn.draw()
                self.messages_btn.focus = False
                self.messages_btn.draw()
                self.quit_btn.focus = False
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()

            if result == "focused":
                # A button has been set to focus, nothing more to do
                # continue and get the next key
                result = None
                continue

            if (not result) and (not self.memberswin.focus):
                # if keystroke, then only of interest if memberswin has focus
                continue

            if not result:
                # key is a keystroke, and memberswin has focus, handle it
                result = self.memberswin.setkey(key)
                # this returns "edit" if an editable field has been given focus
                # could also be "submitted", "next", "previous" or a keystroke such
                # as 9 for tab

            while result == "edit":
               # An editable field is in focus
                inputfield = self.memberswin.inputfield()
                if inputfield is None:
                    break
                result = await inputfield()
                if result in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                    return result
                if not result:
                    break
                if result in ("submitted", "next", "previous"):
                    break
                if isinstance(result, tuple):
                    # a mouse press, go to outer loop with result set
                    break
                # inputfield has returned a keystroke, typically 9 for next tab
                # which is now tested again with self.memberswin.setkey(key)
                result = self.memberswin.setkey(result)

            if result in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return result

            if result == "submitted":
                self.vector.state = 'Busy'
                # The vector has been submitted, draw vector state which is now busy
                widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)
                self.tstatewin.noutrefresh()
                self.vectors_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                result = None
            elif result == "next":   # go to next button
                self.memberswin.defocus() # removes focus and calls draw and noutrefresh on memberswin
                self.vectors_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                result = None
            elif result == "previous":   # go to prev button
                self.memberswin.defocus() # removes focus and calls draw and noutrefresh on memberswin
                self.quit_btn.focus = True
                self.buttwin.clear()
                self.vectors_btn.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()
                self.buttwin.noutrefresh()
                curses.doupdate()
                result = None


# MembersWin is created within VectorScreen


class MembersWin(ParentScreen):

    "Used to display the vector members"


    def __init__(self, stdscr, control, tstatewin, vector):
        super().__init__(stdscr, control)

        self.tstatewin = tstatewin
        self.vector = vector
        self.vectorname = vector.name

        # top more btn on 7th line ( coords 0 to 6 )
        # bot more btn on line (self.maxrows - 3) + 1
        # displaylines = (self.maxrows - 2) - 7  - 1


        # members window
        memwintop = 8                                          # row index 8
        memwinbot = self.maxrows - 4                           # row index 20

        # botmorerow is one below the members window
        botmorerow = memwinbot + 1                             # row index 21
        self.displaylines = memwinbot - memwintop + 1          # self.maxrows - 4  - 8 + 1 = 13

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="TopMore")
        self.topmore_btn.show = False

        # members window
        self.memwin = self.stdscr.subwin(self.displaylines, self.maxcols, memwintop, 0)

        # topindex of member being shown
        self.topindex = 0                   # so six members will show members with indexes 0-5

        # dictionary of member name to member this vector owns
        members_dict = self.vector.members()

        # list of member names in alphabetic order
        self.membernames = sorted(members_dict.keys())

        # namelen is length of name button
        namelen = max(len(name) for name in self.membernames)

        # create the member widgets
        self.memberwidgets = []
        for name in self.membernames:
            if self.vector.vectortype == "SwitchVector":
                self.memberwidgets.append(widgets.SwitchMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "LightVector":
                self.memberwidgets.append(widgets.LightMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "NumberVector":
                self.memberwidgets.append(widgets.NumberMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "TextVector":
                self.memberwidgets.append(widgets.TextMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))
            elif self.vector.vectortype == "BLOBVector":
                self.memberwidgets.append(widgets.BLOBMember(self.stdscr, self.control, self.memwin, self.tstatewin, self.vector, name, namelen))


        # Sets list of displayed widgets, self.displayed
        self.displayedwidgets()


        # note a widget has two indexes, its index in self.memberwidgets and its index in self.displayed

        # displayedindex = memberwidgetsindex - self.topindex  limited by size of self.displayed
        # memberwidgetsindex = displayedindex + self.topindex

        # this is True, if this widget is in focus
        self.focus = False

        # botmorewin = 1 line height, columns just over half of self.maxrows, to give room on the right for submitwin
        # starting at y = columns - 11, x = 0)
        botmorewincols = self.maxcols//2 + 4
        self.botmorewin = self.stdscr.subwin(1, botmorewincols, botmorerow, 0)
        if self.vector.perm == 'ro':
            self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, botmorewincols-11)
        else:
            self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, botmorewincols-20)
        self.botmore_btn.show = False
        self.botmore_btn.focus = False

        # submitwin holding submit_btn and cancel_btn, located to the right of botmorewin
        # submitwin = 1 line height, starting at y=botmorerow, x = botmorewincols + 1
        # width = self.maxcols -x - 2
        self.submitwin = self.stdscr.subwin(1, self.maxcols - botmorewincols - 3, botmorerow, botmorewincols + 1)
        self.submit_btn = widgets.Button(self.submitwin, "Submit", 0, 0)
        self.cancel_btn = widgets.Button(self.submitwin, "Cancel", 0, 12)
        if (self.vector.perm == 'ro') or (self.vector.vectortype == "BLOBVector"):
            self.submit_btn.show = False
            self.cancel_btn.show = False
        else:
            self.submit_btn.show = True
            self.cancel_btn.show = True

        # keep these in a list for easy reference
        self.controlbtns = [ self.topmore_btn, self.botmore_btn, self.submit_btn, self.cancel_btn]

        # this will be set to a widgets awitable input field if it gets focus
        self._inputfield = None


    def displayedwidgets(self):
        "Sets list of widgets displayed"
        self.displayed = []
        line = 0
        for widget in self.memberwidgets[self.topindex:]:
            if line+widget.linecount > self.displaylines:
                break
            self.displayed.append(widget)
            line += widget.linecount


    def defocus(self):
        "Removes focus from all buttons"
        self.focus = False
        for widget in self.displayed:
            if widget.focus:
                widget.focus = False
                widget.draw()
                self.memwin.noutrefresh()
                return
        for btn in self.controlbtns:
            if btn.focus:
                btn.focus = False
                btn.draw()
                btn.window.noutrefresh()
                return


    def set_topfocus(self):
        "Sets topmore_btn focus, or if not shown, sets top widget focus"
        self.defocus()
        self.focus = True
        if self.topindex:
            # self.topindex is not zero, so topmore button must be shown
            # and with focus set
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
            self.topmorewin.noutrefresh()
        else:
            # self.topindex is zero, so top member widget must have focus
            # and with focus set
            widget = self.displayed[0]
            widget.focus = True
            widget.draw()
            self.memwin.noutrefresh()


    def set_botfocus(self):
        """Sets cancel_btn focus, or if not shown
           sets botmore_btn focus, or if not shown,
           sets bottom widget focus"""
        self.defocus()
        self.focus = True

        if self.cancel_btn.show:
            self.cancel_btn.focus = True
            self.cancel_btn.draw()
            self.submitwin.noutrefresh()
            return

        # no submit/cancel button, so either bottom widget is set in focus
        # or bottom more button is set in focus

        if self.botmore_btn.show:
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
            self.botmorewin.noutrefresh()
            return

        # set focus on bottom member widget
        widget = self.displayed[-1]
        widget.focus = True
        widget.draw()
        self.memwin.noutrefresh()



    def draw(self):
        "Clears and draws the screen, but does not call noutrefresh or curses.doupdate()"
        self.memwin.clear()

        # draw the member widgets being displayed
        line = 0
        for memberwidget in self.displayed:
            memberwidget.draw(line)
            line = line+memberwidget.linecount

        if self.topindex:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # Is the bottom widget being displayed?
        # displayedindex = memberwidgetsindex - self.topindex  limited by size of self.displayed
        # memberwidgetsindex = displayedindex + self.topindex

        # displayedindex of last widget displayed
        displayedindex = len(self.displayed) - 1
        memberwidgetsindex = displayedindex + self.topindex

        if memberwidgetsindex == len(self.memberwidgets) -1:
            # very last widget
            self.botmore_btn.show = False
        else:
            self.botmore_btn.show = True
        self.botmore_btn.draw()

        self.submit_btn.draw()
        self.cancel_btn.draw()


    def noutrefresh(self):
        """Refresh this objects entire window, including widgets,
           top and bottom buttons, and submt and cancel buttons"""
        self.topmorewin.noutrefresh()
        self.memwin.noutrefresh()
        self.botmorewin.noutrefresh()
        self.submitwin.noutrefresh()


    def widgetindex_in_focus(self):
        "Returns the memberwidget index which has focus, or None"
        for index,widget in enumerate(self.memberwidgets):
            if widget.focus:
                return index

    def displayed_widgetindex_in_focus(self):
        "Returns the self.displayed index which has focus, or None"
        for index,widget in enumerate(self.displayed):
            if widget.focus:
                return index


    def inputfield(self):
        "Returns None, or an awaitable widget inputfield"
        if self.vector.perm == "ro":
            return
        return self._inputfield


    def handlemouse(self, key):
        "Handles a mouse input"
        if key in self.topmore_btn:
            if self.topmore_btn.focus:
                # same as pressing enter on the focused button
                self.setkey(10)
                return
            else:
                # key is on topmore_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.topmore_btn.focus = True
                self.topmore_btn.draw()
                self.topmorewin.noutrefresh()
                return "focused"

        if key in self.botmore_btn:
            if self.botmore_btn.focus:
                # same as pressing enter on the focused button
                self.setkey(10)
                return
            else:
                # key is on botmore_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.botmore_btn.focus = True
                self.botmore_btn.draw()
                self.botmorewin.noutrefresh()
                return "focused"

        if key in self.submit_btn:
            if self.submit_btn.focus:
                # same as pressing enter on the focused button
                result = self.setkey(10)  # this may return "submitted"
                return result
            else:
                # key is on submit_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.submit_btn.focus = True
                self.submit_btn.draw()
                self.submitwin.noutrefresh()
                return "focused"

        if key in self.cancel_btn:
            if self.cancel_btn.focus:
                # same as pressing enter on the focused button
                self.setkey(10)
                return
            else:
                # key is on cancel_btn, but it does not have focus
                self.defocus()
                self.focus = True
                self.cancel_btn.focus = True
                self.cancel_btn.draw()
                self.submitwin.noutrefresh()
                return "focused"

        # next check - has the mouse key been pressed on a widget
        result = None
        windex = None
        for index, widget in enumerate(self.displayed):
            result = widget.handlemouse(key)
            # result is "focused' or 'edit' if mouse landed on a field
            if result:
                windex = index
                break


        if result == "set_on":  ###
            # special case of a switch widget being turned on
            # set all other widgets Off
            for widget in self.memberwidgets:
                if not widget.focus:
                    widget.on.bold = False
                    widget.off.bold = True
                    widget.on.draw()
                    widget.off.draw()
            self.memwin.noutrefresh()
            return "focused"

        if result:
            # remove focus from any other button
            for index, widget in enumerate(self.displayed):
                if index == windex:
                    continue
                if widget.focus:
                    widget.focus = False
                    widget.draw()
                    break
            # so widget focus has been drawn
            self.memwin.noutrefresh()
            for btn in self.controlbtns:
                if btn.focus:
                    btn.focus = False
                    btn.draw()
                    btn.window.noutrefresh()
                    break
            # and indicate this window has focus
            self.focus = True

        if result == "edit":
            widget = self.displayed[windex]
            self._inputfield = widget.inputfield
        return result



    def setkey(self, key):
        "Handles a key stroke"

        # check if a widget is in focus
        if self.vector.perm != "ro":
            # if ro, nothing to set on widgets
            for widget in self.displayed:
                if widget.focus:
                    # a widget is in focus
                    result = widget.setkey(key)
                    if result == "edit":
                        # this sets an input awaitable
                        self._inputfield = widget.inputfield
                        return result
                    else:
                        self._inputfield = None
                    if result == "set_on":  ###
                        # special case of a switch widget being turned on
                        # set all other widgets Off
                        for widget in self.memberwidgets:
                            if not widget.focus:
                                widget.on.bold = False
                                widget.off.bold = True
                                widget.on.draw()
                                widget.off.draw()
                        self.memwin.noutrefresh()
                        curses.doupdate()
                        return
                    if result:
                        # if the widget returns a key. then continue with
                        # checking it
                        key = result
                        break
                    # the widget has handled the key, and returns None
                    # to indicate no further checks required.
                    return

        if key == 10:
            # Enter key pressed
            if self.topmore_btn.focus:
                # scroll the window down
                self.topindex -= 1
                self.displayedwidgets()
                if not self.topindex:
                    # self.topindex is now zero, so self.topmore_btn will not be shown
                    # and the top widget should get focus
                    topwidget = self.displayed[0]
                    topwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return
            elif self.botmore_btn.focus:
                # scroll the window up
                self.topindex += 1
                self.displayedwidgets()
                # displayedindex of last widget displayed
                displayedindex = len(self.displayed) - 1
                memberwidgetsindex = displayedindex + self.topindex
                if memberwidgetsindex == len(self.memberwidgets) -1:
                    # the last widget is being displayed, so self.botmore_btn will not be shown
                    # and the bottom widget should get focus
                    botwidget = self.memberwidgets[-1]
                    botwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return
            elif self.vector.perm == "ro":
                # can scroll up or down, with more buttons,
                # but nothing to submit, so Enter key ignored
                return
            elif self.submit_btn.focus:
                if submitvector(self.vector, self.memberwidgets):
                    # vector has been submitted, remove focus from this window
                    self.focus = False
                    self.submit_btn.focus = False
                    self.submit_btn.ok()   # draw submit button in green with ok
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    time.sleep(0.3)      # blocking, to avoid screen being changed while this time elapses
                    self.submitwin.clear()
                    self.submit_btn.draw()
                    self.cancel_btn.draw()
                    self.submitwin.noutrefresh()
                    # curses.doupdate() - not needed, called by vector window on submission
                    return "submitted"
                else:
                    # error condition
                    self.submit_btn.alert()
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    time.sleep(0.3)        # blocking, to avoid screen being changed while this time elapses
                    self.submitwin.clear()
                    self.submit_btn.draw()
                    self.cancel_btn.draw()
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    return
            elif self.cancel_btn.focus:
                # Cancel chosen, reset all widgets, removing any value changes
                for memberwidget in self.displayed:
                    memberwidget.reset()
                self.memwin.noutrefresh()
                curses.doupdate()
                return
            else:
                # Enter pressed, but none of the above have handled it
                return

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

        if key in (32, 9, 261, 338, 258):   # go to next button
            if self.cancel_btn.focus:
                # last in this window
                return "next"
            if self.submit_btn.focus:
                self.submit_btn.focus = False
                self.cancel_btn.focus = True
                self.submit_btn.draw()
                self.cancel_btn.draw()
                self.submitwin.noutrefresh()
                curses.doupdate()
                return
            if self.botmore_btn.focus:
                if self.submit_btn.show:
                    self.botmore_btn.focus = False
                    self.botmore_btn.draw()
                    self.submit_btn.focus = True
                    self.submit_btn.draw()
                    self.botmorewin.noutrefresh()
                    self.submitwin.noutrefresh()
                    curses.doupdate()
                    return
                else:
                    return "next"
            # get the top widget being displayed
            if self.topmore_btn.focus:
                self.topmore_btn.focus = False
                self.topmore_btn.draw()
                nextwidget = self.displayed[0]
                nextwidget.focus = True
                nextwidget.draw()
                self.topmorewin.noutrefresh()
                self.memwin.noutrefresh()
                curses.doupdate()
                return

            if (displayedindex := self.displayed_widgetindex_in_focus()) is not None:
                # A widget is in focus
                widget = self.displayed[displayedindex]
                if displayedindex != len(self.displayed) - 1:
                    # the displayed widget is not the last widget on the list of displayed widgets
                    # so simply set the next widget into focus
                    widget.focus = False
                    widget.draw()
                    nextwidget = self.displayed[displayedindex+1]
                    nextwidget.focus = True
                    nextwidget.draw()
                    self.memwin.noutrefresh()
                    curses.doupdate()
                    return
                # The widget in focus is the last of the displayed widgets
                # Either scroll up, or jump to more ....
                widgetindex = displayedindex + self.topindex
                if widgetindex == len(self.memberwidgets) -1:
                    # This is the last widget, the more button will not be shown, but the submit button may be
                    if self.submit_btn.show:
                        widget.focus = False
                        widget.draw()
                        self.submit_btn.focus = True
                        self.submit_btn.draw()
                        self.memwin.noutrefresh()
                        self.submitwin.noutrefresh()
                        curses.doupdate()
                        return
                    # last widget and the submit is not shown
                    return "next"
                # last displayed widgets, but there are further widgets to be shown
                if key == 9:
                    # tab key pressed, set the botmore button in focus
                    widget.focus = False
                    widget.draw()
                    self.botmore_btn.focus = True
                    self.botmore_btn.draw()
                    self.memwin.noutrefresh()
                    self.botmorewin.noutrefresh()
                    curses.doupdate()
                    return
                # next required, but not tab and not last widget,
                # so scroll the window up
                widget.focus = False
                widget.draw()
                self.topindex += 1
                self.displayedwidgets()
                nextwidget = self.displayed[-1]
                nextwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

        if key in (353, 260, 339, 259):   # go to prev button

            if self.cancel_btn.focus:
                # go to submit button
                self.cancel_btn.focus = False
                self.submit_btn.focus = True
                self.cancel_btn.draw()
                self.submit_btn.draw()
                self.submitwin.noutrefresh()
                curses.doupdate()
                return
            if self.submit_btn.focus:
                self.submit_btn.focus = False
                self.submit_btn.draw()
                self.submitwin.noutrefresh()
                if self.botmore_btn.show:
                    self.botmore_btn.focus = True
                    self.botmore_btn.draw()
                    self.botmorewin.noutrefresh()
                    curses.doupdate()
                    return
                # set bottom displayed widget into focus
                widget = self.displayed[-1]
                widget.focus = True
                widget.draw()
                self.memwin.noutrefresh()
                curses.doupdate()
                return
            if self.botmore_btn.focus:
                # set bottom displayed widget into focus
                self.botmore_btn.focus = False
                self.botmore_btn.draw()
                self.botmorewin.noutrefresh()
                widget = self.displayed[-1]
                widget.focus = True
                widget.draw()
                self.memwin.noutrefresh()
                curses.doupdate()
                return
            if self.topmore_btn.focus:
                # top button of this window
                return "previous"
            # So now check if a member button is in focus
            if (displayedindex := self.displayed_widgetindex_in_focus()) is not None:
                # A widget is in focus
                widget = self.displayed[displayedindex]
                if displayedindex:
                    # not zero, so focus can just move up one
                    widget.focus = False
                    widget.draw()
                    prevwidget = self.displayed[displayedindex-1]
                    prevwidget.focus = True
                    prevwidget.draw()
                    self.memwin.noutrefresh()
                    curses.doupdate()
                    return
                # showing top widget of the displayed widgets
                # Either scroll down, or jump to more ....
                # self.topindex is the widget index
                if not self.topindex:
                    # This is the first widget, the more button will not be shown
                    return "previous"
                # top displayed widgets, but more can be shown, if shift-tab pressed,
                # jump to topmore
                if key == 353:
                    # shift tab key pressed, set the topmore button in focus
                    widget.focus = False
                    widget.draw()
                    self.topmore_btn.focus = True
                    self.topmore_btn.draw()
                    self.memwin.noutrefresh()
                    self.topmorewin.noutrefresh()
                    curses.doupdate()
                    return
                # prev required, but not shift-tab and not first widget,
                # so scroll the window down
                widget.focus = False
                widget.draw()
                self.topindex -= 1
                self.displayedwidgets()
                prevwidget = self.displayed[0]
                prevwidget.focus = True
                self.draw()
                self.noutrefresh()
                curses.doupdate()
                return



def submitvector(vector, memberwidgets):
    "Checks and submits the vector, if ok returns True, if not returns False"
    if vector.vectortype == "SwitchVector":
        members = {member.name:member.newvalue() for member in memberwidgets}
        # members is a dictionary of membername : member value ('On' or 'Off')
        # check if switches obey the switch rules 'OneOfMany','AtMostOne','AnyOfMany'
        oncount = sum(value == 'On' for value in members.values())
        if (vector.rule == 'OneOfMany') and oncount != 1:
            # one, and only one must be set
            return False
        if (vector.rule == 'AtMostOne') and oncount > 1:
            # one, or none can be set, but not more than 1
            return False
        vector.send_newSwitchVector(members=members)
        return True
    elif vector.vectortype == "NumberVector":
        members = {member.name:member.newvalue() for member in memberwidgets}
        # members is a dictionary of membername : member value (new number string)
        vector.send_newNumberVector(members=members)
        return True
    elif vector.vectortype == "TextVector":
        members = {member.name:member.newvalue() for member in memberwidgets}
        # members is a dictionary of membername : member value (new text string)
        vector.send_newTextVector(members=members)
        return True
    # BLOBVector's are not called with submit button
    # each member has its own send button
    # LightVectors are ro and cannot be submitted
    return False
