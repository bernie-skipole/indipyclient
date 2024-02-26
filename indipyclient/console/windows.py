
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

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Devices", curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)

        # status window (1 line, full row-4, starting at 4,4)
        self.statwin = self.stdscr.subwin(1, self.maxcols-4, 4, 4)

        # topmorewin (1 line, full row, starting at 6, 0)
        self.topmorewin = self.stdscr.subwin(1, self.maxcols, 6, 0)
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="TopMore")
        self.topmore_btn.show = False

        dnumber = self.devicenumber()

        # devices window - create a pad of 40+2*devices lines, full row
        self.devwin = curses.newpad(40 + 2* dnumber, self.maxcols)

        # devices window top and bottom row numbers
        self.devwintop = 8
        # ensure bottom row is an even number at position self.maxrows - 6 or -7
        row = self.maxrows - 7
        # very large screen may produce a window bigger that the pad,
        # so reduce it to around ten times less than the pad
        if row > 30 + 2* dnumber:
            row = 30 + 2* dnumber
        self.devwinbot = row + row % 2

        # topline of pad to show
        self.topline = 0

        # botmorewin (1 line, full row, starting at self.maxrows - 4, 0)
        self.botmorewin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 4, 0)
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7, onclick="BotMore")
        self.botmore_btn.show = False

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        # this holds the messages and quit buttons
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        # self.focus will be the name of a device in focus
        self.focus = None

        # Start with the messages_btn in focus
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 10, onclick="Messages")
        self.messages_btn.focus = True

        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2, onclick="Quit")
        # devicename to button dictionary
        self.devices = {}


    def show(self):
        "Displays the screen with list of devices"

        # draw the message
        if self.client.messages:
            self.messwin.clear()
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)

        # draw status
        if not self.devicenumber():
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
        self.devwinrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()

    def defocus(self):
        if self.focus:
            btn = self.devices[self.focus]
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

        # The refresh() and noutrefresh() methods of a pad require 6 arguments
        # to specify the part of the pad to be displayed and the location on
        # the screen to be used for the display. The arguments are
        # pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol;
        # the p arguments refer to the upper left corner of the pad region to be displayed and the
        # s arguments define a clipping box on the screen within which the pad region is to be displayed.

        coords = (self.topline, 0, self.devwintop, 0, self.devwinbot, self.maxcols-1)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.devwin.overwrite(self.stdscr, *coords)

        self.topmorewin.noutrefresh()
        self.devwin.noutrefresh(*coords)
        self.botmorewin.noutrefresh()


    @property
    def botline(self):
        "Returns the bottom line of the pad to be displayed"
        return self.topline + self.devwinbot - self.devwintop

    #    self.devwintop = 8
    #    self.devwinbot = self.maxrows - 7 or - 6


    # ex1: self.topline = 0, self.maxrows = 30
    # self.devwinbot = 24
    # botline = 0 + 24 - 8 = 16

    # ex2: self.topline = 0, self.maxrows = 31
    # self.devwinbot = 24
    # botline = 0 + 24 - 8 = 16

    # ex3: topline = 0, self.maxrows = 32
    # self.devwinbot = 26
    # botline = 0 + 26 - 8 = 18

    # ex4: self.topline = 2, self.maxrows = 15
    # self.devwinbot = 8
    # botline = 2 + 8 - 8 = 2

    # ex5: self.topline = 2, self.maxrows = 16
    # self.devwinbot = 10
    # botline = 2 + 10 - 8 = 4

    # ex6: self.topline = 2, self.maxrows = 17
    # self.devwinbot = 10
    # botline = 2 + 10 - 8 = 4


    @property
    def topdevice(self):
        "Returns the index of the top device being displayed"
        return self.topline//2

    @property
    def bottomdevice(self):
        "Returns the index of the bottom device being displayed"

        idx_of_last_device = self.devicenumber() - 1

        last_displayed = self.botline//2

        if idx_of_last_device > last_displayed:
            return last_displayed
        return idx_of_last_device


    def drawdevices(self):
        "Called by self.show/update to create and draw the device buttons"
        self.topmorewin.clear()
        self.devwin.clear()
        self.botmorewin.clear()

        if not self.devicenumber():
            self.focus = None                # the devicename in focus
            self.topmore_btn.show = False
            self.botmore_btn.show = False
            self.topmore_btn.focus = False
            self.botmore_btn.focus = False
            return

        # Remove current devices
        self.devices.clear()

        colnumber = self.maxcols//2 - 6
        enabledclients = {devicename:device for devicename,device in self.client.items() if device.enable}
        for linenumber, devicename in enumerate(enabledclients):
            self.devices[devicename.lower()] = widgets.Button(self.devwin, devicename, linenumber*2, colnumber, onclick=devicename.lower())

        # self.devices is a devicename to button dictionary

        # Note: initially all device buttons are created with focus False
        # self.focus has the name of the device which should be in focus
        # so if it is set, set the appropriate button focus

        if self.focus:
            if self.focus in self.devices:
                self.devices[self.focus].focus = True
            else:
                self.focus = None

        # if self.topdevice is not zero, then draw top more button
        if self.topdevice:
            self.topmore_btn.show = True
        else:
            self.topmore_btn.show = False
            self.topmore_btn.focus = False
        self.topmore_btn.draw()

        # draw devices buttons
        for devbutton in self.devices.values():
            devbutton.draw()

        # self.bottomdevice is the index of the bottom device being displayed
        if self.bottomdevice < len(self.devices) -1:
            self.botmore_btn.show = True
        else:
            self.botmore_btn.show = False
            self.botmore_btn.focus = False
        self.botmore_btn.draw()



    def drawbuttons(self):
        "Called by self.show/update to draw the messages and quit buttons"
        self.buttwin.clear()

        # If a device is in focus, these buttons are not
        if self.focus or self.topmore_btn.focus or self.botmore_btn.focus:
            self.messages_btn.focus = False
            self.quit_btn.focus = False
        elif not self.quit_btn.focus:
            self.messages_btn.focus = True
        elif not self.messages_btn.focus:
            self.quit_btn.focus = True

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
            self.drawdevices()
            self.drawbuttons()
            self.devwinrefresh()
            self.buttwin.noutrefresh()
            curses.doupdate()
            return
        if event.devicename is not None:
            if event.devicename.lower() not in self.devices:
                # unknown device, check this is a definition
                if isinstance(event, events.defVector) or isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwinrefresh()
                    curses.doupdate()


    def topmorechosen(self):
        "Update when topmore button pressed"
        if not self.topmore_btn.focus:
            return
        # pressing topmore button may cause first device to be displayed
        # which results in the topmore button vanishing
        btnlist = list(self.devices.keys())
        # btnlist is the names of the device buttons
        if self.topdevice == 1:
            self.topmore_btn.focus = False
            self.focus = btnlist[0]
        self.topline -= 2
        self.drawdevices()
        self.devwinrefresh()


    def botmorechosen(self):
        "Update when botmore button pressed"
        if not self.botmore_btn.focus:
            return
        # pressing botmore button may cause last device to be displayed
        # which results in the botmore button vanishing
        btnlist = list(self.devices.keys())
        # btnlist is the names of the device buttons
        if self.bottomdevice == len(btnlist) - 2:
            self.botmore_btn.focus = False
            self.focus = btnlist[-1]
        self.topline += 2
        self.drawdevices()
        self.devwinrefresh()



# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"
        try:
            self.stdscr.nodelay(True)
            while True:
                key = await self.keyinput()
                if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                    return key

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
                            # either a top or bottem more button or a device has focus
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

                    devicelist = list(self.devices.values())
                    for btn_number in range(self.topdevice, self.bottomdevice+1):
                        btn = devicelist[btn_number]
                        # key tuple pad starts at screen row self.devwintop, and
                        # has been scrolled up at self.topline
                        if (key[0]-self.devwintop+self.topline, key[1]) in btn:
                            if btn.focus:
                                return btn.onclick
                            else:
                                # button not in focus, so set it
                                self.defocus()
                                btn.focus = True
                                btn.draw()
                                self.focus = btn.onclick
                                self.devwinrefresh()
                                self.buttwin.noutrefresh()
                                curses.doupdate()
                                break
                    continue


                # which button has focus
                btnlist = list(self.devices.keys())
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

                    # If not Quit or Messages, return the device in focus
                    return self.focus

                if key in (32, 9, 261, 338, 258):
                    # go to the next button
                    if self.quit_btn.focus:
                        self.quit_btn.focus = False
                        if self.topdevice:
                            # that is, if topdevice does not have index zero
                            self.topmore_btn.focus = True
                        else:
                            self.focus = btnlist[0]
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        self.quit_btn.focus = True
                    elif self.topmore_btn.focus:
                        self.topmore_btn.focus = False
                        self.focus = btnlist[self.topdevice]
                    elif self.botmore_btn.focus:
                        self.botmore_btn.focus = False
                        self.messages_btn.focus = True
                    else:
                        # one of the devices has focus
                        indx = btnlist.index(self.focus)
                        if indx == len(self.client) - 1:
                            # very last device, the botmore_btn should not be shown
                            self.focus = None
                            self.messages_btn.focus = True
                        elif indx == self.bottomdevice:
                            if key in (338, 258):      # 338 page down, 258 down arrow
                                # display next device
                                self.topline += 2
                                self.focus = btnlist[indx+1]
                            else:
                                # last device on display
                                self.focus = None
                                self.botmore_btn.focus = True
                        else:
                            self.focus = btnlist[indx+1]

                elif key in (353, 260, 339, 259):
                    # go to previous button
                    if self.quit_btn.focus:
                        self.quit_btn.focus = False
                        self.messages_btn.focus = True
                    elif self.messages_btn.focus:
                        self.messages_btn.focus = False
                        if self.botmore_btn.show:
                            self.botmore_btn.focus = True
                        else:
                            self.focus = btnlist[-1]
                    elif self.botmore_btn.focus:
                        self.botmore_btn.focus = False
                        self.focus = btnlist[self.bottomdevice]
                    elif self.topmore_btn.focus:
                        self.topmore_btn.focus = False
                        self.quit_btn.focus = True
                    elif self.focus == btnlist[0]:
                        self.focus = None
                        self.quit_btn.focus = True
                    else:
                        indx = btnlist.index(self.focus)
                        if indx == self.topdevice:
                            if key in (339, 259): # 339 page up, 259 up arrow
                                self.topline -= 2
                                self.focus = btnlist[indx-1]
                            else:
                                self.focus = None
                                self.topmore_btn.focus = True
                        else:
                            self.focus = btnlist[indx-1]

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

        self.devicename = devicename
        # start with vectorname None, a vector to view will be chosen by this screen
        self.vectorname = None

        # title window  (1 line, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(1, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Device: " + self.devicename, curses.A_BOLD)

        # messages window (1 line, full row, starting at 2,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 2, 0)
        self.lastmessage = ""

        # list areas of the screen, one of these areas as the current 'focus'
        # Groups being the horizontal line of group names associated with a device
        # Vectors being the area showing the vectors associated with a device and group
        # and Devices Messages and Quit are the bottom buttons
        self.screenparts = ("Groups", "Vectors", "Devices", "Messages", "Quit")

        # groups list
        try:
            self.groups = []
            self.groupwin = GroupButtons(self.stdscr, self.consoleclient)

            # window showing the vectors of the active group
            self.vectorswin = VectorListWin(self.stdscr, self.consoleclient)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise

        # bottom buttons, [Devices] [Messages] [Quit]

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.device = None
        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 15)
        self.devices_btn.focus = True
        self.focus = "Devices"

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 5)
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 6)


    @property
    def activegroup(self):
        "Return name of group currently active"
        return self.groupwin.active

    def close(self, value):
        self._close = value
        self.groupwin.close(value)
        self.vectorswin.close(value)


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


        # get the groups this device contains, use a set to avoid duplicates
        groupset = {vector.group for vector in self.device.values() if vector.enable}
        self.groups = sorted(list(groupset))
        # populate a widget showing horizontal list of groups
        self.groupwin.set_groups(self.groups)
        self.groupwin.draw()

        # Draw the device vector widgets, as given by self.activegroup
        self.vectorswin.draw(self.devicename, self.activegroup)

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


    def update(self, event):
        "Change anything that has been updated"
        if self.device.messages:
            if self.device.messages[0] != self.lastmessage:
                self.lastmessage = self.device.messages[0]
                widgets.drawmessage(self.messwin, self.lastmessage, maxcols=self.maxcols)
                self.messwin.noutrefresh()


        # get the groups this device contains, use a set to avoid duplicates
        groupset = {vector.group for vector in self.device.values() if vector.enable}
        groups = sorted(list(groupset))
        if self.groups != groups:
            self.groups = groups
            # populate a widget showing horizontal list of groups
            self.groupwin.set_groups(self.groups)
            self.groupwin.draw()
            self.groupwin.noutrefresh()

        # Draw the device vector widgets, as given by self.activegroup
        self.vectorswin.draw(self.devicename, self.activegroup)
        self.vectorswin.noutrefresh()
        curses.doupdate()


    async def inputs(self):
        "Gets inputs from the screen"

        try:
            self.stdscr.nodelay(True)
            while True:
                if self.focus == "Groups":
                    # focus has been given to the GroupButtons which monitors its own inputs
                    key = await self.groupwin.input()
                    if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                        return key
                    if key == 10:
                        # must update the screen with a new group
                        self.show()
                        continue
                elif self.focus == "Vectors":
                    # focus has been given to VectorListWin which monitors its own inputs
                    key = await self.vectorswin.input()
                    if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                        return key
                    if key == 10:
                        # a vector has been chosen, get the vectorname chosen
                        self.vectorname = self.vectorswin.vectorname
                        return "Vectors"
                else:
                    key = await self.keyinput()
                    if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                        return key

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
                    self.vectorswin.focus = False
                elif self.focus == "Groups":
                    self.groupwin.focus = False
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
                elif newfocus == "Groups":
                    self.groupwin.focus = True
                elif newfocus == "Devices":
                    self.devices_btn.focus = True
                elif newfocus == "Messages":
                    self.messages_btn.focus = True
                elif newfocus == "Quit":
                    self.quit_btn.focus = True
                self.focus = newfocus

                # so buttons have been set with the appropriate focus
                # now draw them
                self.vectorswin.draw(self.devicename, self.groupwin.active)
                self.groupwin.draw()
                self.devices_btn.draw()
                self.messages_btn.draw()
                self.quit_btn.draw()

                self.vectorswin.noutrefresh()
                self.groupwin.noutrefresh()
                self.buttwin.noutrefresh()
                curses.doupdate()
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"

