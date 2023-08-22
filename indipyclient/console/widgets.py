
import asyncio, curses


class StartScreen:

    def __init__(self, stdscr):
        self.stdscr = stdscr

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
        self.stdscr.addstr( curses.LINES - 1, curses.COLS//2 - 10, "[Devices]", curses.A_REVERSE)
        self.stdscr.addstr( curses.LINES - 1, curses.COLS//2 + 2, "[Quit]")
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
