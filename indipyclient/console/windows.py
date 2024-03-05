
import asyncio, curses, sys, os, pathlib, time, textwrap

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise




from . import widgets

from .. import events



class ParentScreen:

    def __init__(self, stdscr, consoleclient):
        self.stdscr = stdscr
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.consoleclient = consoleclient
        self.client = consoleclient.client
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



class ConsoleClientScreen(ParentScreen):

    "Parent to windows which are set in self.consoleclient.screen"

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)
        self.stdscr.clear()

    async def keyinput(self):
        """Waits for a key press,
           if self.consoleclient.screen is not self, returns 'Stop'
           if self.consoleclient.stop is True, returns 'Stop',
           if screen has been resized, returns 'Resize',
           if self._close has been given a value, returns that value
           Otherwise returns the key pressed."""
        while self.consoleclient.screen is self:
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
        try:
            self.stdscr.nodelay(True)
            while True:
                key = await self.keyinput()
                if key in ("Resize", "Stop"):
                    return key
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


class MessagesScreen(ConsoleClientScreen):

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)

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
        self.infowin.addstr(5, 5, "Enable/Disable BLOB's:")

        self.enable_btn = widgets.Button(self.infowin, "Enabled", 5, 30, onclick="EnableBLOBs")
        self.disable_btn = widgets.Button(self.infowin, "Disabled", 5, 40, onclick="DisableBLOBs")
        if self.consoleclient.blobenabled:
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
        return self.consoleclient.connected

    def showunconnected(self):
        "Called by consoleclient on disconnection"
        if self.consoleclient.connected:
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

        if self.consoleclient.blobenabled:
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
            displaytext = textwrap.shorten(message, width=self.maxcols-10, placeholder="...")
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
            displaytext = textwrap.shorten(message, width=self.maxcols-10, placeholder="...")
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
        self.consoleclient.blobenabled = False
        await self.client.report("Warning! BLOBs disabled")
        self.consoleclient.send_disableBLOB()
        self.enable_btn.bold = False
        self.disable_btn.bold = True
        self.enable_btn.draw()
        self.disable_btn.draw()
        self.infowin.noutrefresh()
        curses.doupdate()


    async def inputs(self):
        "Gets inputs from the screen"
        try:
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

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


class EnableBLOBsScreen(ConsoleClientScreen):

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)

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

        if self.consoleclient.blobfolder is None:
            self._newpath = ''
        else:
            self._newpath = str(self.consoleclient.blobfolder)

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

        if self.consoleclient.blobenabled:
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
        self._newpath = self.path_txt.text
        if self._newpath:
            try:
                blobfolder = pathlib.Path(self._newpath).expanduser().resolve()
            except Exception:
                self.consoleclient.blobenabled = False
                self.consoleclient.send_disableBLOB()
                self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
                await self.client.report("Warning! BLOB folder is invalid")
            else:
                if blobfolder.is_dir():
                    self.consoleclient.blobfolder = blobfolder
                    self._newpath = str(blobfolder)
                    self.path_txt.text = self._newpath
                    self.path_txt.draw()
                    self.consoleclient.blobenabled = True
                    self.consoleclient.send_enableBLOB()
                    self.pathwin.addstr(0, 0, "BLOBs are enabled  ", curses.A_BOLD)
                    await self.client.report("BLOB folder is set")
                else:
                    self.consoleclient.blobenabled = False
                    self.consoleclient.send_disableBLOB()
                    self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
                    await self.client.report("Warning! BLOB folder is invalid")
        else:
            self.consoleclient.blobenabled = False
            self.pathwin.addstr(0, 0, "BLOBs are disabled ", curses.A_BOLD)
            await self.client.report("Warning! BLOB folder is invalid")
            self.consoleclient.send_disableBLOB()
        self.submit_btn.focus = False
        self.messages_btn.focus = True


    async def inputs(self):
        "Gets inputs from the screen"

        try:
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

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


    async def textinput(self):
        "Input text, set it into self._newvalue"
        # set cursor visible
        curses.curs_set(1)
        editstring = self.path_txt.editstring(self.stdscr)

        while not self.consoleclient.stop:
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

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)

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
        try:
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

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


