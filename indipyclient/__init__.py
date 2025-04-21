

import sys

from .ipyclient import IPyClient as IPyClient
from .events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector, Message, VectorTimeOut)

from .propertymembers import getfloat as getfloat

if sys.version_info < (3, 10):
    raise ImportError('indipyclient requires Python >= 3.10')


version = "0.7.4"
