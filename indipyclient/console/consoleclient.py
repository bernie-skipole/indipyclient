
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
        eventque.put(event)


class ConsoleControl:

    def __init__(self, client, eventque):
        self.client = client
        self.eventque = eventque

        # set up screen
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.stdscr.keypad(True)
        self.cols = curses.COLS
        self.lines = curses.LINES

    def shutdown(self):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

    async def asyncrun(self):
        try:
            while True:
                await asyncio.sleep(0)
                try:
                    event = self.eventque.get_nowait()
                except asyncio.QueueEmpty:
                    event = None
                try:
                    messagetuple = self.client.messages.popleft()
                except IndexError:
                    message = None
                else:
                    message = messagetuple[0].isoformat(sep='T')[:21] + "  " + messagetuple[1]
                if not self.client.connected:
                    # display the startscreen
                    if message:
                        widgets.startscreen(self.stdscr, "indipyclient console", "Not Connected", [message])
                    else:
                        widgets.startscreen(self.stdscr, "indipyclient console", "Not Connected")
                    await asyncio.sleep(2)
                    continue
                if not len(self.client):
                    # No devices received yet
                    if message:
                        widgets.startscreen(self.stdscr, "indipyclient console", "Sending getProperties", [message])
                    else:
                        widgets.startscreen(self.stdscr, "indipyclient console", "Sending getProperties")
                    self.client.send_getProperties()
                    await asyncio.sleep(2)
                    continue
        except Exception:
            self.shutdown()
            raise
