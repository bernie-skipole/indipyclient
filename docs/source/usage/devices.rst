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

**self.enable**

This will normally be True, but will become False if the INDI server sends a request to delete the device.
