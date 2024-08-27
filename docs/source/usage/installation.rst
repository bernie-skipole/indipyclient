Installation
============

indipyclient requires python 3.10 or later.

As the console uses the python standard library curses package, which is not available on Windows, indipyclient works on linux only.

The package is available on Pypi, it has no dependencies other than the Python standard library.

It can be installed, like any other package, into a virtual environment using pip, in which case, with the environment activated, it can be invoked with:

python -m indipyclient

As it is a command line program it can also be installed using tools such as pipx or uv.

For example

uv tools install indipyclient

Will install it, after which it can be run. Try:

indipyclient --help

To display the options.

Without any options the client will attempt to connect to localhost.

Or if you want to run it, without installing:

uv tools run indipyclient

This will pull indipyclient from Pypi and run it in a temporary virtual environment, pipx has a similar capability.

**Notes**

You could run the INDI service on one machine, and indipyclient on another if you specify the host and port to connect to. However a more secure method would be to run both on the same machine using the default localhost, and do not open the port to network connections.  You can still uses the terminal remotely, by calling the machine using SSH, and in the SSH session, open the client by running indipyclient.

You should note that indipyclient relies on the Python Curses standard library package, and this is not available on Windows, in which case using an SSH connection and running indipyclient on the server is the best option.

The Curses library depends on the terminal providing support for terminal control sequences, if your terminal program is not compatable you may find the layout distorted, or certain features such as selecting fields by mouse click not working. In which case, if possible, pick a different emulation.

**For Import**

If you are intending to import the indipyclient package to use the classes to create your own clients or scripts, you would typically install it into a virtual environment.

You can then import indipyclient, create a class inheriting from IPyClient, and typically write your own rxevent(event) coroutine method, which is called whenever data is received.

The IPyClient object gives you access to Devices, which represent the remote instrument and property Vectors, which are collections of one or more member values. For example a SwitchVector may hold a number of switches, such as a radio button set. The values of these vectors can be read, and updated values transmitted using methods described further in this documentation.

Finally the asyncrun() coroutine method of IPyClient should be awaited which will cause the connection to the INDI server to be made.

**Example**

This script monitors a remote "Thermostat" and prints the temperature as events are received from an INDI "Thermostat" driver. The driver is described as an example at https://indipydriver.readthedocs.io

The script checks for a setNumberVector event, and if the event matches the device, vector and member names, prints the received value. This continues indefinetly, printing the temperature as values are received::

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


As well as IPyClient, the function indipyclient.getfloat(value) is available which, given a string version of a number as described in the INDI specification, will return a float. This could be used in the above example to ensure value is a float.

.. autofunction:: indipyclient.getfloat
