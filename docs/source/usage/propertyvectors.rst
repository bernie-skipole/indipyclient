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

One of "Idle", "Ok", "Busy" or "Alert"

**self.message**

**self.devicename**

**self.rule**

Applicable to Switch Vectors only, in which case it will be one of "OneOfMany", "AtMostOne" or "AnyOfMany"

**self.perm**

One of "ro", "wo" or "rw". Not applicable to Light Vector, which is read only.

**self.vectortype**

Set to Vector type string such as 'SwitchVector', 'NumberVector' etc.

**self.enable**

If self.enable is False, this property is 'deleted'.

----

.. autoclass:: indipyclient.propertyvectors.PropertyVector

**Attributes**

Inherits attributes from Vector, and also has:

**self.device**

The device object owning this vector.

----

The following vectors all inherit from PropertyVector. As received events arrive from the server, these vectors are created or updated and are available via the mapping of vectorname to vector object of the ipyclient[devicename], device object.

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
