Members
=======

Instances of these classes are created automatically as data is received
from the INDI server.

Each vector contains one or more members, which can be obtained from the vector members() method.

You should never need to instantiate these classes yourself.

The classes are defined in indipyclient.propertymembers


----

.. autoclass:: indipyclient.propertymembers.SwitchMember

**Attributes**

**self.name**

**self.label**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.LightMember

**Attributes**

**self.name**

**self.label**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.TextMember

**Attributes**

**self.name**

**self.label**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.NumberMember
   :members: getfloatvalue, getfloat, getformattedvalue, getformattedstring

**Attributes**

**self.name**

**self.label**

**self.membervalue**

A string value of the number taken from the XML protocol

**self.format**

A string defining the format, specified in the INDI protocol, this is used by the above methods to create the formatted value string.

**self.min**

The minimum value

**self.max**

The maximum, if min is equal to max, the client should ignore these.

**self.step**

step is incremental step values, set to a string of zero if not used.

These values, and self.membervalue are strings taken from the XML protocol. The getfloatvalue and getfloat methods can be used to parse these values to floats.

----

.. autoclass:: indipyclient.propertymembers.BLOBMember

**Attributes**

**self.name**

**self.label**

**self.membervalue**

A Bytes value of the received BLOB.

**self.blobsize**

blobsize is an integer, the size of the BLOB before any compression.

**self.blobformat**

blobformat should be a string describing the BLOB, such as '.jpeg'

----

To summarise:

Your IPyClient object is a mapping of device name to devices, you have:

device = ipyclient[devicename]

Devices are mappings of vectors:

vector = ipyclient[devicename][vectorname]

Vectors are mappings of member values:

value = ipyclient[devicename][vectorname][membername]

The objects defined by classes SwitchMember, LightMember, TextMember, NumberMember and BLOBMember are available via the vector members() method:

members = vector.members()

memberobject = members[membername]