class ChooseVectorScreen(ConsoleClientScreen):

    def __init__(self, stdscr, consoleclient, devicename):
        super().__init__(stdscr, consoleclient)

        # devicename is the actual devicename given by the device (not set to lower case)
        self.devicename = devicename
        # start with vectorname None, a vector to view will be chosen by this screen
        self.vectorname = None

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)                  # row 0
        self.titlewin.addstr(0, 0, "Device: " + self.devicename, curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)                   # row 2
        self.lastmessage = ""

        # list areas of the screen, one of these areas has the current 'focus'
        # Groups being the horizontal line of group names associated with a device
        # Vectors being the area showing the vectors associated with a device and group
        # and Devices, Messages and Quit are the bottom buttons
        self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")

        # groups list
        try:
            self.groupwin = GroupWin(self.stdscr, self.consoleclient, self.devicename)         # row 4
            # this creates its own window (1 line, full row, starting at 4,0)

            # window showing the vectors of the active group
            self.vectorswin = VectorListWin(self.stdscr, self.consoleclient, self.devicename)    # topmore row 6
        except Exception:                                                                        # botmore row self.maxrows - 4 row 20
            traceback.print_exc(file=sys.stderr)
            raise

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
        "Displays device"

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
        self.vectorswin.vecwinrefresh()
        self.buttwin.noutrefresh()

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
        self.vectorswin.vecwinrefresh()
        curses.doupdate()


    async def inputs(self):
        "Gets inputs from the screen"

        try:
            self.stdscr.nodelay(True)
            while True:
                key = await self.keyinput()
                if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                    return key

                if self.focus == "Groups":
                    # focus has been given to the GroupWin
                    result = self.groupwin.setkey(key)
                    if result == "NewGroup":
                        # must update the screen with a new group
                        self.show()
                        continue
                    if not result:
                        continue
                    key = result

                elif self.focus == "Vectors":
                    # focus has been given to VectorListWin
                    result = self.vectorswin.setkey(key)
                    if not result:
                        continue
                    if result in self.device:
                        # result is a vector name, check if it is enabled
                        if self.device[result].enable:
                            # a vector has been chosen, get the vectorname chosen
                            self.vectorname = result
                            return "Vectors"
                        else:
                            continue
                    key = result

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
                        newfocus = "Groups"
                    else:
                        indx = self.screenparts.index(self.focus)
                        newfocus = self.screenparts[indx+1]
                elif key in (353, 260, 339, 259):
                    # go to previous button
                    if self.focus == "Groups":
                        newfocus = "Quit"
                    else:
                        indx = self.screenparts.index(self.focus)
                        newfocus = self.screenparts[indx-1]
                else:
                    # key not recognised
                    continue
                if self.focus == "Vectors":
                    self.vectorswin.defocus()
                    self.vectorswin.draw(self.devicename, self.groupwin.active, change=True)
                elif self.focus == "Groups":
                    self.groupwin.defocus()
                elif self.focus == "Devices":
                    self.devices_btn.focus = False
                elif self.focus == "Messages":
                    self.messages_btn.focus = False
                elif self.focus == "Quit":
                    self.quit_btn.focus = False
                if newfocus == "Vectors":
                    if self.focus == "Groups":
                        self.vectorswin.set_top_focus()
                    else:
                        self.vectorswin.set_bot_focus()
                    self.vectorswin.draw(self.devicename, self.groupwin.active, change=True)
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
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()

                self.vectorswin.vecwinrefresh()
                self.groupwin.noutrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


# This class GroupBtns defines the position of group buttons on the row

class GroupBtns:

    def __init__(self, device, maxcols):
        "get the groups this device contains, use a set to avoid duplicates"
        self.maxcols = maxcols

        groupset = {vector.group for vector in device.values() if vector.enable}
        if not groupset:
            groupset = set("default")

        # self.groups is a list of group names
        self.groups = sorted(list(groupset))

        # self.positions is a list of tuples (col, btnlen)
        self.positions = []

        # If there is only one group, text is displayed rather than buttons
        if len(self.groups) == 1:
            self.text = textwrap.shorten(f" Groups : {self.groups[0]}", width=self.maxcols-6, placeholder="...")
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

    def maxwidth(self):
        "calculate width of buttons"
        # =<[prev]=[btn]=[btn]=....               =[next]>=
        #     9                                      8
        btnspace = self.maxcols - 9 - 8                           # 80-9-8 is 63
        # assume three buttons
        maxbtn = btnspace//3 - 3  # -3 for brackets and space     # 21-3 = 18
        maxtext = max(len(grp) for grp in self.groups)
        # choose whichever is smaller
        if maxbtn >= maxtext:
            width = maxtext + 2     # 2 for the [] brackets
        else:
            width = maxbtn + 2
        return width



# The following two windows, GroupWin and VectorListWin are sub windows of ChooseVectorScreen

