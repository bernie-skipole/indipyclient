Summary
=======

The following summarises how a client could be structured, describing the control of a simulated LED On or Off switch. The driver for this switch is described at:

https://indipydriver.readthedocs.io


In this example, the actual control is from a thread running a simple console 'input' command.


Your Class
^^^^^^^^^^

You would normally start by creating one or more classes or functions that control your hardware, for example::

    import asyncio

    from indipyclient import (IPyClient,
                              delProperty, defSwitchVector, defTextVector,
                              defNumberVector, defLightVector, defBLOBVector,
                              setSwitchVector, setTextVector, setNumberVector,
                              setLightVector, setBLOBVector)




