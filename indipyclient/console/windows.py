
import asyncio, curses, sys, os, pathlib, textwrap

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
        # if close string is set, it becomes the return value from input routines
        self._close = ""

    def close(self, value):
        self._close = value


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
            return key
        return "Stop"


class MessagesScreen(ConsoleClientScreen):

    def __init__(self, stdscr, consoleclient):
        super().__init__(stdscr, consoleclient)

        self.disconnectionflag = False

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Messages", curses.A_BOLD)

        # messages window (8 lines, full row - 4, starting at 4,3)
        self.messwin = self.stdscr.subwin(8, self.maxcols-4, 4, 3)

        # info window 6 lines, width 60
        self.infowin = self.stdscr.subwin(6, 60, self.maxrows-8, self.maxcols//2 - 29)
        self.infowin.addstr(0, 14, "All Timestamps are UTC")
        self.infowin.addstr(1, 0, "Once connected, choose 'Devices' and press Enter. Then use")
        self.infowin.addstr(2, 0, "Tab/Shift-Tab to move between fields, Enter to select, and")
        self.infowin.addstr(3, 0, "Arrow/Page keys to show further fields where necessary.")
        self.infowin.addstr(5, 5, "Enable/Disable BLOB's:")

        self.enable_btn = widgets.Button(self.infowin, "Enabled", 5, 30)
        self.disable_btn = widgets.Button(self.infowin, "Disabled", 5, 40)
        if self.consoleclient.blobenabled:
            self.enable_btn.bold = True
            self.disable_btn.bold = False
        else:
            self.enable_btn.bold = False
            self.disable_btn.bold = True

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 10)
        self.devices_btn.focus = False
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2)
        self.quit_btn.focus = True


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
        self.enable_btn.focus = False
        self.disable_btn.focus = False
        self.devices_btn.focus = False
        self.quit_btn.focus = True
        self.enable_btn.draw()
        self.disable_btn.draw()
        self.devices_btn.draw()
        self.quit_btn.draw()
        self.titlewin.noutrefresh()
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


# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"
        try:
            self.stdscr.nodelay(True)
            while True:
                key = await self.keyinput()
                if key in ("Resize", "Devices", "Vectors", "Stop"):
                    return key
                if not self.connected:
                    # only accept quit
                    self.enable_btn.focus = False
                    self.disable_btn.focus = False
                    self.devices_btn.focus = False
                    self.quit_btn.focus = True
                    self.enable_btn.draw()
                    self.disable_btn.draw()
                    self.devices_btn.draw()
                    self.quit_btn.draw()
                    self.buttwin.noutrefresh()
                    self.infowin.noutrefresh()
                    curses.doupdate()
                    if key == 10:
                        return "Quit"
                    continue

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
                    if self.devices_btn.focus:
                        return "Devices"
                    elif self.quit_btn.focus:
                        return "Quit"
                    elif self.enable_btn.focus:
                        return "EnableBLOBs"
                    elif self.disable_btn.focus:
                        self.consoleclient.blobenabled = False
                        await self.client.report("Warning! BLOBs disabled")
                        self.consoleclient.send_disableBLOB()
                        self.enable_btn.bold = False
                        self.disable_btn.bold = True
                        self.enable_btn.draw()
                        self.disable_btn.draw()
                        self.infowin.noutrefresh()
                        curses.doupdate()
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

        messagerow = self.maxcols//2 - 30

        self.pathwin.addstr(2, messagerow, "The INDI spec allows BLOB's to be received, by device or")
        self.pathwin.addstr(3, messagerow, "by device and property. This client is a simplification")
        self.pathwin.addstr(4, messagerow, "and enables or disables all received BLOB's.")
        self.pathwin.addstr(5, messagerow, "To enable BLOB's ensure the path below is set to a valid")
        self.pathwin.addstr(6, messagerow, "folder where BLOBs will be put, and press submit.")

        self.pathfocus = False

        if self.consoleclient.blobfolder is None:
            self._newpath = ''
        else:
            self._newpath = str(self.consoleclient.blobfolder)

        self.submit_btn = widgets.Button(self.pathwin, "Submit", 10, self.maxcols//2 - 3)

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.devices_btn = widgets.Button(self.buttwin, "Devices", 0, self.maxcols//2 - 15)
        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 5)
        self.messages_btn.focus = True
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 6)


    def blobfoldertext(self):
        "Return the blobfolder path, padded to the required width for editing"
        length = self.maxcols-10
        bf = self._newpath.strip()
        if not bf:
            return " "*length
        if len(bf) > length:
            bf = textwrap.shorten(bf, width=length, placeholder="...")
        else:
            bf = bf.ljust(length)
        return bf


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

        # draw the path
        self.drawpath()
        # draw submit, device, messages and quit buttons
        self.drawbuttons()

        # refresh these sub-windows and update physical screen
        self.titlewin.noutrefresh()
        self.messwin.noutrefresh()
        self.pathwin.noutrefresh()
        self.buttwin.noutrefresh()
        curses.doupdate()


    def drawpath(self):
        "Draws the path, together with its focus state"
        if self.pathfocus:
            self.pathwin.addstr(8, 0, "[", curses.A_BOLD)
            self.pathwin.addstr(8, 1, self.blobfoldertext())
            self.pathwin.addstr(8, self.maxcols-9, "]", curses.A_BOLD)
        else:
            self.pathwin.addstr(8, 0, "[" + self.blobfoldertext() + "]")


    def drawbuttons(self):
        "Draws the buttons, together with their focus state"
        # If this window controls are in focus, these buttons are not
        if self.pathfocus:
            self.submit_btn.focus = False
            self.messages_btn.focus = False
            self.quit_btn.focus = False
            self.devices_btn.focus = False

        self.submit_btn.draw()
        self.messages_btn.draw()
        self.devices_btn.draw()
        self.quit_btn.draw()


    def update(self, event):
        "Only update if global message has changed"
        if isinstance(event, events.Message):
            widgets.drawmessage(self.messwin, self.client.messages[0], maxcols=self.maxcols)
            self.messwin.noutrefresh()
            curses.doupdate()


    async def inputs(self):
        "Gets inputs from the screen"

        try:
            self.stdscr.nodelay(True)
            while True:
                if self.pathfocus:
                    # text input here
                    key = await self.textinput()
                else:
                    key = await self.keyinput()
                if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                    return key
                if key == 10:
                    if self.quit_btn.focus:
                        widgets.drawmessage(self.messwin, "Quit chosen ... Please wait", bold = True, maxcols=self.maxcols)
                        self.messwin.noutrefresh()
                        curses.doupdate()
                        return "Quit"
                    elif self.messages_btn.focus:
                        return "Messages"
                    elif self.devices_btn.focus:
                        if self.client.connected:
                            return "Devices"
                        else:
                            return "Messages"
                    elif self.submit_btn.focus:
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
                                    self.drawpath()
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

                elif key in (32, 9, 261, 338, 258):
                    # go to the next button
                    if self.pathfocus:
                        self.pathfocus = False
                        self.submit_btn.focus = True
                        self.drawpath()
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
                        self.pathfocus = True
                        self.drawpath()

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
                        self.pathfocus = True
                        self.drawpath()
                    elif self.pathfocus:
                        self.pathfocus = False
                        self.quit_btn.focus = True
                        self.drawpath()
                else:
                    # button not recognised
                    continue

                # draw buttons
                self.drawbuttons()
                self.buttwin.noutrefresh()
                self.pathwin.noutrefresh()
                curses.doupdate()

        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"


    def drawpath(self):
        "Draws the path, together with its focus state"
        if self.pathfocus:
            self.pathwin.addstr(8, 0, "[", curses.A_BOLD)
            self.pathwin.addstr(8, 1, self.blobfoldertext())
            self.pathwin.addstr(8, self.maxcols-9, "]", curses.A_BOLD)
        else:
            self.pathwin.addstr(8, 0, "[" + self.blobfoldertext() + "]")


    async def textinput(self):
        "Input text, set it into self._newvalue"
        # set cursor visible
        curses.curs_set(1)
                                                  # row startcol  endcol      start text
        editstring = widgets.EditString(self.stdscr, 12, 5, self.maxcols-6, self.blobfoldertext())

        while not self.consoleclient.stop:
            key = await self.keyinput()
            if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                return key
            if key == 10:
                curses.curs_set(0)
                return 9
            # key is to be inserted into the editable field, and self._newpath updated
            value = editstring.gettext(key)
            self._newpath = value.strip()
            self.pathwin.addstr( 8, 1, value )
            self.pathwin.noutrefresh()
            editstring.movecurs()
            curses.doupdate()


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
        self.topmore_btn = widgets.Button(self.topmorewin, "<More>", 0, self.maxcols//2 - 7)
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
        self.botmore_btn = widgets.Button(self.botmorewin, "<More>", 0, self.maxcols//2 - 7)
        self.botmore_btn.show = False

        # buttons window (1 line, full row, starting at  self.maxrows - 1, 0)
        # this holds the messages and quit buttons
        self.buttwin = self.stdscr.subwin(1, self.maxcols, self.maxrows - 1, 0)

        self.messages_btn = widgets.Button(self.buttwin, "Messages", 0, self.maxcols//2 - 10)
        self.messages_btn.focus = True
        self.focus = None
        self.quit_btn = widgets.Button(self.buttwin, "Quit", 0, self.maxcols//2 + 2)
        # devicename to button dictionary
        self.devices = {}


    def devicenumber(self):
        "Returns the number of enabled devices"
        dnumber = 0
        for device in self.client.values():
            if device.enable:
                dnumber += 1
        return dnumber


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
        self.topmorewin.clear()
        self.devwin.clear()
        self.botmorewin.clear()

        if not self.devicenumber():
            self.focus = None
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
            self.devices[devicename.lower()] = widgets.Button(self.devwin, devicename, linenumber*2, colnumber)

        # start with all device buttons focus False
        for devbutton in self.devices.values():
            devbutton.focus = False

        if self.focus not in self.devices:
            self.focus = None
        else:
            self.devices[self.focus].focus = True

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

        number_of_devices = self.devicenumber()
        # each device takes 2 lines
        if self.bottomdevice < number_of_devices -1:
            self.botmore_btn.show = True
        else:
            self.botmore_btn.show = False
            self.botmore_btn.focus = False
        self.botmore_btn.draw()



    def drawbuttons(self):
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
                if isinstance(event, events.defVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwinrefresh()
                    curses.doupdate()
                elif isinstance(event, events.defBLOBVector):
                    # could be a new device
                    self.drawdevices()
                    self.devwinrefresh()
                    curses.doupdate()



# 32 space, 9 tab, 353 shift tab, 261 right arrow, 260 left arrow, 10 return, 339 page up, 338 page down, 259 up arrow, 258 down arrow

    async def inputs(self):
        "Gets inputs from the screen"
        try:
            self.stdscr.nodelay(True)
            while True:
                key = await self.keyinput()
                if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                    return key
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
                        # pressing topmore button may cause first device to be displayed
                        # which results in the topmore button vanishing
                        if self.topdevice == 1:
                            self.topmore_btn.focus = False
                            self.focus = btnlist[0]
                        self.topline -= 2
                        self.drawdevices()
                        self.devwinrefresh()
                        curses.doupdate()
                        continue
                    if self.botmore_btn.focus:
                        # pressing botmore button may cause last device to be displayed
                        # which results in the botmore button vanishing
                        if self.bottomdevice == len(self.client) - 2:
                            self.botmore_btn.focus = False
                            self.focus = btnlist[-1]
                        self.topline += 2
                        self.drawdevices()
                        self.devwinrefresh()
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
            while (not self.consoleclient.stop) and (self.consoleclient.screen is self):
                await asyncio.sleep(0)
                if self.focus == "Groups":
                    # focus has been given to the groups widget which monitors its own inputs
                    key = await self.groupwin.input()
                    if key in ("Resize", "Messages", "Devices", "Vectors", "Stop"):
                        return key
                    if key == 10:
                        # must update the screen with a new group
                        self.show()
                        continue
                elif self.focus == "Vectors":
                    # focus has been given to Vectors which monitors its own inputs
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

# These windows are sub windows of ChooseVectorScreen

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
