
import asyncio, curses, sys

import traceback
#        except Exception:
#            traceback.print_exc(file=sys.stderr)
#            raise




from . import widgets


from .. import events


class MemberScreen:

    def __init__(self, stdscr, consoleclient, devicename, vectorname, membername):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.maxrows, self.maxcols = self.stdscr.getmaxyx()
        self.consoleclient = consoleclient
        self.client = consoleclient.client
        self.devicename = devicename
        self.vectorname = vectorname
        self.membername = membername

        self.device = self.client[self.devicename]
        self.vector = self.device[self.vectorname]
        self.member = self.vector[self.membername]

        # title window  (3 lines, full row, starting at 0,0)
        self.titlewin = self.stdscr.subwin(3, self.maxcols, 0, 0)
        self.titlewin.addstr(0, 1, self.devicename)
        self.titlewin.addstr(1, 1, self.vectorname + " : " + self.vector.group)
        self.titlewin.addstr(2, 1, self.vector.label, curses.A_BOLD)

        # messages window (1 line, full row, starting at 3,0)
        self.messwin = self.stdscr.subwin(1, self.maxcols, 3, 0)

        # timestamp and state window (1 line, full row, starting at 4,0)
        self.tstatewin = self.stdscr.subwin(1, self.maxcols, 4, 0)
