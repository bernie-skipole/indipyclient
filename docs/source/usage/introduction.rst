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

Using pip, the package can be installed from:

https://pypi.org/project/indipyclient

I would suggest (on debian derivatives) that you should start with::

    sudo apt-get install python3-venv python3-setuptools python3-pip python3-wheel

Then create a virtual environment, and use pip to install indipyclient, if you need further information on pip and virtual environments, try:

https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/

Once installed you would typically create a subclass of IPyClient to handle the received data, and which automatically creates devices, vectors and their members.

The class has a rxevent method which can be overwritten.

async def rxevent(self, event)

This is called whenever data is received, typically describing an instrument parameter. The event object describes the received data, and you provide any code which, if required, responds to the received data.

You would also create your own coroutines to read the client attributes and display them if a GUI client is being created, or to act on them appropriately if you are creating a script to control the instrument. Your coroutine would usually take the IPyClient subclass instance as an argument, so you could use its attributes and methods to read the received vector values, and transmit new values.

Having created an instance of your IPyClient subclass (ie MyClient), and your own co-routines you would typically run them using something like::

    async def main():

        client = MyClient(indihost="localhost", indiport=7624)
        t1 = client.asyncrun()          # runs the client which connects to the indi service
        t2 = control(client)            # assuming your own co-routine is called 'control'
        await asyncio.gather(t1, t2)


    asyncio.run(main())



Issues
^^^^^^

When transmitting or receiving BLOBS the entire BLOB is loaded into memory, which may cause issues if the BLOB is large. It is suggested that very large binary objects should be transferred by some other method.
