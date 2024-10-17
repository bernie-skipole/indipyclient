Concept
=======

You may have Python programs reading or controlling external instruments, or GPIO pins or any form of data collection or control.

The associated package 'indipydriver' can be used to take your data, organise it into a structure defined by the INDI protocol, and serve it on a port.

The INDI protocol (Instrument Neutral Distributed Interface) specifies a limited number of ways the data can be presented, as switches, lights, text, numbers and BLOBs (Binary Large Objects), together with grouping and label values which may be useful to display the data.

As the protocol contains the format of the data, a client could learn and present the controls when it connects. It could also be much simpler if it is written for a particular instrument, in which case the controls can be immediately set up, and present the data as it is received.

This 'indipyclient' package is an INDI client.

It provides a general purpose terminal client, which learns the devices and their controls. If using it for that purpose only, then simply run the program from the command line.

It also contains classes which make the connection, decode the protocol, and present the data as class attributes, and have methods which can transmit data.

Note: other INDI servers and clients are available. See :ref:`references`.

The INDI Protocol
-----------------

The protocol is defined at:

https://www.clearskyinstitute.com/INDI/INDI.pdf

In general, a client transmits a 'getProperties' request (this indipyclient package does this for you on connecting).

The server replies with definition packets (defSwitchVector, defLightVector, .. ) that define the format of the instrument data.

The indipyclient package reads these, and its main IPyClient instance becomes a mapping of the devices, vectors and members.

For example, if ipyclient is your instance of IPyClient:

ipyclient[devicename][vectorname][membername] will be the value of a particular parameter.

Multiple devices can be served, a 'vector' is a collection of members, so a switch vector may have one or more switches in it.

As the instrument produces changing values, the server sends 'set' packets, such as setSwitchVector, setLightVector ..., these contain new values, and are read and update the ipyclient values. They also cause the ipyclient.rxevent(event) method to be called, which you could overwrite to take any actions you prefer. The possible event objects are described within this documentation.

To transmit a new value you could call the ipyclient.send_newVector coroutine method, or if you have a vector object, you could call its specified send method, for example vector.send_newSwitchVector, these are called with the appropriate new member values.

Each vector has a state attribute, set to a string, one of "Idle", "Ok", "Busy" or "Alert".

When a send method is called, the vector's state is automatically set to "Busy", and when a 'set' packet is received, it will update the ipyclient values and also provide confirmation of the changed state by setting it to "Ok".

Timeouts
--------

Whenever you send updated values, a timer is started and if a timeout occurs before the server responds, a VectorTimeOut event will be created, which you could choose to ignore, or take action such as setting an Alert flag.

The INDI protocol allows the server to suggest a timeout for each vector. The ipyclient.set_vector_timeouts method allows you to set minimum and maximum timeouts which restricts the suggested values between a minimum and maximum value.

The method also has a timeout_enable argument which enables or disables the VectorTimeOut event and also enables two other timers:

ipyclient.idle_timeout is set to twice timeout_max, and will cause a getProperties to be sent if nothing is either transmitted or received in that time.

ipyclient.respond_timeout is set to four times timeout_max, and will assume a call failure and attempt a reconnect, if after any transmission, nothing is received for that time.

If the timeout_enable argument is set to False, then these timeouts are disabled, and you have the freedom to implement any of your own timing controls.

The INDI standard states:

*The Device will eventually send a state of Ok if and when the new values for the Property have been successfully accomplished according to the Devices criteria, or send back Alert if they can not be accomplished with a message explaining why.*

Note 'Property' and 'Vector' are interchangeable terms. The spec also states:

*Timeout values give Clients a simple ability to detect dysfunctional Devices or broken communication...*

You have the option of handling timeouts however you prefer.

BLOBs
-----

When a client first connects, the server assumes that transmitting BLOBs to the client is disabled. To enable BLOB's the client must transmit an enableBLOB command.

The IPyClient object has the following method:

async def send_enableBLOB(self, value, devicename, vectorname=None)

The devicename must be specified, but if the vectorname is not, the command applies to all BLOBs from that device.

If devicename and vectorname are both specified, the command applies to that particular vector.

The value must be one of:

**Never**

This disables BLOBs.

**Also**

This enables BLOBs, which will be sent together with any other vectors generated by the driver.

**Only**

This enables BLOBs, but disallows any other vectors, so the connection is dedicated to BLOBs only.

So if you wish to receive BLOBs amongst other vectors for every device, then for every device you need to await ipyclient.send_enableBLOB("Also", devicename)

Asynchronous operation
----------------------

The indipyclient classes send and receive data asynchronously, and the ipyclient.asyncrun() coroutine method, when awaited, causes the client to make its call and run.

The asyncrun method could be gathered together with any of your own coroutines, or could be called with the asyncio.run() call.

If your own code is blocking, then you will probably need to await ipyclient.asyncrun() in another thread, a common method would be to introduce queues to pass data between threads. To help with this, IPyClient has a snapshot() method which returns a copy of the state of the client, with devices, vectors and members, but without the methods to send or update data. This snapshot could be passed to other threads providing them with the current client information. See :ref:`queclient`.


Example
-------

This script monitors a remote "Thermostat" and prints the temperature as events are received. The thermostat driver is described as an example at https://indipydriver.readthedocs.io

The script checks for a setNumberVector event, and if the event matches the device, vector and member names, prints the received value. This continues indefinitely, printing the temperature as values are received::

    import asyncio
    import indipyclient as ipc

    class MyClient(ipc.IPyClient):

        async def rxevent(self, event):
            "Prints the temperature as it is received"
            if isinstance(event, ipc.setNumberVector):
                if event.devicename != "Thermostat":
                    return
                if event.vectorname != "temperaturevector":
                    return
                # use dictionary get method which returns None
                # if this member name is not present in the event
                value = event.get("temperature")
                if value:
                    print(value)

    myclient = MyClient()

    asyncio.run(myclient.asyncrun())


As well as IPyClient, the function getfloat(value) is available which, given a string version of a number as described in the INDI specification, will return a float. This could be used in the above example to ensure value is a float.

.. autofunction:: indipyclient.getfloat


Logging
-------

This indipyclient package uses the Python standard library logging module, it uses logger with name "indipyclient" and emits logs at levels:

**ERROR**

Logs errors including tracebacks from exceptions

**WARNING**

Logs connection status and warnings

**INFO**

Logs informational messages.

**DEBUG**

Logs xml data transmitted and received. The verbosity of this xml data can be set with the IPyClient.debug_verbosity(verbose) method, where 0 is no xml traffic is recorded, 1 is xml recorded but the least verbose, and 3 is the most.

To record logs you will need to add a handler, and a logging level, for example::

    import logging
    logger = logging.getLogger('indipyclient')

    fh = logging.FileHandler("logfile.log")
    logger.addHandler(fh)

    logger.setLevel(logging.DEBUG)

This leaves you with the flexibility to add any available loghandler, and to set your own formats if required.

As default, logs at level WARNING and above will appear on your console, which may be distracting. You could add a NullHandler to the start of your script if you do not want any output to be displayed::

    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.NullHandler())
