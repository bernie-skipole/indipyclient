
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
           Otherwise returns the key pressed or a tuple of mouse button release coordinates."""
        while True:
            if self.control.stop:
                return "Stop"
            if self._close:
                return self._close
            key = self.stdscr.getch()
            if key == -1:
                await asyncio.sleep(0.02)
                continue
            if key == curses.KEY_RESIZE:
                return "Resize"
            if key == curses.KEY_MOUSE:
                try:
                    mouse = curses.getmouse()
                except curses.error:
                    continue
                # mouse is (id, x, y, z, bstate)
                if mouse[4] == curses.BUTTON1_RELEASED:
                    # return a tuple of the mouse coordinates
                    #          row     col
                    return (mouse[2], mouse[1])
                # mouse action not recognised
                await asyncio.sleep(0)
                continue
            return key


class TooSmall(ParentScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)
        self.stdscr.clear()
        curses.flushinp()

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



class MessagesScreen(ParentScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)
        self.stdscr.clear()
        curses.flushinp()

        self.showing_disconnected = False

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Messages", curses.A_BOLD)

        # messages window (8 lines, full row - 4, starting at 4,3)
        self.messwin = self.stdscr.subwin(8, self.maxcols-4, 4, 3)

        # info window 6 lines, width 70
        self.infowin = self.stdscr.subwin(6, 70, self.maxrows-8, self.maxcols//2 - 35)
        self.infowin.addstr(0, 0, "Once connected, choose 'Devices' and press Enter. Then use")
        self.infowin.addstr(1, 0, "mouse or Tab/Shift-Tab to move between fields, Enter to select,")
        self.infowin.addstr(2, 0, "and Arrow/Page keys to show further fields where necessary.")
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
            self.showing_disconnected = False
            return
        if self.showing_disconnected:
            # already showing a disconnected status
            return
        # showing_disconnected is false, but the client is disconnected
        # so update buttons and titlewin, and set flag True, so the update
        # does not keep repeating
        self.showing_disconnected = True
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
            self.showing_disconnected = False
            self.titlewin.addstr(2, 0, "Connected    ")
            self.devices_btn.focus = True
            self.quit_btn.focus = False
        else:
            self.showing_disconnected = True
            self.titlewin.addstr(2, 0, "Not Connected")
            self.devices_btn.focus = False
            self.quit_btn.focus = True

        # draw messages
        self.messwin.clear()
        messages = self.client.messages
        lastmessagenumber = len(messages) - 1
        mlist = reversed([ widgets.localtimestring(t) + "  " + m for t,m in messages ])
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
        mlist = reversed([ widgets.localtimestring(t) + "  " + m for t,m in messages ])
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


    async def disableBLOBs(self):
        self.control.blobenabled = False
        await self.client.report("Warning! BLOBs disabled")
        await self.control.send_disableBLOB()
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
                                await self.disableBLOBs()
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
                            await self.disableBLOBs()
                            break
                        else:
                            return value


class EnableBLOBsScreen(ParentScreen):

    def __init__(self, stdscr, control):
        super().__init__(stdscr, control)
        self.stdscr.clear()
        curses.flushinp()


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
        self.path_txt = widgets.Text(stdscr, self.pathwin, self._newpath, 8, 0, txtlen=self.maxcols-8)

        self.submit_btn = widgets.Button(self.pathwin, "Submit", 10, self.maxcols//2 - 3, onclick="Submit")

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 15, onclick="Devices")
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 5, onclick="Messages")
        self.messages_btn.focus = True
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 6, onclick="Quit")

        # as self.messages_btn.focus is True, no editable field can have focus at this moment
        # so ensure the cursor is off
        curses.curs_set(0)

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


    async def submit(self):
        self._newpath = self.path_txt.text.strip()
        blobfolder = None
        if self._newpath:
            try:
                blobfolder = pathlib.Path(self._newpath).expanduser().resolve()
            except Exception:
                self.control.blobenabled = False
                await self.control.send_disableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
                await self.client.report("Warning! Unable to parse BLOB folder")
                self.submit_btn.focus = False
                self.messages_btn.focus = True
                return
            if blobfolder.is_dir():
                self.control.blobfolder = blobfolder
                self._newpath = str(blobfolder)
                self.path_txt.text = self._newpath
                self.path_txt.draw()
                self.control.blobenabled = True
                await self.control.send_enableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are enabled  ", curses.A_BOLD)
                await self.client.report("BLOB folder is set")
            else:
                self.control.blobenabled = False
                await self.control.send_disableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
                await self.client.report("Warning! BLOB folder is not a directory")
        else:
            self.control.blobenabled = False
            self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
            await self.client.report("Warning! BLOB folder is invalid")
            await self.control.send_disableBLOB()
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
                                await self.submit()
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
                    await self.submit()

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
        self.path_txt.new_texteditor()

        while not self.control.stop:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key
            if isinstance(key, tuple):
                if key in self.path_txt:
                    continue
                return key
            if key == 10:
                return 9
            # key is to be inserted into the editable field, and self._newpath updated
            value = self.path_txt.gettext(key)
            self._newpath = value.strip()
            self.path_txt.draw()
            self.pathwin.noutrefresh()
            self.path_txt.movecurs()
            curses.doupdate()
