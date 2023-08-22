
import asyncio, sys

import curses

from ..ipyclient import IPyClient
from ..events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector)

from . import widgets


class ConsoleClient(IPyClient):

    """This is a console client"""

    pass

class ConsoleControl:

    def __init__(self, client):
        self.client = client

        # set up screen
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.stdscr.keypad(True)

        # this keeps track of which screen is being displayed
        self.screen = "startscreen"

        # this is set to True, to shut down the client
        self._shutdown = False
        # and shutdown routine sets this to True to stop coroutines
        self._stop = False


    def shutdown(self):
        self._shutdown = True


    async def _checkshutdown(self):
        "If self._shutdown becomes True, shutdown"
        while not self._shutdown:
            await asyncio.sleep(0)
        self.client.report("Shutting down client - please wait")
        await asyncio.sleep(1)
        self.client.shutdown()
        # now stop co-routines
        self._stop = True
        await asyncio.sleep(0.5)
        # clear up the terminal
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()


    async def showscreen(self):
        try:
            while not self._stop:
                await asyncio.sleep(0)
                if not self.client.connected:
                    # display the startscreen
                    self.screen = "startscreen"
                    messages = [ t.isoformat(sep='T')[11:21] + "  " + m for t,m in reversed(self.client.messages) ]
                    widgets.startscreen(self.stdscr, "indipyclient console", "Not Connected", messages)
                    await asyncio.sleep(2)
                    continue
                # to get here a connection must be made
                if self.screen == "startscreen":
                    messages = [ t.isoformat(sep='T')[11:21] + "  " + m for t,m in reversed(self.client.messages) ]
                    widgets.startscreen(self.stdscr, "indipyclient console", "Connected", messages)
                    await asyncio.sleep(2)
                # some other screen etc....
        except Exception:
            self._shutdown = True


    async def getinput(self):
        try:
            while not self._stop:
                await asyncio.sleep(0)
                if self.screen == "startscreen":
                    result = await widgets.startinputs(self.stdscr)
                    if result == "Quit":
                        self._shutdown = True
                        break
                    # if result == "Devices":
                    #     self.screen = "Devices"
        except Exception:
            self._shutdown = True


    async def asyncrun(self):
        """Gathers tasks to be run simultaneously"""
        await asyncio.gather(self.showscreen(), self.getinput(), self._checkshutdown())