class GroupWin(ParentScreen):

    def __init__(self, stdscr, consoleclient, devicename, active=None):
        super().__init__(stdscr, consoleclient)

        # window (1 line, full row, starting at 4,0)
        self.window = self.stdscr.subwin(1, self.maxcols, 4, 0)   # this window on row 4

        self.devicename = devicename
        device = self.client[self.devicename]

        # active is the name of the group currently being shown
        self.active = active

        # grps is a class that calculates button positions along the row
        self.grps = GroupBtns(device, self.maxcols)

        # group names to buttons
        self.grpbuttons = {}             # group names are original case

        # this is set to the group name in focus, if any
        self.focus = None
        self.rightfocus = False  # True if rightmore has focus
        self.leftfocus = False   # True if leftmore has focus

        self.groupcols = {}       # dictionary of groupname to column number

        self.leftidx = 0          # index of leftmost button

        # the horizontal display of group buttons may not hold all the buttons
        # give the index of self.groups from and to
        self.fromgroup = 0
        self.togroup = 0
        self.nextcol = 0
        self.nextfocus = False
        self.prevfocus = False


    def groups(self):
        "self.groups() returns a list of group names"
        return self.grps.groups

    def noutrefresh(self):
        "Call noutrefresh on group window"
        self.window.noutrefresh()

    def defocus(self):
        "Remove focus from all buttons, and re-draw the button which had focus"
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

        # grps is a class that calculates button positions along the row
        self.grps = GroupBtns(device, self.maxcols)

        # clear the line
        self.window.clear()

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
            # no buttons
            return
        elif len(groups) == 2:
            self.window.addstr(0, 0, self.grps.text)
            self.rightfocus = False
            self.leftfocus = False

        # create buttons

        self.rightmore_btn = widgets.Button(self.window, "next", 0, self.maxcols-8, onclick="Next")
        self.rightmore_btn.show = False

        self.leftmore_btn = widgets.Button(self.window, "prev", 0, 2, onclick="Previous")
        self.leftmore_btn.show = False


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


    def has_focus(self):
        "Returns True if any button has focus"
        if self.focus or self.leftfocus or self.rightfocus:
            return True
        else:
            return False


    def setkey(self, key):

        if not self.grpbuttons:
            return key

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
                self.rightmore_btn.draw()
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
                self.leftmore_btn.draw()
                self.window.noutrefresh()
                return 258   # treat as 258 down arrow key

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
                    return key #258   # treat as 258 down arrow key

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


    def __init__(self, stdscr, consoleclient, devicename):
        super().__init__(stdscr, consoleclient)


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


        self.displaylines = self.maxrows - 5 - 8         ######### delete

        # self.focus will be the name of a vector in focus
        self.focus = None

        # vectornames to vectors in the current group
        self.vectors = {}
        # vectornames to buttons
        self.vecbuttons = {}             # vectornames are original case

        # vector names to vector states of vectors in the current group
        self.vectorstates = {}


    def vecwinrefresh(self):
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
        if self.topmore_btn.show:
            self.topmore_btn.focus = True
        else:
            self.focus = names[0]


    def set_bot_focus(self):
        names = list(self.vecbuttons.keys())
        if self.botmore_btn.show:
            self.botmore_btn.focus = True
        else:
            self.focus = names[-1]


    def draw(self, devicename, groupname, change=False):

        # change is a flag to indicate the window needs to be redrawn

        if (groupname != self.groupname) or (devicename != self.devicename):
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
            # shorten the name and set it as a button
            nm = vectorname[:17] + "..." if len(vectorname) > 20 else vectorname
            self.vecbuttons[vectorname] = widgets.Button(self.window, nm, linenumber, 1, onclick=vectorname.lower())
            label = self.vectors[vectorname].label
            lb = label[:27] + "..." if len(label) > 30 else label
            self.window.addstr(linenumber, 30, lb)  # the shortenned label
            lowerstate = self.vectorstates[vectorname].lower()
            if lowerstate == "idle":
                self.window.addstr(linenumber, self.maxcols - 20, "  Idle  ", self.consoleclient.color(lowerstate))
            elif lowerstate == "ok":
                self.window.addstr(linenumber, self.maxcols - 20, "  OK    ", self.consoleclient.color(lowerstate))
            elif lowerstate == "busy":
                self.window.addstr(linenumber, self.maxcols - 20, "  Busy  ", self.consoleclient.color(lowerstate))
            elif lowerstate == "alert":
                self.window.addstr(linenumber, self.maxcols - 20, "  Alert ", self.consoleclient.color(lowerstate))
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
        "Update when topmore button pressed"
        if not self.topmore_btn.focus:
            return
        if not self.topindex:    # self.topindex cannot be zero
            return

        # vectors is a dictionary of vectornames to vectors
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
        self.vecwinrefresh()


    def botmorechosen(self):
        "Update when botmore button pressed"
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

        if new_bot_idx > lastidx:
            # no point incrementing topindex as it does not display any new vector
            self.botmore_btn.show = False
            self.focus = names[-1]        # set focus to name of last device
        else:
            # so increment topindex
            self.topindex = new_top_idx
            if new_bot_idx == lastidx:
                # cannot increment further
                self.botmore_btn.show = False
                self.focus = names[-1]

        self.draw(self.devicename, self.groupname, change=True)
        self.vecwinrefresh()


    def setkey(self, key):

        names = list(self.vectors.keys())
        lastidx = len(names)-1            # index of last vector

        displayedbtns = list(self.vecbuttons.values())
        displayednames = list(self.vecbuttons.keys())
        bottomidx = self.botindex()       # index of last displayed vector

        if key == 10:
            if self.topmore_btn.focus:
                self.topmorechosen()
                curses.doupdate()
            elif self.botmore_btn.focus:
                self.botmorechosen()
                curses.doupdate()
            elif self.focus:
                return self.focus.lower()

        elif key in (32, 9, 261, 338, 258):
            # go to the next
            if self.botmore_btn.focus:
                self.focus = None
                self.draw(self.devicename, self.groupname, change=True)
                self.vecwinrefresh()
                curses.doupdate()
                return key
            elif self.topmore_btn.focus:
                self.topmore_btn.focus = False
                self.focus = displayednames[0]
            else:
                # one of the devices has focus
                try:
                    indx = names.index(self.focus)
                except ValueError:
                    return
                # indx here is the index on the list of all devices, not just those displayed
                if indx == lastidx:
                    # very last device, the botmore_btn should not be shown
                    self.focus = None
                    self.draw(self.devicename, self.groupname, change=True)
                    self.vecwinrefresh()
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
                self.vecwinrefresh()
                curses.doupdate()
                return key
            elif self.focus == names[0]:
                self.focus = None
                self.draw(self.devicename, self.groupname, change=True)
                self.vecwinrefresh()
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
        self.vecwinrefresh()
        curses.doupdate()



