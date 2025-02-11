Devices
=======

Normally you will never create any instances of a Device class, they are created automatically as the server informs the client of their existence via the INDI protocol.

So for example, you will have your IPyClient object, and as it is a mapping of device name to devices, you have:

device = ipyclient[devicename]

Devices are mappings of vectors:

vector = ipyclient[devicename][vectorname]

Vectors are mappings of member values:

value = ipyclient[devicename][vectorname][membername]

These mappings obey dictionary methods allowing you to iterate over items, keys and values.

.. autoclass:: indipyclient.ipyclient.Device
   :members: snapshot

**Attributes**

The attributes of the device object are:

**self.devicename**

**self.user_string**

This is initially an empty string, but can be set by your code to any string you like.

**self.messages**

This is a collections.deque of item tuples (Timestamp, message).

Where the messages are received from the INDI server and are associated with the device. The deque has a maxlen=8 value set, and so only the last eight messages will be available.

Note, messages are added with 'appendleft' so the newest message is messages[0] and the oldest message is messages[-1] or can be obtained with .pop()

**self.enable**

This will normally be True, but will become False if the INDI server sends a request to delete the device.


Device Snapshot
===============

The snapshot() method of the device returns a SnapDevice object which is a copy of the state of the device and vectors. This could be used if you wish to pass this state to your own routines, perhaps to record values in another thread without danger of them being updated.

The snapshot is a mapping of vector name to snapshot copies of vectors, but without the methods to send vector updates.

.. autoclass:: indipyclient.ipyclient.SnapDevice
   :members:

The dumps and dump methods can be used to create JSON records of the device state.

The SnapDevice object has attributes, which are copies of the Device attributes.

**self.devicename**

**self.user_string**

**self.messages**

The messages attribute is cast as a list rather than a collections.deque. It is the messages at the point the snapshot is taken, it does not update.

**self.enable**

True if any vector of this device has enable True, otherwise False if the device has been deleted. This does not update.
