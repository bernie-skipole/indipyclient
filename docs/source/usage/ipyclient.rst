IPyClient
=========

As well as running the terminal client, indipyclient can be imported which gives access to a number of classes and methods which can be used by your own program to send and receive data to remote INDI servers. This enables you to write your own scripts to control remote instruments, or helps you create your own client program.

Typically you would import the class IPyClient, and overide its rxevent(event) method, which is an awaitable coroutine.

rxevent(event) is automatically called whenever data is received, and the event will be of a type which can be tested, and attributes read to handle the data received.

As devices and vectors are learnt from the received data, the IPyClient object becomes a mapping of devicename to device objects, which in turn are mappings to vectors and values. It also has a send_newVector method which can be used by your own code to send data to the remote instrument.

The IPyClient object has an asyncrun() coroutine method which needs to run in an event loop, typically gathered with your own tasks, to run your script or client.

The rest of this documentation details the classes, methods and attributes available.


.. autoclass:: indipyclient.IPyClient
   :members:
   :exclude-members: level, logfile, logfp

**Attributes**

Attributes of the IPyClient object are:

**self.indihost**

The host as given in the class argument.

**self.indiport**

The port as given in the class argument.

**self.clientdata**

Dictionary of any named arguments.

**self.connected**

True if a connection has been made.

**self.stopped**

True when asyncrun is finished.

**self.level**

Read only attribute, set via setlogging method.

**self.logfile**

Read only attribute, set via setlogging method.

**self.logfp**

Read only attribute, set via setlogging method.

The IPyClient object is also mapping of device name to device object. These Device objects are automatically created as data comes from the INDI server.