class VectorScreen(ConsoleClientScreen):

    "This displays the chosen vector and its members"


    def __init__(self, stdscr, consoleclient, devicename, vectorname):
        super().__init__(stdscr, consoleclient)

        self.devicename = devicename
        self.vectorname = vectorname

        self.device = self.client[self.devicename]
        self.vector = self.device[self.vectorname]

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 1, "Device: " + self.devicename)
        self.titlewin.addstr(1, 1, "Vector: " + self.vectorname + " : Group: " + self.vector.group)
        self.titlewin.addstr(2, 1, self.vector.label, curses.A_BOLD)

        # messages window (1 line, full row, starting at 3,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 3, 0)

        # timestamp and state window (1 line, full row, starting at 4,0)
        self.tstatewin = self.stdscr.subwin(1, self.maxcols, 4, 0)

        try:
            # window showing the members of the vector
            self.members = MembersWin(self.stdscr, self.consoleclient, self.vector, self.tstatewin)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # bottom buttons, [Vectors] [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.vectors_btn = widgets.Button(self.buttwin, "Vectors", 0, self.maxcols//2 - 20)
        self.vectors_btn.focus = True

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10)
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 11)

    def close(self, value):
        "Sets _close, which is returned by the input co-routine"
        self._close = value
        self.members.close(value)


    def show(self):
        "Displays the window"

        if self.vector.message:
            widgets.drawmessage(self.messwin, self.vector.message, maxcols=self.maxcols)

        widgets.draw_timestamp_state(self.consoleclient, self.tstatewin, self.vector)

        # Draw the members widgets
        self.members.draw()

        # draw the bottom buttons
        self.vectors_btn.draw()
        self.devices_btn.draw()
        self.messages_btn.draw()
        self.quit_btn.draw()

        #  and refresh
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.tstatewin.noutrefresh()
        self.members.noutrefresh()
        self.buttwin.noutrefresh()

        curses.doupdate()
        return

    def update(self, event):
        "An event affecting this vector has occurred, re-draw the screen"

        self.titlewin.clear()
        self.titlewin.addstr(0, 1, "Device: " + self.devicename)
        self.titlewin.addstr(1, 1, "Vector: " + self.vectorname + " : Group: " + self.vector.group)
        self.titlewin.addstr(2, 1, self.vector.label, curses.A_BOLD)

        self.messwin.clear()
        self.tstatewin.clear()
        self.buttwin.clear()
        # self.members does not need a clear() call, as its window is cleared in its call method

        self.show()
        # calling self.show in turn calls button and members draw and noutrefresh methods


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
                self.members.set_topfocus()
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
                self.members.set_botfocus()
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
            while True:

                if self.members.focus:
                    # focus has been given to one of the MembersWin windows which monitors its own inputs
                    result = await self.members.input()
                    if result in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                        return result
                    if result == "submitted":
                        self.vector.state = 'Busy'
                        # The vector has been submitted, draw vector state which is now busy
                        widgets.draw_timestamp_state(self.consoleclient, self.tstatewin, self.vector)
                        self.tstatewin.noutrefresh()
                        self.vectors_btn.focus = True
                        self.buttwin.clear()
                        self.vectors_btn.draw()
                        self.devices_btn.draw()
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                        curses.doupdate()
                    elif result == "next":   # go to next button
                        self.members.set_nofocus() # removes focus and calls draw and noutrefresh on memberswin
                        self.vectors_btn.focus = True
                        self.buttwin.clear()
                        self.vectors_btn.draw()
                        self.devices_btn.draw()
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                        curses.doupdate()
                    elif result == "previous":   # go to prev button
                        self.members.set_nofocus() # removes focus and calls draw and noutrefresh on memberswin
                        self.quit_btn.focus = True
                        self.buttwin.clear()
                        self.vectors_btn.draw()
                        self.devices_btn.draw()
                        self.messages_btn.draw()
                        self.quit_btn.draw()
                        self.buttwin.noutrefresh()
                        curses.doupdate()
                else:
                    key = await self.keyinput()
                    if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                        return key

                    # check this vector has not been deleted
                    if not self.vector.enable:
                        return "Vectors"

                    if self.vectors_btn.focus or self.devices_btn.focus or self.messages_btn.focus or self.quit_btn.focus:
                        result = self.check_bottom_btn(key)
                        if result:
                            return result

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


