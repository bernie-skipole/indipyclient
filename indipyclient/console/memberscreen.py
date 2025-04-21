import curses, time

from . import widgets

from .windows import ParentScreen


class MemberScreen(ParentScreen):

    "This displays the chosen member"


    def __init__(self, stdscr, control, devicename, vectorname, membername):
        super().__init__(stdscr, control)
        self.stdscr.clear()
        curses.flushinp()

        # ensure the cursor is off
        curses.curs_set(0)

        self.devicename = devicename
        self.vectorname = vectorname
        self.membername = membername

        self.device = self.client[self.devicename]
        self.vector = self.device[self.vectorname]

        # timestamp and state window (1 line, full row, starting at 1,0)
        self.tstatewin = self.stdscr.subwin(1, self.maxcols, 1, 0)

        # label window
        self.labelwin = self.stdscr.subwin(1, self.maxcols, 3, 0)

        # member window
        self.memwin = self.stdscr.subwin(self.maxrows - 5, self.maxcols, 4, 0)

        self.memmaxrows, self.memmaxcols = self.memwin.getmaxyx()

        self.timeset = time.monotonic()


    def show(self):
        "Displays the window"

        if not self.device.enable:
            self.memwin.clear()
            self.memwin.addstr(0, 2, f"Device {self.devicename} not available", curses.A_BOLD)
            self.memwin.noutrefresh()
            curses.doupdate()
            return

        if not self.vector.enable:
            self.memwin.clear()
            self.memwin.addstr(0, 2, f"Vector {self.vectorname} not available", curses.A_BOLD)
            self.memwin.noutrefresh()
            curses.doupdate()
            return

        widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)

        tstamp = widgets.localtimestring(self.vector.timestamp)
        vectorlabel = widgets.shorten(self.vector.label, width=self.maxcols//2, placeholder="...")
        self.tstatewin.addstr(0, len(tstamp)+5, vectorlabel)

        displaylabel = widgets.shorten(self.vector.memberlabel(self.membername), width=self.maxcols-5, placeholder="...")
        self.labelwin.addstr(0, 2, displaylabel)

        # draw the contents value here
        if self.vector.vectortype == "NumberVector":
            self.draw_number()
        elif self.vector.vectortype == "TextVector":
            self.draw_text()
        elif self.vector.vectortype == "LightVector":
            self.draw_light()
        elif self.vector.vectortype == "SwitchVector":
            self.draw_switch()
        elif self.vector.vectortype == "BLOBVector":
            self.draw_blob()

        newtime = time.monotonic()
        if newtime < self.timeset+10:
            # only show this in the first ten seconds, if updating
            self.memwin.addstr(self.memmaxrows-1, 2, "Press any key to return")

        #  and refresh
        self.tstatewin.noutrefresh()
        self.memwin.noutrefresh()
        curses.doupdate()


    def update(self, event):
        "An event affecting this vector has occurred, re-draw the screen"
        self.show()


    def timeout(self, event):
        "A timeout event has occurred, update the vector state"
        if self.vector.state == "Busy":
            self.vector.state = "Alert"
            self.vector.timestamp = event.timestamp
            widgets.draw_timestamp_state(self.control, self.tstatewin, self.vector)
            tstamp = widgets.localtimestring(self.vector.timestamp)
            self.tstatewin.addstr(0, len(tstamp)+5, "A timeout has occurred")
            self.tstatewin.noutrefresh()
            curses.doupdate()

    async def inputs(self):
        "Gets inputs from the screen"

        self.stdscr.nodelay(True)
        while True:
            key = await self.keyinput()
            # self.keyinput returns either key, or a tuple or "Stop" or "Resize"
            if key in ("Resize", "Stop"):
                return key
            if isinstance(key, tuple):
                continue
            return "Vectors"


    def draw_number(self):
        "Draws the formatted number"
        self.memwin.clear()
        # draw the number value
        text = self.vector.getformattedvalue(self.membername).strip()
        text = widgets.shorten(text, width=self.memmaxcols-4, placeholder="...")
        # draw the value
        self.memwin.addstr(self.memmaxrows//2, (self.memmaxcols-len(text))//2, text, curses.A_BOLD)


    def draw_text(self):
        "Draws the text"
        self.memwin.clear()
        # draw the text value
        text = self.vector[self.membername].strip()
        text = widgets.shorten(text, width=self.memmaxcols-4, placeholder="...")
        # draw the value
        self.memwin.addstr(self.memmaxrows//2, (self.memmaxcols-len(text))//2, text, curses.A_BOLD)


    def draw_light(self):
        "Draws the light value surrounded by the colou"
        self.memwin.clear()
        # draw the light value
        lowervalue = self.vector[self.membername].strip().lower()
        # draw the light value
        if lowervalue == "idle":
            text = "  Idle   "
        elif lowervalue == "ok":
            text = "   OK    "
        elif lowervalue == "busy":
            text = "  Busy   "
        elif lowervalue == "alert":
            text = "  Alert  "
        else:
            return
        # draw the value
        self.memwin.addstr(self.memmaxrows//2-1, (self.memmaxcols-9)//2, "         ", self.control.color(lowervalue))
        self.memwin.addstr(self.memmaxrows//2, (self.memmaxcols-9)//2, text, self.control.color(lowervalue))
        self.memwin.addstr(self.memmaxrows//2+1, (self.memmaxcols-9)//2, "         ", self.control.color(lowervalue))


    def draw_switch(self):
        "Draws the switch"
        self.memwin.clear()
        # draw the On, Off value
        lowervalue = self.vector[self.membername].strip().lower()
        text = "ON" if lowervalue == "on" else "OFF"
        # draw the value
        self.memwin.addstr(self.memmaxrows//2, (self.memmaxcols-3)//2, text, curses.A_BOLD)


    def draw_blob(self):
        "Draws the received BLOB filename"
        self.memwin.clear()
        # get the last received filename
        filename = self.vector.member(self.membername).filename
        if not filename:
            filename = "- file not yet received -"
        # draw the filename
        text = widgets.shorten(filename, width=self.memmaxcols-4, placeholder="...")
        self.memwin.addstr(self.memmaxrows//2, (self.memmaxcols-len(text))//2, text, curses.A_BOLD)
