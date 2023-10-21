
import asyncio, curses, sys

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise




from . import widgets

from .. import events


class VectorScreen:

    def __init__(self, stdscr, consoleclient, devicename, vectorname):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.devicename = devicename
        self.vectorname = vectorname

        # title window  (2 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(2, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 0, "Device: " + self.devicename, curses.A_BOLD)
        self.titlewin.addstr(1, 0, "Vector: " + self.vectorname, curses.A_BOLD)


    def show(self):
        "Displays the window"

        self.titlewin.noutrefresh()
        curses.doupdate()
        return

    def update(self, event):
        pass


    async def inputs(self):
        "Gets inputs from the screen"

        try:
            self.stdscr.nodelay(True)
            while (not self.consoleclient.stop) and (self.consoleclient.screen is self):
                await asyncio.sleep(0)
                key = self.stdscr.getch()

                if key == -1:
                    continue
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return "Quit"
