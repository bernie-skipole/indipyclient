Events
======

As received data arrives from the server, events are raised. These events are automatically used to create the Devices, Vectors and Members that describe the device properties.

Also the IPyClient rxevent(event) coroutine method is called. As default this does nothing, consisting merely of the pass command. You can create your own class, inheriting from IPyClient and override this method, if you wish to act on the event received.

Events are of different types, which initially define a vector, and then set existing vector values.  These event objects are described here, you could inspect the event type, and depending on its devicename, vectorname you can obtain the vector from the IPyClient mapping, and inspect its attributes.

You should never need to instantiate these classes yourself.

The classes are defined in indipyclient.events

----

.. autoclass:: indipyclient.events.VectorTimeOut:

**Attributes**

**self.device**

**self.devicename**

**self.vector**

**self.vectorname**

**self.timestamp**

This is created by datetime.now(tz=timezone.utc)

----

.. autoclass:: indipyclient.events.Message:

**Attributes**

**self.device**

Could be None if this is a global message from the server not assigned to a device

**self.vectorname**

Could be None if this message is not associated with a vector

**self.devicename**

Could be None

**self.root**

The root xml object

**self.timestamp**

**self.message**

----

.. autoclass:: indipyclient.events.delProperty


**Attributes**

**self.device**

**self.vectorname**

**self.devicename**

**self.root**

An xml.etree.ElementTree object of the received xml data.

**self.timestamp**

**self.message**

----

.. autoclass:: indipyclient.events.defSwitchVector

**Attributes**

**self.device**

**self.vectorname**

**self.devicename**

**self.root**

**self.timestamp**

**self.message**

**self.vector**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.rule**

One of 'OneOfMany', 'AtMostOne', 'AnyOfMany'

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being label

----

.. autoclass:: indipyclient.events.defTextVector

**Attributes**

**self.device**

**self.vectorname**

**self.devicename**

**self.root**

**self.timestamp**

**self.message**

**self.vector**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being label

----

.. autoclass:: indipyclient.events.defNumberVector

**Attributes**

**self.device**

**self.vectorname**

**self.devicename**

**self.root**

**self.timestamp**

**self.message**

**self.vector**

**self.label**

**self.group**

**self.state**

**self.perm**

**self.timeout**

**self.memberlabels**

Dictionary with key member name and value being a tuple of (label, format, min, max, step).
