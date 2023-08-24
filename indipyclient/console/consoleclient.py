
import asyncio, sys

import curses

from ..ipyclient import IPyClient
from ..events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector)

from . import windows


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
        self.screen = windows.MessagesScreen(self.stdscr)

        # this is set to True, to shut down the client
        self._shutdown = False
        # and shutdown routine sets this to True to stop coroutines
        self.stop = False
        # these are set to True when asyncrun is finished
        self.showscreenstopped = False
        self.getinputstopped = False

        if curses.LINES < 16 or curses.COLS < 50:
            curses.nocbreak()
            self.stdscr.keypad(False)
            curses.curs_set(1)
            curses.echo()
            curses.endwin()
            print("Terminal too small!")
            sys.exit(1)


    def shutdown(self):
        self._shutdown = True


    async def _checkshutdown(self):
        "If self._shutdown becomes True, shutdown"
        while not self._shutdown:
            await asyncio.sleep(0)
        self.client.report("Shutting down client - please wait")
        self.client.shutdown()
        while not self.client.stopped:
            await asyncio.sleep(0)
        # now stop co-routines
        self.stop = True
        while (not self.showscreenstopped) and (not self.getinputstopped):
            await asyncio.sleep(0)
        # async tasks finished, clear up the terminal
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.curs_set(1)
        curses.echo()
        curses.endwin()


    async def showscreen(self):
        try:
            while not self.stop:
                await asyncio.sleep(0)
                if not self.client.connected:
                    if not isinstance(self.screen, windows.MessagesScreen):
                        self.screen = windows.MessagesScreen(self.stdscr)
                    # display the messages screen
                    self.screen.show("indipyclient console", "Not Connected", self.client.messages)
                    await asyncio.sleep(2)
                    continue
                # to get here a connection must be in place
                if isinstance(self.screen, windows.MessagesScreen):
                    self.screen.show("indipyclient console", "Connected", self.client.messages)
                    await asyncio.sleep(2)
                # some other screen etc....
        except Exception:
            self._shutdown = True
        self.showscreenstopped = True


    async def getinput(self):
        try:
            while not self.stop:
                await asyncio.sleep(0)
                if isinstance(self.screen, windows.MessagesScreen):
                    result = await self.screen.inputs(self)
                    if result == "Quit":
                        self._shutdown = True
                        break
                    if result == "Devices":
                        pass
                    #     self.screen = windows.Devices() etc
        except Exception:
            self._shutdown = True
        self.getinputstopped = True


    async def asyncrun(self):
        """Gathers tasks to be run simultaneously"""
        self.stop = False
        await asyncio.gather(self.showscreen(), self.getinput(), self._checkshutdown())
