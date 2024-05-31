Events
======

As received data arrives from the server, events are raised. These events are automatically used to create the Devices, Vectors and Members that describe the device properties.

After setting any new values into the Vectors and members, the IPyClient rxevent(event) coroutine method is called. As default this does nothing, consisting merely of the pass command. If you wish to act on the event received you could create your own class, inheriting from IPyClient and override this method,

Events are of different types, which initially define a vector, and then set existing vector values.  These event objects are described here.

You should never need to instantiate these classes yourself.

The classes can be imported directly from the indipyclient module, which may be needed if you are checking the event class using isinstance, or pattern matching.

----

.. autoclass:: indipyclient.events.VectorTimeOut


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.timestamp**

This is created by datetime.now(tz=timezone.utc)

**self.eventtype**

Set to the string "TimeOut".

----

.. autoclass:: indipyclient.events.Message


**Attributes**

**self.device**

Could be None if this is a global message from the server not assigned to a device

**self.devicename**

Could be None

**self.vectorname**

Always None, as this message is either a global message or only associated with a device

**self.root**

An xml.etree.ElementTree object of the received xml data.

**self.timestamp**

**self.message**

If self.device is None, the tuple (self.timestamp, self.message) is appended to the IPyClient messages deque.

If self.device is given, the tuple is appended to the device messages deque.

**self.eventtype**

Set to the string "Message".

----

.. autoclass:: indipyclient.events.getProperties

The getProperties request is normally sent from the client to Drivers, and so is not normally received by a client. However one driver can snoop on another by transmitting a getProperties, which may therefore be received here. Usually it should be ignored by a client.

**Attributes**

**self.device**

Could be None

**self.devicename**

Could be None

**self.vectorname**

Could be None

**self.root**

An xml.etree.ElementTree object of the received xml data.

**self.timestamp**

**self.eventtype**

Set to the string "getProperties".

----

.. autoclass:: indipyclient.events.delProperty


**Attributes**

**self.device**

**self.devicename**

**self.vectorname**

Could be None, to indicate the whole device is deleted.

**self.root**

An xml.etree.ElementTree object of the received xml data.

**self.timestamp**

**self.message**

**self.eventtype**

Set to the string "Delete".

----

.. autoclass:: indipyclient.events.defSwitchVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.rule**

One of 'OneOfMany', 'AtMostOne', 'AnyOfMany'

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being label

**self.eventtype**

Set to the string "Define".

----

.. autoclass:: indipyclient.events.defTextVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being label

**self.eventtype**

Set to the string "Define".

----

.. autoclass:: indipyclient.events.defNumberVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being a tuple of (label, format, min, max, step).

**self.eventtype**

Set to the string "Define".

----

.. autoclass:: indipyclient.events.defLightVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.label**

**self.group**

**self.state**

**self.memberlabels**

Dictionary with key member name and value being label

**self.eventtype**

Set to the string "Define".

----

.. autoclass:: indipyclient.events.defBLOBVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being label

**self.eventtype**

Set to the string "DefineBLOB".

----

.. autoclass:: indipyclient.events.setSwitchVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.state**

**self.timeout**

This could be None if no timeout information is included, in which case the existing timeout is not altered.

**self.eventtype**

Set to the string "Set".

----

.. autoclass:: indipyclient.events.setTextVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.state**

**self.timeout**

This could be None if no timeout information is included, in which case the existing timeout is not altered.

**self.eventtype**

Set to the string "Set".

----

.. autoclass:: indipyclient.events.setNumberVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.state**

**self.timeout**

This could be None if no timeout information is included, in which case the existing timeout is not altered.

**self.eventtype**

Set to the string "Set".

----

.. autoclass:: indipyclient.events.setLightVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.state**

**self.timeout**

This is None.

**self.eventtype**

Set to the string "Set".

----

.. autoclass:: indipyclient.events.setBLOBVector


**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.root**

**self.timestamp**

**self.message**

**self.state**

**self.sizeformat**

A dictionary of membername to tuple (membersize, memberformat)

**self.timeout**

This could be None if no timeout information is included, in which case the existing timeout is not altered.

**self.eventtype**

Set to the string "SetBLOB".
