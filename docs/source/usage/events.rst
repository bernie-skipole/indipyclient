Events
======

As received data arrives from the server, events are raised. These events are automatically used to create the Devices, Vectors and Members that describe the device properties. You do not have to instantiate any of the event classes described here, they are created automatically as data is received.

Also the IPyClient rxevent(event) coroutine method is called. As default this does nothing, consisting merely of the pass command. You can create your own class, inheriting from IPyClient and override this method, if you wish to act on the event received.

Events are of different types, which initially define a vector, and then set existing vector values.  These event objects are described here, you could inspect the event type, and depending on its devicename, vectorname you can obtain the vector from the IPyClient mapping, and inspect its attributes. You would also typically call the vector methods to transmit new values to the server.