# MembersWin is created within VectorScreen


class MembersWin(ParentScreen):

    "Used to display the vector members"


    def __init__(self, stdscr, consoleclient, vector, tstatewin):
        super().__init__(stdscr, consoleclient)

        self.vector = vector
        self.vectorname = vector.name
        self.tstatewin = tstatewin

        self.topline = 0

        # dictionary of member name to member this vector owns
        members_dict = self.vector.members()

        # list of member names in alphabetic order
        self.membernames = sorted(members_dict.keys())

        # number of lines in a pad, assume four lines per member, with a minimum of 50
        self.padlines = max(50, len(self.membernames)*4)

        self.window = curses.newpad(self.padlines, self.maxcols)

        # create the member widgets
        try:
            self.memberwidgets = []
            for name in self.membernames:
                if self.vector.vectortype == "SwitchVector":
                    self.memberwidgets.append(widgets.SwitchMember(self.stdscr, self.consoleclient, self.window, self, self.vector, name))
                elif self.vector.vectortype == "LightVector":
                    self.memberwidgets.append(widgets.LightMember(self.stdscr, self.consoleclient, self.window, self, self.vector, name))
                elif self.vector.vectortype == "NumberVector":
                    self.memberwidgets.append(widgets.NumberMember(self.stdscr, self.consoleclient, self.window, self, self.vector, name))
                elif self.vector.vectortype == "TextVector":
                    self.memberwidgets.append(widgets.TextMember(self.stdscr, self.consoleclient, self.window, self, self.vector, name))
                elif self.vector.vectortype == "BLOBVector":
                    self.memberwidgets.append(widgets.BLOBMember(self.stdscr, self.consoleclient, self.window, self, self.vector, name))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # this is True, if this widget is in focus
        self.focus = False

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols-1, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.topmore_btn.show = False
        self.topmore_btn.focus = False

        # window.subwin(nlines, ncols, begin_y, begin_x)
        # Return a sub-window, whose upper-left corner is at (begin_y, begin_x), and whose width/height is ncols/nlines.


        # botmorewin = 1 line height, columns just over half of self.maxrows, to give room on the right for submitwin
        # starting at y = columns - 11, x = 0)
        botmorewincols = self.maxcols//2 + 4
        self.botmorewin = self.stdscr.subwin(1, botmorewincols, self.maxrows - 3, 0)
        if self.vector.perm == 'ro':
            self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, botmorewincols-11)
        else:
            self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, botmorewincols-20)
        self.botmore_btn.show = False
        self.botmore_btn.focus = False

        # submitwin and submit_btn, located to the right of botmorewin
        # submitwin = 1 line height, starting at y=self.maxrows - 3, x = botmorewincols + 1
        # width = self.maxcols -x - 2
        self.submitwin = self.stdscr.subwin(1, self.maxcols - botmorewincols - 3, self.maxrows - 3, botmorewincols + 1)
        self.submit_btn = widgets.Button(self.submitwin, "Submit", 0, 0)
        self.cancel_btn = widgets.Button(self.submitwin, "Cancel", 0, 12)
        if (self.vector.perm == 'ro') or (self.vector.vectortype == "BLOBVector"):
            self.submit_btn.show = False
            self.cancel_btn.show = False
        else:
            self.submit_btn.show = True
            self.cancel_btn.show = True
        self.submit_btn.focus = False
        self.cancel_btn.focus = False

        # top more btn on 7th line ( coords 0 to 6 )
        # bot more btn on line (self.maxrows - 3) + 1
        # displaylines = (self.maxrows - 2) - 7  - 1

        self.displaylines = self.maxrows - 10

    def close(self, value):
        "Sets _close to a value, which stops the input co-routine"
        self._close = value
        for widget in self.memberwidgets:
            widget.close(value)

    def set_nofocus(self):
        self.focus = False
        for widget in self.memberwidgets:
            if widget.focus:
                widget.focus = False
                widget.draw()
                self.noutrefresh()
                return
        self.topmore_btn.focus = False
        self.botmore_btn.focus = False
        self.submit_btn.focus = False
        self.cancel_btn.focus = False
        self.topmore_btn.draw()
        self.botmore_btn.draw()
        self.submit_btn.draw()
        self.cancel_btn.draw()
        self.topmorewin.noutrefresh()
        self.botmorewin.noutrefresh()
        self.submitwin.noutrefresh()

    def set_topfocus(self):
        self.focus = True
        self.botmore_btn.focus = False
        self.botmore_btn.draw()
        self.botmorewin.noutrefresh()
        self.submit_btn.focus = False
        self.cancel_btn.focus = False
        self.submit_btn.draw()
        self.cancel_btn.draw()
        self.submitwin.noutrefresh()


        if self.topline:
            # self.topline is not zero, so topmore button must be shown
            # and with focus set
            self.topmore_btn.show = True
            self.topmore_btn.focus = True
            self.topmore_btn.draw()
            self.topmorewin.noutrefresh()
        else:
            # self.topline is zero, so top member widget must be shown
            # and with focus set
            widget = self.memberwidgets[0]
            widget.focus = True
            self.draw()
            self.noutrefresh()


    def set_botfocus(self):
        self.focus = True
        self.topmore_btn.focus = False
        self.topmore_btn.draw()
        self.topmorewin.noutrefresh()

        if self.cancel_btn.show:
            self.cancel_btn.focus = True
            self.cancel_btn.draw()
            self.submitwin.noutrefresh()
            return

        # no submit/cancel button, so either bottom widget is set in focus
        # or bottom more button is set in focus

        botindex = self.widgetindex_bottom_displayed()
        if botindex == len(self.memberwidgets)-1:
            # last widget is displayed
            # set focus on bottom member widget
            widget = self.memberwidgets[botindex]
            widget.focus = True
            self.draw()
            self.noutrefresh()
        else:
            self.botmore_btn.show = True
            self.botmore_btn.focus = True
            self.botmore_btn.draw()
            self.botmorewin.noutrefresh()


    def draw(self):
        self.window.clear()

        # self.memberwidgets is the list of widgets
        # get the number of lines the widgets take
        lines = 0
        for widget in self.memberwidgets:
            lines += widget.linecount

        # pad may need increasing if extra members have been added
        padlines = max(self.padlines, lines)
        if padlines != self.padlines:
            self.padlines = padlines
            self.window.resize(self.padlines, self.maxcols)
            self.topline = 0

        # draw the member widgets
        try:
            line = 0
            for memberwidget in self.memberwidgets:
                memberwidget.draw(line)
                line = memberwidget.endline + 1
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # Is the top of the pad being displayed?
        if self.topline:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
        self.topmore_btn.draw()

        # Is the bottom widget being displayed?
        botindex = self.widgetindex_bottom_displayed()
        if botindex == len(self.memberwidgets) -1:
            self.botmore_btn.show = False
        else:
            self.botmore_btn.show = True
        self.botmore_btn.draw()

        self.submit_btn.draw()
        self.cancel_btn.draw()


    def noutrefresh(self):
        "Refresh this objects entire window, including widgets and top and bottom buttons"
        self.topmorewin.noutrefresh()
        self.widgetsrefresh()
        self.botmorewin.noutrefresh()
        self.submitwin.noutrefresh()


    def widgetsrefresh(self):
        "Refreshes the pad window holding the widgets"
        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.topline, 0, 7, 1, self.maxrows - 4, self.maxcols-2)
                  # pad row, pad col, win start row, win start col, win end row, win end col
        self.window.overwrite(self.stdscr, *coords)
        self.window.noutrefresh(*coords)


    def widgetindex_in_focus(self):
        "Returns the memberwidget index which has focus, or None"
        for index,widget in enumerate(self.memberwidgets):
            if widget.focus:
                return index


    def widgetindex_bottom_displayed(self):
        "Return the memberwidget index being displayed at bottom of window"
        for index,widget in enumerate(self.memberwidgets):
            if widget.endline == self.topline + self.displaylines - 1:
                return index
            if widget.endline > self.topline + self.displaylines - 1:
                return index-1
        else:
            return len(self.memberwidgets) - 1


    def widgetindex_top_displayed(self):
        "Return the memberwidget index being displayed at top of window"
        for index,widget in enumerate(self.memberwidgets):
            if widget.startline >= self.topline:
                return index

# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow


    async def input(self):
        "This window is in focus, and monitors inputs"
        self.stdscr.nodelay(True)
        try:
            while True:

                if self.vector.perm == "ro":
                    # no widget is writeable
                    key = await self.keyinput()
                else:
                    # check if a widget is in focus
                    for widget in self.memberwidgets:
                        if widget.focus:
                            # a widget is in focus, and writeable the widget monitors its own input
                            key = await widget.input()
                            break
                    else:
                        # no widget is in focus
                        key = await self.keyinput()


                if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                    return key
                if not self.vector.enable:
                    return "Vectors"

                if key == 10:
                    if self.topmore_btn.focus:
                        # scroll the window down
                        self.topline -= 1
                        if not self.topline:
                            # if topline is zero, topmore button should not be shown
                            self.topmore_btn.show = False
                            self.topmore_btn.draw()
                            self.topmorewin.noutrefresh()
                            # but the top widget should get focus
                            topwidget = self.memberwidgets[0]
                            topwidget.focus = True
                            topwidget.draw()
                        self.noutrefresh()
                        curses.doupdate()
                        continue
                    elif self.botmore_btn.focus:
                        # scroll the window up
                        self.topline += 1
                        botindex = self.widgetindex_bottom_displayed()
                        if botindex == len(self.memberwidgets)-1:
                            # bottom widget displayed, so more button should be hidden
                            self.botmore_btn.show = False
                            self.botmore_btn.draw()
                            self.botmorewin.noutrefresh()
                            # and the bottom widget should get focus
                            botwidget = self.memberwidgets[botindex]
                            botwidget.focus = True
                            botwidget.draw()
                        self.noutrefresh()
                        curses.doupdate()
                        continue
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
                            continue
                    elif self.cancel_btn.focus:
                        # Cancel chosen, reset all widgets, removing any value changes
                        for memberwidget in self.memberwidgets:
                            memberwidget.reset()
                        self.widgetsrefresh()
                        curses.doupdate()
                        continue

                if key in (10, 32, 9, 261, 338, 258):   # go to next button
                    if self.cancel_btn.focus:
                        return "next"
                    if self.submit_btn.focus:
                        self.submit_btn.focus = False
                        self.cancel_btn.focus = True
                        self.submit_btn.draw()
                        self.cancel_btn.draw()
                        self.submitwin.noutrefresh()
                        curses.doupdate()
                        continue
                    if self.botmore_btn.focus:
                        if self.submit_btn.show:
                            self.botmore_btn.focus = False
                            self.botmore_btn.draw()
                            self.submit_btn.focus = True
                            self.submit_btn.draw()
                            self.botmorewin.noutrefresh()
                            self.submitwin.noutrefresh()
                            curses.doupdate()
                            continue
                        else:
                            return "next"
                    # get the top widget being displayed
                    topwidgetindex = self.widgetindex_top_displayed()
                    if self.topmore_btn.focus:
                        self.topmore_btn.focus = False
                        self.topmore_btn.draw()
                        nextwidget = self.memberwidgets[topwidgetindex]
                        nextwidget.focus = True
                        nextwidget.draw()
                        self.noutrefresh()
                        curses.doupdate()
                        continue
                    elif (widgetindex := self.widgetindex_in_focus()) is not None:
                        widget = self.memberwidgets[widgetindex]
                        # widget is the widget currently in focus
                        if widgetindex == len(self.memberwidgets) -1:
                            # last widget,
                            widget.focus = False
                            widget.draw()
                            if self.submit_btn.show:
                                self.submit_btn.focus = True
                                self.submit_btn.draw()
                                self.noutrefresh()
                                curses.doupdate()
                                continue
                            else:
                                # go on to the vector button by returning from this members window
                                self.noutrefresh()
                                return "next"
                        if self.memberwidgets[widgetindex+1].endline > self.topline + self.displaylines - 1:
                            # next widget is still not displayed
                            if key == 9:
                                # tab key pressed, go to bottom more button
                                widget.focus = False
                                widget.draw()
                                self.botmore_btn.focus = True
                                self.botmore_btn.draw()
                                self.botmorewin.noutrefresh()
                            else:
                                # page/arrow pressed, scroll the window up
                                self.topline += 1
                                if not self.topmore_btn.show:
                                    # top more button should be displayed
                                    self.topmore_btn.show = True
                                    self.topmore_btn.draw()
                                    self.topmorewin.noutrefresh()
                                if self.botmore_btn.show:
                                    botindex = self.widgetindex_bottom_displayed()
                                    if botindex == len(self.memberwidgets)-1:
                                        # bottom more button should not be displayed
                                        self.botmore_btn.show = False
                                        self.botmore_btn.draw()
                                        self.botmorewin.noutrefresh()
                        else:
                            # set next widget in focus
                            widget.focus = False
                            widget.draw()
                            nextwidget = self.memberwidgets[widgetindex+1]
                            nextwidget.focus = True
                            nextwidget.draw()
                            # if nextwidget is the last widget, then do not show self.botmore_btn
                            if widgetindex+1 == len(self.memberwidgets)-1:
                                self.botmore_btn.show = False
                                self.botmorewin.clear()
                        self.noutrefresh()
                        curses.doupdate()
                        continue

                if key in (353, 260, 339, 259):   # go to prev button
                    if self.topmore_btn.focus:
                        return key
                    if self.cancel_btn.focus:
                        self.cancel_btn.focus = False
                        self.submit_btn.focus = True
                        self.cancel_btn.draw()
                        self.submit_btn.draw()
                        self.submitwin.noutrefresh()
                        curses.doupdate()
                        continue
                    # get the bottom widget being displayed
                    bottomwidgetindex = self.widgetindex_bottom_displayed()
                    if self.submit_btn.focus:
                        self.submit_btn.focus = False
                        self.submit_btn.draw()
                        self.submitwin.noutrefresh()
                        if self.botmore_btn.show:
                            self.botmore_btn.focus = True
                            self.botmore_btn.draw()
                            self.botmorewin.noutrefresh()
                            curses.doupdate()
                            continue
                        else:
                            # botmore button not shown, so go to last widget
                            prevwidget = self.memberwidgets[bottomwidgetindex]
                            prevwidget.focus = True
                            prevwidget.draw()
                            self.noutrefresh()
                            curses.doupdate()
                            continue
                    if self.botmore_btn.focus:
                        self.botmore_btn.focus = False
                        self.botmore_btn.draw()
                        prevwidget = self.memberwidgets[bottomwidgetindex]
                        prevwidget.focus = True
                        prevwidget.draw()
                        self.noutrefresh()
                        curses.doupdate()
                        continue
                    elif (widgetindex := self.widgetindex_in_focus()) is not None:
                        widget = self.memberwidgets[widgetindex]
                        if widgetindex == 0:
                            # The topmost widget is in focus, remove focus
                            widget.focus = False
                            widget.draw()
                            self.topline = 0
                            # First widget, so go on to the quit button by returning from this members window
                            self.noutrefresh()
                            return "previous"
                        if (not self.topline) and (widgetindex == 1):
                            # topline is zero, and set first widget in focus
                            widget.focus = False
                            widget.draw()
                            prevwidget = self.memberwidgets[0]
                            prevwidget.focus = True
                            prevwidget.draw()
                        elif self.memberwidgets[widgetindex-1].startline < self.topline:
                            # widget previous to current in focus widget is not fully displayed
                            if key == 353:
                                # shift tab pressed, jump to top more button
                                widget.focus = False
                                widget.draw()
                                self.topmore_btn.focus = True
                                self.topmore_btn.draw()
                                self.topmorewin.noutrefresh()
                            else:
                                # scroll the window down
                                self.topline -= 1
                                if not self.topline:
                                    # if topline is zero, topmore button should not be shown
                                    self.topmore_btn.show = False
                                    self.topmore_btn.draw()
                                    self.topmorewin.noutrefresh()
                                if not self.botmore_btn.show:
                                    botindex = self.widgetindex_bottom_displayed()
                                    if botindex != len(self.memberwidgets)-1:
                                        # bottom more button should be displayed
                                        self.botmore_btn.show = True
                                        self.botmore_btn.draw()
                                        self.botmorewin.noutrefresh()
                        else:
                            # set prev widget in focus
                            widget.focus = False
                            widget.draw()
                            prevwidget = self.memberwidgets[widgetindex-1]
                            prevwidget.focus = True
                            prevwidget.draw()
                        self.noutrefresh()
                        curses.doupdate()

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


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
    elif vector.vectortype == "BLOBVector":
        members = {}
        # members is a dictionary of membername : member value , blob size, blob format
        for member in memberwidgets:
            filepath = member.newvalue()
            blobformat = ''.join(pathlib.Path(filepath).suffixes)
            members[member.name] = (filepath, 0, blobformat)
        vector.send_newBLOBVector(members=members)
        return True
    return False
