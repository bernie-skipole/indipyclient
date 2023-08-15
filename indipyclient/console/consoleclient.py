
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
            if not self.connected:
                await asyncio.sleep(2)
                continue
            try:
                # the device and vector should be recorded in this mapping
                vector = self['led']['ledswitchvector']
            except KeyError:
                # The device and vector have not been received yet, send a getProperties
                # requesting info from the driver and wait a couple of seconds
                await self.send_getProperties()
                await asyncio.sleep(2)
                continue
            await asyncio.sleep(0)
