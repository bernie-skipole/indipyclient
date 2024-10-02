IPyClient
=========

Importing indipyclient gives access to a number of classes and methods which can be used by your own program to send and receive data to remote instruments. This enables you to write your own controlling scripts, or helps you create your own client program.

Typically you would import the class IPyClient, and overide its rxevent(event) method, which is an awaitable coroutine.

rxevent(event) is automatically called whenever data is received, and the event will be of a type which can be tested, and attributes read to handle the data received.

As devices and vectors are learnt from the received data, the IPyClient object becomes a mapping of devicename to device objects, which in turn are mappings to vectors and values. It also has a send_newVector coroutine method which can be used by your own code to send data to the remote instrument.

The IPyClient object has an asyncrun() coroutine method which needs to run in an event loop, typically gathered with your own tasks, to run your script or client.

IPyClient has a 'hardware' coroutine method which is started with the IPyClient.asyncrun method, but as default does nothing. It is available to be overidden if required, for example, if data is to be sent to the remote instrument every ten seconds::

    async def hardware(self):
        while not self._stop:
            await asyncio.sleep(10)
            datavalue = my_function() # your own function which obtains data
            await self.send_newVector("devicename", "vectorname", members={"membername":datavalue})

Note that attribute self._stop becomes True when the method shutdown() is called, requesting any coroutines to stop.

The rest of this documentation details the classes, methods and attributes available.


.. autoclass:: indipyclient.IPyClient
   :members:


**Attributes**

Attributes of the IPyClient object are:

**self.indihost**

The host as given in the class argument.

**self.indiport**

The port as given in the class argument.

**self.clientdata**

Dictionary of any named arguments.

**self.enable_reports**

If True, then INFO logs, and any message set into the report method will be injected into the client as a received message, and hence will be shown on the terminal messages window. As default this is True.

**self.connected**

True if a connection has been made.

**self.stopped**

This is an asyncio.Event object, which is set when asyncrun is finished.

awaiting self.stopped.wait() will wait until the client has shutdown. This could be used to clear up after a client has closed.

**self.messages**

This is a collections.deque of item tuples (Timestamp, message).

Where the messages are 'global' messages received from the INDI server, or by the report() coroutine method. They are not associated with a device which has its own messages attribute. The deque has a maxlen=8 value set, and so only the last eight messages will be available.

Note, messages are added with 'appendleft' so the newest message is messages[0] and the oldest message is messages[-1] or can be obtained with .pop()


Logging
=======

This indipyclient package uses the Python standard library logging module, it uses logger with name "indipyclient" and emits logs at levels:

**ERROR**

Logs errors including tracebacks from exceptions

**INFO**

Logs informational messages and error messages as above.

**DEBUG**

Logs xml data transmitted and received, and the info and error messages as above. The verbosity of this xml data can be set with the IPyClient.debug_verbosity(verbose) method, where 0 is no xml traffic is recorded, 1 is xml recorded but the least verbose, and 3 is the most.

To create logs you will need to add a handler, and a logging level, for example::

    import logging
    logger = logging.getLogger('indipyclient')

    fh = logging.FileHandler("logfile.log")
    logger.addHandler(fh)

    logger.setLevel(logging.DEBUG)

This leaves you with the flexibility to add any available loghandler, and to set your own formats if required.


Client Snapshot
===============

The snapshot() method of IPyClient returns a Snap object which is a copy of the state of the client, devices etc.. This could be used if you wish to pass this state to your own routines, perhaps to record values in another thread without danger of them being updated.

The snapshot is a mapping of devicename to snapshot copies of devices and vectors, without any coroutine methods, so cannot be used to send vector updates. You would never instantiate this class yourself, but would ceate it by calling the snapshot method of IPyClient.

.. autoclass:: indipyclient.ipyclient.Snap
   :members:

The dumps and dump methods can be used to create JSON records of the client state. The JSON record does not include BLOB values, they are set as null.

The Snap object has attributes, which are copies of the IPyClient attributes.

**self.indihost**

**self.indiport**

**self.connected**

This is the connected value at the point the snapshot is taken, it does not update.

**self.messages**

The messages attribute is cast as a list rather than a collections.deque. It is the messages at the point the snapshot is taken, it does not update.