# The following two windows, GroupButtons and VectorListWin are sub windows of ChooseVectorScreen

class GroupButtons(ParentScreen):

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)

        # window (1 line, full row, starting at 4,0)
        self.window = self.stdscr.subwin(1, self.maxcols, 4, 0)

        self.groups = []          # list of group names
        self.groupcols = {}       # dictionary of groupname to column number
        # active is the name of the group currently being shown
        self.active = None
        # this is True, if this widget is in focus
        self._focus = False
        # this is set to the group in focus, if any
        self.groupfocus = None

        # the horizontal display of group buttons may not hold all the buttons
        # give the index of self.groups from and to
        self.fromgroup = 0
        self.togroup = 0
        self.nextcol = 0
        self.nextfocus = False
        self.prevfocus = False


    def noutrefresh(self):
        self.window.noutrefresh()


    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, value):
        if self._focus == value:
            return
        self._focus = value
        if value:
            self.groupfocus = self.groups[self.fromgroup]
        else:
            self.groupfocus = None
            self.nextfocus = False
            self.prevfocus = False


    def set_groups(self, groups):
        self.groups = groups.copy()
        if not len(self.groups):
            self.groups = ["default"]
        self.groupcols.clear()
        if self.groupfocus:
            if self.groupfocus not in self.groups:
                self.groupfocus = None
                self.nextfocus = False
                self.prevfocus = False
        if self.active is None:
            self.active = self.groups[0]
        elif self.active not in self.groups:
            self.active = self.groups[0]


    def draw(self):
        "Draw the line of groups"
        self.groupcols.clear()
        if self.active is None:
            self.active = self.groups[0]
        # clear the line
        self.window.clear()

        # draw 'Prev' button if necessary
        if self.fromgroup:
            self.drawprev(self.prevfocus)
            col = 11
        else:
            col = 2

        for indx, group in enumerate(self.groups):
            if indx < self.fromgroup:
                continue
            self.groupcols[group] = col

            # is this the last?
            if group == self.groups[-1]:
                self.togroup = indx
                if self.nextfocus:
                    self.nextfocus = False
                    self.groupfocus = group

            col = self.drawgroup(group)

            # If not the last, check if another can be drawn
            # otherwise print the 'Next' button
            if (group != self.groups[-1]) and (col+20 >= self.maxcols):
                self.nextcol = col
                self.drawnext(self.nextfocus)
                self.togroup = indx
                break


    def drawgroup(self, group):
        # draw the group, return col position of next group to be shown
        grouptoshow = "["+group+"]"
        col = self.groupcols[group]
        if group == self.active:
            if self.groupfocus == group:
                # group in focus
                self.window.addstr(0, col, grouptoshow, curses.A_REVERSE)
            else:
                # active item
                self.window.addstr(0, col, grouptoshow, curses.A_BOLD)
        else:
            if self.groupfocus == group:
                # group in focus
                self.window.addstr(0, col, grouptoshow, curses.A_REVERSE)
            else:
                self.window.addstr(0, col, grouptoshow)
        col += (len(grouptoshow) + 2)
        return col


    def drawprev(self, focus=False):
        if focus:
            self.window.addstr(0, 2, "<<Prev]", curses.A_REVERSE)
            # set focus on prev button
            self.prevfocus = True
            # remove focus from group
            self.groupfocus = None
        else:
            self.window.addstr(0, 2, "<<Prev]")
            self.prevfocus = False


    def drawnext(self, focus=False):
        if focus:
            # remove focus from group
            self.groupfocus = None
            self.drawgroup(self.groups[self.togroup])
            # set focus on next button
            self.nextfocus = True
            self.window.addstr(0, self.nextcol, "[Next>>", curses.A_REVERSE)
        else:
            self.window.addstr(0, self.nextcol, "[Next>>")
            self.nextfocus = False


    async def input(self):
        "Get group button pressed, or next or previous"
        self.stdscr.nodelay(True)
        while True:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key

            if key == 10:

                if self.prevfocus:
                    # Enter has been pressed when the 'Prev' button has focus
                    self.fromgroup = self.fromgroup - 1
                    if not self.fromgroup:
                        # self.fromgroup is zero, so no prev button
                        self.prevfocus = False
                        self.groupfocus = self.groups[0]
                    self.draw()
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue

                if self.nextfocus:
                    # Enter has been pressed when the 'Next' button has
                    # focus
                    if self.fromgroup:
                        self.fromgroup = self.fromgroup + 1
                    else:
                        self.fromgroup = 2
                    self.draw()
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue

                # set this groupfocus button as the active button,
                # and return the key
                if self.active == self.groupfocus:
                    # no change
                    continue
                # set a change of the active group
                self.active = self.groupfocus
                return 10

            if key in (32, 9, 261):   # space, tab, right arrow
                if self.prevfocus:
                    # remove focus from prev button
                    self.drawprev()
                    # set focus on from button
                    self.groupfocus = self.groups[self.fromgroup]
                    self.drawgroup(self.groupfocus)
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue
                if self.nextfocus:
                    return 258   # treat as 258 down arrow key
                # go to the next group
                if self.groupfocus == self.groups[-1]:
                    # At the last group, cannot go further
                    return key
                indx = self.groups.index(self.groupfocus)
                if self.togroup and (indx+1 > self.togroup):
                    # next choice is beyond togroup
                    if key == 261:   # right arrow
                        if self.fromgroup:
                            self.fromgroup = self.fromgroup + 1
                        else:
                            self.fromgroup = 2
                        # get the new group in focus
                        self.groupfocus = self.groups[indx+1]
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue
                    else:
                        # so highlight 'next' key
                        self.drawnext(focus=True)
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue
                # get the new group in focus
                self.groupfocus = self.groups[indx+1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                continue
            if key in (353, 260):   # 353 shift tab, 260 left arrow
                if self.prevfocus:
                    # remove focus from the button
                    self.drawprev(focus=False)
                    return 258   # treat as 258 down arrow key
                if self.nextfocus:
                    # group to the left of the 'Next' button, now has focus
                    self.groupfocus = self.groups[self.togroup]
                    self.drawgroup(self.groups[self.togroup])
                    # remove focus from next button
                    self.drawnext(focus=False)
                    self.window.noutrefresh()
                    curses.doupdate()
                    continue
                # go to the previous group
                indx = self.groups.index(self.groupfocus)
                if not indx:
                    # indx zero means first group
                    return key
                if indx == self.fromgroup:
                    if key == 260:  # left arrow, moves to previous group
                        self.fromgroup = self.fromgroup - 1
                        if not self.fromgroup:
                            # self.fromgroup is zero, so no prev button
                            self.prevfocus = False
                            self.groupfocus = self.groups[0]
                        else:
                            # get the new group in focus
                            self.groupfocus = self.groups[indx-1]
                        self.draw()
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue
                    else:
                        # the button to the left must be the 'Prev' button
                        # remove focus from current button
                        currentgroup = self.groupfocus
                        self.groupfocus = None
                        self.drawgroup(currentgroup)
                        # set Prev button as the focus
                        self.drawprev(focus=True)
                        self.window.noutrefresh()
                        curses.doupdate()
                        continue

                self.groupfocus = self.groups[indx-1]
                self.draw()
                self.window.noutrefresh()
                curses.doupdate()
                continue
            if key in (338, 339, 258, 259):          # 338 page down, 339 page up, 258 down arrow, 259 up arrow
                return key



class VectorListWin(ParentScreen):

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)

        # number of lines in a pad, assume 50
        self.padlines = 50
        self.window = curses.newpad(self.padlines, self.maxcols)

        # vector index number of top vector being displayed
        self.topvectindex = 0

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

        # list of vector states, recorded to check if any changes have occurred
        self.vectorstates = []

        # list of vector buttons
        self.vector_btns = []

        # start with vectorname None, a vector to view will be chosen by this screen
        self.vectorname = None


    @property
    def botvectindex(self):
        """vector index number of bottom vector being displayed"""
        return min(self.topvectindex + self.displaylines//2, self.lastvectorindex)


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
        if self.topvectindex:
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

        nochange = True  # flag to indicate the window does not need to be redrawn

        if (groupname != self.groupname) or (devicename != self.devicename):
            nochange = False

        self.devicename = devicename
        self.device = self.client[devicename]
        self.groupname = groupname

        vectornames = [vector.name for vector in self.device.values() if vector.group == self.groupname and vector.enable]
        vectornames.sort()

        if nochange:
            currentnames = [vector.name for vector in self.vectors]
            if vectornames != currentnames:
                # A change has occurred
                nochange = False

        if nochange:
            # Check if any vector state has changed
            newstates = [vector.state.lower() for vector in self.vectors]
            if self.vectorstates != newstates:
                # A change has occurred
                nochange = False

        if nochange:
            # no change, therefore do not draw
            return

        # A change to the vectors listed, or to a vector state has occurred
        # proceed to draw the screen

        self.vectors = [self.device[name] for name in vectornames]
        self.vectorstates = [vector.state.lower() for vector in self.vectors]

        self.window.clear()
        self.topmorewin.clear()
        self.botmorewin.clear()

        self.topmore_btn.show = False
        self.topmore_btn.draw()

        self.topvectindex = 0

        try:

            # draw the vectors in the client with this device and group

            # pad may need increasing if extra members have been added
            padlines = max(self.padlines, len(self.vectors)*2)
            if padlines != self.padlines:
                self.padlines = padlines
                self.window.resize(self.padlines, self.maxcols)

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


            if self.botvectindex >= self.lastvectorindex:
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

        coords = (self.topvectindex*2, 0, 8, 1, self.displaylines + 8, self.maxcols-2)
                  # pad row, pad col, win start row, win start col, win end row, win end col

        self.topmorewin.noutrefresh()
        self.window.overwrite(self.stdscr, *coords)
        self.window.noutrefresh(*coords)
        self.botmorewin.noutrefresh()


    def upline(self):
        if not self.topvectindex:
            # already at top
            return
        self.topvectindex -= 1
        if not self.topvectindex:
            # at the top vectors
            self.topmore_btn.show = False
            self.topmore_btn.draw()
            btn = self.vector_btns[0]
            btn.focus = True
            btn.draw()
        if (not self.botmore_btn.show) and (self.botvectindex < self.lastvectorindex):
            self.botmore_btn.show = True
            self.botmore_btn.draw()
        self.noutrefresh()
        curses.doupdate()


    def downline(self):
        if self.botvectindex >= self.lastvectorindex:
            # already at the bottom
            return
        self.topvectindex += 1
        if not self.topmore_btn.show:
            self.topmore_btn.show = True
            self.topmore_btn.draw()
        if self.botvectindex >= self.lastvectorindex:
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
        while True:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key

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

            elif key in (32, 9, 261, 338, 258):
                # go to the next
                if self.botmore_btn.focus:
                    self.focus = False
                    return key
                elif self.topmore_btn.focus:
                    # set focus on top vector
                    self.topmore_btn.focus = False
                    btn = self.vector_btns[self.topvectindex]
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
                    if btnindex >= self.botvectindex:
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
                    if btnindex >= self.botvectindex:
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
                    btn = self.vector_btns[self.botvectindex]
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
                    if btnindex == self.topvectindex:
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
                    if btnindex == self.topvectindex:
                        self.set_top_focus()
                    else:
                        self.vector_btns[btnindex].focus = False
                        self.vector_btns[btnindex-1].focus = True
                        self.vector_btns[btnindex].draw()
                        self.vector_btns[btnindex-1].draw()
                        self.noutrefresh()
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
