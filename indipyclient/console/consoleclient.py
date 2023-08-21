
import asyncio, sys

import curses

from ..ipyclient import IPyClient
from ..events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector)

from . import widgets


class ConsoleClient(IPyClient):

    """This is a console client"""

    # self.clientdata is a dictionary

    async def rxevent(self, event):
        "Pass the event into eventque so it can be obtained by the console control"
        eventque = self.clientdata['eventque']
        await eventque.put(event)


class ConsoleControl:

    def __init__(self, client, eventque):
        self.client = client
        self.eventque = eventque

        # set up screen
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        self.origcursor = curses.curs_set(0)
        self.stdscr.keypad(True)

        # this keeps track of which screen is being displayed
        self.screen = "startscreen"

        # this is set to True, to shut down the client
        self._stop = False


    async def shutdown(self):
        self._stop = True
        await self.client.shutdown()
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.curs_set(self.origcursor)
        curses.echo()
        curses.endwin()

    async def showscreen(self):
        while not self._stop:
            await asyncio.sleep(0)
            try:
                event = self.eventque.get_nowait()
            except asyncio.QueueEmpty:
                event = None
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
        # having brooken from while loop, shutdown the client
        await self.shutdown()



    async def getinput(self):
        while not self._stop:
            await asyncio.sleep(0)
            if self.screen == "startscreen":
                result = widgets.startinputs(self.stdscr)
                if result == "quit":
                    self._stop = True
                    break
                # if result == "Devices":
                #     self.screen = "Devices"

        # having brooken from while loop, shutdown the client
        await self.shutdown()



    async def asyncrun(self):
        """Gathers tasks to be run simultaneously"""
        await asyncio.gather(self.showscreen(), self.getinput(), return_exceptions=True)
