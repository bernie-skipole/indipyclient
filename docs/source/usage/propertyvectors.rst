Property Vectors
================

Instances of these classes are created automatically as data is received
from the INDI server, typically you would read their attributes to display
values on a client.

You should never need to instantiate these classes yourself.

All these vectors are mappings of membername to membervalue, and have the
following methods and attributes:

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

**self.perm**

One of "ro", "wo" or "rw". Not applicable to Light Vector, which is read only.

**self.vectortype**

Set to Vector type string such as 'SwitchVector', 'NumberVector' etc.

**self.enable**

If self.enable is False, this property has been 'deleted'.

**self.device**

The device object owning this vector. This attribute is not available in the 'snapshot'.

----

As data is received these vectors are created or updated and are available via ipyclient[devicename][vectorname]

.. autoclass:: indipyclient.propertyvectors.SwitchVector
   :members: send_newSwitchVector, members, memberlabel, snapshot

As well as the common attributes, the switch vector has a rule attribute.

**self.rule**

Applicable to Switch Vectors only, in which case it will be one of "OneOfMany", "AtMostOne" or "AnyOfMany".

For example, if the attribute is "OneOfMany", of the members of this vector, one, and only one can be "On".

----

.. autoclass:: indipyclient.propertyvectors.LightVector
   :members: members, memberlabel, snapshot

----

.. autoclass:: indipyclient.propertyvectors.TextVector
   :members: send_newTextVector, members, memberlabel, snapshot

----

.. autoclass:: indipyclient.propertyvectors.NumberVector
   :members: getfloatvalue, getformattedvalue, send_newNumberVector, members, memberlabel, snapshot

----

.. autoclass:: indipyclient.propertyvectors.BLOBVector
   :members: send_newBLOBVector, members, memberlabel, snapshot
