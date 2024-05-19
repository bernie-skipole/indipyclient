

import logging
logging.getLogger('indipyclient').addHandler(logging.NullHandler())

from .ipyclient import IPyClient
from .events import (delProperty, defSwitchVector, defTextVector, defNumberVector, defLightVector, defBLOBVector,
                     setSwitchVector, setTextVector, setNumberVector, setLightVector, setBLOBVector, Message, VectorTimeOut)

from .propertymembers import getfloat

version = "0.1.5"
