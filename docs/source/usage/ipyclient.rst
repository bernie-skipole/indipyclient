IPyClient
=========

As well as running the terminal client, indipyclient can be imported which gives access to a number of classes and methods which can be used by your own program to send and receive data to remote INDI servers. This enables you to write your own scripts to control remote instruments, or helps you create your own client program.

Typically you would import the class IPyClient, and overide its rxevent(event) method, which is an awaitable coroutine.

rxevent(event) is automatically called whenever data is received, and the event will be of a type which can be tested, and attributes read to handle the data received.

As devices and vectors are learnt from the received data, the IPyClient object becomes a mapping of devicename to device objects, which in turn are mappings to vectors and values. It also has a send_newVector method which can be used by your own code to send data to the remote instrument.

The IPyClient object has an asyncrun() coroutine method which needs to run in an event loop, typically gathered with your own tasks, to run your script or client.

IPyClient has a 'hardware' coroutine method which is started with asyncrun, but as default does nothing. It is available to be overidden if required, for example, if data is to be sent to the remote instrument every ten seconds::

    async def hardware(self):
        while not self._stop:
            await asyncio.sleep(10)
            datavalue = my_function() # your own function which obtains data
            self.send_newVector("devicename", "vectorname", members={"membername":datavalue}):

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

**self.connected**

True if a connection has been made.

**self.stopped**

True when asyncrun is finished.

**self.messages**

This is a collections.deque of item tuples (Timestamp, message).

Where the messages are 'global' messages received from the INDI server, or by the report() coroutine method. They are not associated with a device which has its own messages attribute. The deque has a maxlen=8 value set, and so only the last eight messages will be available.

Note, messages are added with 'appendleft' so the newest message is messages[0] and the oldest message is messages[-1] or can be obtained with .pop()

The IPyClient object is also mapping of device name to device object. These Device objects are automatically created as data comes from the INDI server.

Note that the set_vector_timeouts method enables the creation of VectorTimeOut events which are not part of the INDI standard which states:

*The Device will eventually send a state of Ok if and when the new values for the Property have been successfully accomplished according to the Devices criteria, or send back Alert if they can not be accomplished with a message explaining why.*

It also states:

*Timeout values give Clients a simple ability to detect dysfunctional Devices or broken communication...*

You have the option of handling timeouts however you prefer.

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
