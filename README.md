# indipyclient

You may have Python programs implementing some form of data collection or control and wish to remotely operate such an instrument.

This indipyclient package provides a set of classes which can be used to create scripts to control or display the remote instrument. In particular your script can import and create an instance of the 'IPyClient' class.

An associated package 'indipydriver' can be used to take your data, organise it into a data structure defined by the INDI protocol, and serve it on a port, ready for this client to connect to.

INDI - Instrument Neutral Distributed Interface.

See https://en.wikipedia.org/wiki/Instrument_Neutral_Distributed_Interface

INDI is often used with astronomical instruments, but is a general purpose protocol which can be used for any instrument control.

The INDI protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object). The client takes the format of switches, numbers etc., from the protocol.

The IPyClient object has an asyncrun() coroutine method which needs to be awaited, typically gathered with your own tasks. The client transmits a 'getProperties' request (this indipyclient package does this for you on connecting).

The server replies with definition packets (defSwitchVector, defLightVector, .. ) that define the format of the instrument data.

The indipyclient package reads these, and its IPyClient instance becomes a mapping of the devices, vectors and members.

For example, if ipyclient is your instance of IPyClient:

ipyclient[devicename][vectorname][membername] will be the value of a particular parameter.

Multiple devices can be served, a 'vector' is a collection of members, so a switch vector may have one or more switches in it.

As the instrument produces changing values, the server sends 'set' packets, such as setSwitchVector, setLightVector ..., these contain new values, which update the ipyclient values. They also cause the ipyclient.rxevent(event) method to be called, which you could overwrite to take any actions you prefer.

To transmit a new value you could call the ipyclient.send_newVector coroutine method.

Indipyclient can be installed from Pypi with:

    pip install indipyclient

Further documentation is available at:

https://indipyclient.readthedocs.io

The package can be installed from:

https://pypi.org/project/indipyclient

and indipydriver is available at:

https://pypi.org/project/indipydriver

https://github.com/bernie-skipole/indipydriver

A terminal client 'indipyterm' is available, which itself calls on indipyclient to do the heavy lifting, and uses the textual package to present terminal characters, this is available at:

https://pypi.org/project/indipyterm

https://github.com/bernie-skipole/indipyterm
