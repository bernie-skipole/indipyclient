Vectors
=======

Instances of these classes are created automatically as data is received
from the INDI server, typically you would read their attributes to display
values on a client.

.. autoclass:: indipyclient.propertyvectors.Vector
   :members: members, memberlabel


**Attributes**

Attributes of the Vector object are derived from the INDI protocol

**self.name**

**self.label**

**self.group**

**self.state**

**self.message**

**self.devicename**

**self.rule**

None unless inherited and set by Switch Vectors

**self.perm**

**self.vectortype**

Set to Vector type such as SwitchVector, NumberVector etc.

**self.enable**

If self.enable is False, this property is 'deleted'.

----

.. autoclass:: indipyclient.propertyvectors.PropertyVector

**Attributes**

Inherits attributes from Vector, and also has:

**self.device**

The device object owning this vector.
