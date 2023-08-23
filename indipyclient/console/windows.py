
import asyncio, curses

from . import widgets

class StartScreen:

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.devices_btn = widgets.Button(stdscr, "Devices", curses.LINES - 1, curses.COLS//2 - 10)
        self.devices_btn.set_focus(True)
        self.quit_btn = widgets.Button(stdscr, "Quit", curses.LINES - 1, curses.COLS//2 + 2)
        self.quit_btn.set_focus(False)

    def startscreen(self, title, info, messages=[]):
        "Displays title, info string and list of messages on a start screen"
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, title, curses.A_BOLD)
        self.stdscr.addstr(2, 0, info)
        lastmessagenumber = len(messages) - 1
        for count, m in enumerate(messages):
            if count == lastmessagenumber:
                # high light the last, current message
                self.stdscr.addstr(4+count, 4, m, curses.A_BOLD)
            else:
                self.stdscr.addstr(4+count, 4, m)
        # put [Devices] [Quit] buttons on screen
        self.devices_btn.draw()
        self.quit_btn.draw()
        self.stdscr.refresh()


    async def startinputs(self):
        "Gets inputs from the screen"
        try:
            self.stdscr.nodelay(True)
            while True:
                await asyncio.sleep(0)
                try:
                    key = self.stdscr.getkey()
                except curses.error:
                    continue
                if key == "q" or key == "Q":
                    return "Quit"
        except Exception:
            return "Quit"
