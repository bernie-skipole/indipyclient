Concept
=======

You may have Python programs reading or controlling external instruments, or GPIO pins or any form of data collection or control.

The package indipydriver consists of classes ipydriver and ipyserver which can be used to take your data, organise it into the xml data structure as defined by the INDI protocol, and serve it on a port.

The INDI protocol (Instrument Neutral Distributed Interface) specifies a limited number of ways the data can be presented, as switches, lights, text, numbers and BLOBs (Binary Large Objects), together with grouping and label values which may be useful to display the data.

An INDI client can then connect to this serving port, decode the protocol, and present the switches, lights etc., to the user or to any controlling or logging script required.

As the protocol contains the format of the data, a client could learn and present the controls when it connects. It could also be much simpler if it is written for a particular instrument, in which case the controls can be immediately set up, and present the data as it is received. 

This indipyclient package is an INDI client.

It provides a general purpose terminal client, which learns the devices and their controls as it connects. If using it for that purpose only, then simply run the program from the command line.

It also contains classes which make the connection, decode the protocol, and present the data as class attributes, and have methods which can transmit data.

The INDI Protocol
=================

The protocol is defined at:

https://www.clearskyinstitute.com/INDI/INDI.pdf

In general, a client transmits a 'getProperties' request (this indipyclient package does this for you on connecting).

The server replies with definition packets (defSwitchVector, defLightVector, .. ) that define the format of the instrument data.

The indipyclient package reads these, and its main IPyClient instance becomes a mapping of the devices, vectors and members.

For example:

ipyclient[devicename][vectorname][membername] will be the value of a particular parameter.

Multiple devices can be served, a 'vector' is a collection of members, so a switch vector may have one or more switches in it, to define a radio button set perhaps.

As the instrument produces changing values, the server sends 'set' packets, such as setSwitchVector, setLightVector ..., these contain new values, and are read and update the ipclient values. They also cause the ipclient.rxevent(event) method to be called, which you could overwrite to take any actions you prefer. The possible event objects are described within this documentation.

To transmit a new value you could call the ipyclient.send_newVector coroutine method, or if you have a vector object, you could call its specified send method, for example vector.send_newSwitchVector, these are called with the appropriate new member values.






