Introduction
============


This is under development and not yet ready for use

indipyclient
^^^^^^^^^^^^

This is a pure python package, with no dependencies, providing a set of classes which can be used to create an INDI client. Either a script, or a GUI implementation could use this to generate the INDI protocol XML, and to create the connection to a port serving INDI drivers.

This is a companion package to 'indipydriver' which can be used to create INDI drivers.

INDI - Instrument Neutral Distributed Interface.

For further information on INDI, see :ref:`references`.

The INDI protocol is defined so that drivers should operate with any INDI client.

The protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object) and the client can send commands to control the instrument.  The client can be general purpose, taking the format of switches, numbers etc., from the protocol.

INDI is often used with astronomical instruments, but is a general purpose protocol which can be used for any instrument control providing drivers are available.

The IPyClient object created listens to the data sent from drivers, and creates 'device' objects, each of which contains 'vector' objects, such as a SwitchVector or LightVector. These Vector objects can contain one or more 'members', such as a number of 'switches', or a number of 'lights' and their values.

The package can be installed from:

https://pypi.org/project/indipyclient

Typically you would create a subclass of IPyClient.

The class has methods which should be overwritten.

async def rxevent(self, event)

This is called whenever data is received, typically describing an instrument parameter. The event object describes the received data, and you provide the code which then typically displays the data.

async def control(self)

This should be a contuously running coroutine which you can use to run your own functions, or monitor your user input, and if required send updates to the drivers and instruments.

Having created an instance of your IPyClient subclass, you would run the client using:

asyncio.run(client.asyncrun())


Issues
^^^^^^

When transmitting or receiving BLOBS the entire BLOB is loaded into memory, which may cause issues if the BLOB is large. It is suggested that very large binary objects should be transferred by some other method.
