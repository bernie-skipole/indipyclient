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

**Attributes**

The attributes of the device object are:

**self.devicename**

**self.messages**

This is a collections.deque of item tuples (Timestamp, message).

Where the messages are received from the INDI server and are associated with the device. The deque has a maxlen=8 value set, and so only the last eight messages will be available.

Note, messages are added with 'appendleft' so the newest message is messages[0] and the oldest message is messages[-1] or can be obtained with .pop()

If you use the ipyclient.snapshot method to create a snapshot, the snapshot device will have attribute messages which will be this deque cast as a list.

**self.enable**

This will normally be True, but will become False if the INDI server sends a request to delete the device.
