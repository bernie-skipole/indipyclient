Members
=======

Instances of these classes are created automatically as data is received
from the INDI server.

Each vector contains one or more members, the member value can be obtained from:

vector[membername]

For a SwitchMember, the value would be "On" of "Off".

The member object can be obtained from the method:

vector.member(membername)

For a SwitchMember, the member object would be an instance of the SwitchMember class as defined below.

You should never need to instantiate these classes yourself.

----

.. autoclass:: indipyclient.propertymembers.SwitchMember

**Attributes**

**self.name**

**self.label**

**self.user_string**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.LightMember

**Attributes**

**self.name**

**self.label**

**self.user_string**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.TextMember

**Attributes**

**self.name**

**self.label**

**self.user_string**

**self.membervalue**

----

.. autoclass:: indipyclient.propertymembers.NumberMember
   :members: getfloatvalue, getfloat, getformattedvalue, getformattedstring

**Attributes**

**self.name**

**self.label**

**self.user_string**

**self.membervalue**

A string value of the number taken from the XML protocol

**self.format**

A string defining the format, specified in the INDI protocol, this is used by the above methods to create the formatted value string.

**self.min**

The minimum value

**self.max**

The maximum, if min is equal to max, the client should ignore these.

**self.step**

step is incremental step values, set to a string of zero if not used.

These values, and self.membervalue are strings taken from the XML protocol. The getfloatvalue and getfloat methods can be used to parse these values to floats.

----

.. autoclass:: indipyclient.propertymembers.BLOBMember

**Attributes**

**self.name**

**self.label**

**self.user_string**

**self.filename**

A filename is set here if the client has a BLOBfolder set, and a received file has been saved. It is therefore the file name of the last file received.

**self.membervalue**

A Bytes value of the received BLOB.

**self.blobsize**

blobsize is an integer, the size of the BLOB before any compression.

**self.blobformat**

blobformat should be a string describing the BLOB, such as '.jpeg'

----

To summarise:

Your IPyClient object is a mapping of device name to devices, you have:

device = ipyclient[devicename]

Devices are mappings of vectors:

vector = ipyclient[devicename][vectorname]

Vectors are mappings of member values:

value = ipyclient[devicename][vectorname][membername]

The objects defined by classes SwitchMember, LightMember, TextMember, NumberMember and BLOBMember are available via the vector member() and members() methods:

vector[membername] returns the value

vector.members() returns a dictionary of membername:memberobject

vector.member(membername) returns a member object

To illustrate this, the following example connects to a server, and prints devices, vectors and member values::


    """Connects to server, listens 5 seconds, prints properties, shuts down"""

    import asyncio
    from indipyclient import IPyClient

    async def main():
        "Print all devices, vectors and values then shut down"

        # get an instance of IPyClient, which, using its default
        # values, will connect to a server running on localhost
        client = IPyClient()

        # run the client.asyncrun() method to start the connection
        # and obtain values from the server
        client_task = asyncio.create_task(client.asyncrun())

        # after starting, wait 5 seconds for devices to be learnt
        # by the client
        await asyncio.sleep(5)

        for devicename, device in client.items():
            print(f"Device : {devicename}")
            for vectorname, vector in device.items():
                print(f"  Vector : {vectorname}")
                for membername, value in vector.items():
                    print(f"    Member : {membername} Value : {value}")

        # request a shutdown
        client.shutdown()

        # wait for the shutdown
        await client_task

    asyncio.run( main() )


For the thermostat server example this outputs::

    Device : Thermostat
      Vector : temperaturevector
        Member : temperature Value : 19.60
      Vector : targetvector
        Member : target Value : 15.00
