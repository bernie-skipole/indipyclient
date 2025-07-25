

import sys

from .ipyclient import IPyClient

from .events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector, Message, VectorTimeOut)

from .propertymembers import getfloat

version = "0.8.2"

__all__ = ["version", "IPyClient", "getfloat",
           "delProperty", "defSwitchVector", "defTextVector", "defNumberVector", "defLightVector", "defBLOBVector",
           "setSwitchVector", "setTextVector", "setNumberVector", "setLightVector", "setBLOBVector", "Message", "VectorTimeOut"]

if sys.version_info < (3, 10):
    raise ImportError('indipyclient requires Python >= 3.10')


# IPyClient(indihost="localhost", indiport=7624, **clientdata)
#      This class can be used to create your own scripts or client, and provides
#      a connection to an INDI service, with parsing of the XML protocol.
#      You should create your own class, inheriting from this, and overriding the
#      rxevent method.
#      The argument clientdata provides any named arguments you may wish to pass
#      into the object when instantiating it.
#      The IPyClient object is also a mapping of devicename to device object, which
#      is populated as devices and their vectors are learned from the INDI protocol.

# getfloat(value)
#      The INDI spec specifies several different number formats, given a number
#      in any of these formats, this returns a float.
#      If an error occurs while parsing the number, a TypeError exception is raised."""

# events: These are created as data is received, for example a setTextVector will be created when
#         the connected indi service sends a 'setTextVector' instruction.
#         VectorTimeOut is an exception to this, and will be created if no expected response is received
#         These events can be handled by overwriting the IPyClient.rxevent(self, event) method.
