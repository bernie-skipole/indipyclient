Property Vectors
================

Instances of these classes are created automatically as data is received
from the INDI server, typically you would read their attributes to display
values on a client.

You should never need to instantiate these classes yourself.

All these vectors are mappings of membername to membervalue, and have the
following methods and attributes:

**Common Methods - All the vector classes have the following methods:**


**member(membername)**
    Returns the member object

**memberlabel(membername)**
    Returns the member label, given a member name

**members()**
    Returns a dictionary of member objects

**async create_clientevent(eventtype="ClientEvent",  \*\*payload)**
    Creates a ClientEvent, and calls the IPyClient rxevent co-routine

This can be used to generate an event which may be of use to the programmer
if the rxevent co-routine processes data in some way, and it is wanted
to inject data into that process for any purpose, then this can be used.

The event will be a ClientEvent object, the attribute eventtype is by default "ClientEvent"
but can be set to any string, the payload can be any kwargs wanted.

**snapshot()**
    Take a snapshot of the vector and returns an object which is a restricted copy of the current state of the vector. Vector methods for sending data will not be available. This copy will not be updated by events. This is provided so that you can handle the vector data, without fear of the value changing.

The snapshot will have the same common attributes and methods as the vector, apart from the snapshot and create_clientevent methods, and the device attribute. It will also have the extra methods:

**dictdump(inc_blob=False)**
    Returns a dictionary of this vector, with datetime objects converted to strings.
    Set inc_blob to True to include BLOB values in the dictionary.

**dump(fp, indent=None, separators=None, inc_blob=False)**
    Serialize the snapshot as a JSON formatted stream to fp, a file-like object.
    This uses the Python json module which always produces str objects, not bytes
    objects. Therefore, fp.write() must support str input.
    Set inc_blob to True to include BLOB values in the file.

**dumps(indent=None, separators=None, inc_blob=False)**
    Returns a JSON string of the snapshot.
    Set inc_blob to True to include BLOB values in the string.


**Common Attributes - All the vector classes have the following attributes:**

**self.name**

**self.label**

**self.group**

**self.state**

One of "Idle", "Ok", "Busy" or "Alert"

**self.message**

When values are received from the server, the values may have an optional message set. This attribute holds the last message received.

**self.message_timestamp**

If a message is received, this holds the UTC datetime of the message.

**self.devicename**

**self.user_string**

This is initially an empty string, but can be set by your code to any string you like.

**self.timestamp**

A UTC datetime object, updated from the server as values are received.

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
   :members: send_newSwitchVector

As well as the common attributes, the switch vector has a rule attribute.

**self.rule**

Applicable to Switch Vectors only, in which case it will be one of "OneOfMany", "AtMostOne" or "AnyOfMany".

For example, if the attribute is "OneOfMany", of the members of this vector, one, and only one can be "On".

----

.. autoclass:: indipyclient.propertyvectors.LightVector

----

.. autoclass:: indipyclient.propertyvectors.TextVector
   :members: send_newTextVector

----

.. autoclass:: indipyclient.propertyvectors.NumberVector
   :members: getfloatvalue, getformattedvalue, send_newNumberVector

Note the 'SnapNumberVector' object returned by the snapshot method also has the getfloatvalue and get formattedvalue methods.

----

.. autoclass:: indipyclient.propertyvectors.BLOBVector
   :members: send_newBLOBVector
