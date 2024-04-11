Members
=======

Instances of these classes are created automatically as data is received
from the INDI server.

Each vector contains one or more members, which can be obtained from the vector members() method.

Each member holds a value, which can be obtained either from the vector[membername] mapping, or from the member object itself, in attribute membervalue.

.. autoclass:: indipyclient.propertymembers.Member


**Attributes**

The Member object contains the attributes:

**self.name**

**self.label**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.SwitchMember

----

.. autoclass:: indipyclient.propertymembers.LightMember

----

.. autoclass:: indipyclient.propertymembers.TextMember

----

.. autoclass:: indipyclient.propertymembers.ParentNumberMember
   :members: getfloatvalue, getfloat, getformattedvalue, getformattedstring

**Attributes**

As well as inherited attributes from the Member class, this object has further attributes:

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

.. autoclass:: indipyclient.propertymembers.NumberMember

----

.. autoclass:: indipyclient.propertymembers.ParentBLOBMember

**Attributes**

As well as inherited attributes from the Member class, this object has further attributes:

**self.blobsize**

blobsize is an integer, the size of the BLOB before any compression.

**self.blobformat**

blobformat should be a string describing the BLOB, such as '.jpeg'

----

.. autoclass:: indipyclient.propertymembers.BLOBMember

----

To summarise:

Your IPyClient object is a mapping of device name to devices, you have:

device = ipyclient[devicename]

Devices are mappings of vectors:

vector = ipyclient[devicename][vectorname]

Vectors are mappings of member values:

value = ipyclient[devicename][vectorname][membername]

The objects defined by classes SwitchMember, LightMember, TextMember, NumberMember and BLOBMember are available via the members attribute:

members = vector.members()

memberobject = members[membername]
