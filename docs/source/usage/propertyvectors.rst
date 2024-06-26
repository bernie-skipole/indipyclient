Property Vectors
================

Instances of these classes are created automatically as data is received
from the INDI server, typically you would read their attributes to display
values on a client.

You should never need to instantiate these classes yourself.

The classes are defined in indipyclient.propertyvectors

All these vectors are mappings of membername to membervalue, and have the
following methods and attributes:

**Common Methods**

**members(self)**

Returns a dictionary of member objects

**memberlabel(self, membername)**

Returns the member label, given a member name

**Common Attributes**

Attributes of the Vector object are derived from the INDI protocol

**self.name**

**self.label**

**self.group**

**self.state**

One of "Idle", "Ok", "Busy" or "Alert"

**self.message**

**self.devicename**

**self.timestamp**

A UTC datetime object

**self.timeout**

A float, suggested timeout for updating a value.

**self.rule**

Applicable to Switch Vectors only, in which case it will be one of "OneOfMany", "AtMostOne" or "AnyOfMany"

**self.perm**

One of "ro", "wo" or "rw". Not applicable to Light Vector, which is read only.

**self.vectortype**

Set to Vector type string such as 'SwitchVector', 'NumberVector' etc.

**self.enable**

If self.enable is False, this property is 'deleted'.

**self.device**

The device object owning this vector. This attribute is not available in the 'snapshot'.

----

As data is received these vectors are created or updated and are available via ipyclient[devicename][vectorname]

.. autoclass:: indipyclient.propertyvectors.SwitchVector
   :members: send_newSwitchVector

----

.. autoclass:: indipyclient.propertyvectors.LightVector

----

.. autoclass:: indipyclient.propertyvectors.TextVector
   :members: send_newTextVector

----

.. autoclass:: indipyclient.propertyvectors.NumberVector
   :members: getfloatvalue, getformattedvalue, send_newNumberVector

----

.. autoclass:: indipyclient.propertyvectors.BLOBVector
   :members: send_newBLOBVector
