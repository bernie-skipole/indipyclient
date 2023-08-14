
import asyncio, sys

from ..ipyclient import IPyClient
from ..events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector)


class ConsoleClient(IPyClient):

    """This is a console client"""

    async def rxevent(self, event):
        "The remote device is expected to send a value if the led changes state"
        match event:
            case defSwitchVector(devicename="led", vectorname="ledswitchvector") if 'ledswitchmember' in event.vector:
                ledvalue = event.vector['ledswitchmember']
                print(f"\nReceived value : {ledvalue}")

    async def control(self):
        """Override this to operate your own scripts, and transmit updates"""
        while True:
            await asyncio.sleep(0)
