

import os, sys, collections, threading, asyncio, pathlib

from time import sleep

from datetime import datetime

import xml.etree.ElementTree as ET

from . import events

from .error import ParseException, reporterror


# All xml data received from the driver should be contained in one of the following tags
TAGS = (b'message',
        b'delProperty',
        b'defSwitchVector',
        b'setSwitchVector',
        b'defLightVector',
        b'setLightVector',
        b'defTextVector',
        b'setTextVector',
        b'defNumberVector',
        b'setNumberVector',
        b'defBLOBVector',
        b'setBLOBVector'
       )

DEFTAGS = ( 'defSwitchVector',
            'defLightVector',
            'defTextVector',
            'defNumberVector',
            'defBLOBVector'
          )




# _STARTTAGS is a tuple of ( b'<defTextVector', ...  ) data received will be tested to start with such a starttag
_STARTTAGS = tuple(b'<' + tag for tag in TAGS)

# _ENDTAGS is a tuple of ( b'</defTextVector>', ...  ) data received will be tested to end with such an endtag
_ENDTAGS = tuple(b'</' + tag + b'>' for tag in TAGS)



def _makestart(element):
    "Given an xml element, returns a string of its start, including < tag attributes >"
    attriblist = ["<", element.tag]
    for key,value in element.attrib.items():
        attriblist.append(f" {key}=\"{value}\"")
    attriblist.append(">")
    return "".join(attriblist)


def blob_xml_bytes(xmldata):
    """A generator yielding blob xml byte strings
       for a newBLOBVector.
       reads member bytes, b64 encodes the data
       and yields the byte string including tags."""

    # yield initial newBLOBVector
    newblobvector = _makestart(xmldata)
    yield newblobvector.encode()
    for oneblob in xmldata.iter('oneBLOB'):
        bytescontent = oneblob.text
        size = oneblob.get("size")
        if size == "0":
            oneblob.set("size", str(len(bytescontent)))
        # yield start of oneblob
        start = _makestart(oneblob)
        yield start.encode()
        # yield body, b64 encoded, in chunks
        encoded_data = standard_b64encode(bytescontent)
        chunksize = 1000
        for b in range(0, len(encoded_data), chunksize):
            yield encoded_data[b:b+chunksize]
        yield b"</oneBLOB>"
    yield b"</newBLOBVector>\n"



class IPyClient(collections.UserDict):


    def __init__(self, blobfolder, indihost="localhost", indiport=7624, **clientdata):
        "An instance of this is a mapping of devicename to device object"
        self.blobfolder = blobfolder

        self.indihost = indihost
        self.indiport = indiport

        # dictionary of optional data
        self.clientdata = clientdata

        # create queue where client will put xml data to be transmitted
        self.writerque = asyncio.Queue(4)
        # and create readerque where received xmldata will be put
        self.readerque = asyncio.Queue(4)
        # self.data is a dictionary of devicename to device object
        self.data = {}
        # self.messages is a deque of "Timestamp space message"
        self.messages = collections.deque(maxlen=5)

        # self.connected is True if connection has been made
        self.connected = False



    async def _comms(self):
        "Create a connection to an INDI port"
        while True:
            try:
                # start by openning a connection
                reader, writer = await asyncio.open_connection(self.indihost, self.indiport)
                self.connected = True
                print(f"Connected to {self.indihost}:{self.indiport}")
                await asyncio.gather(self._run_tx(writer), self._run_rx(reader))
            except ConnectionRefusedError:
                reporterror(f"Connection refused on {self.indihost}:{self.indiport}, re-trying...")
            except asyncio.IncompleteReadError:
                reporterror(f"Connection failed on {self.indihost}:{self.indiport}, re-trying...")
            self.connected = False
            await asyncio.sleep(5)


    async def send(self, xmldata):
        "Transmits xmldata, this is an internal method, not normally called by a user."
        if self.connected:
            await self.writerque.put(xmldata)

    async def _run_tx(self, writer):
        "Monitors self.writerque and if it has data, uses writer to send it"
        while True:
            txdata = await self.writerque.get()
            if txdata.tag == "newBLOBVector" and len(txdata):
                # txdata is a newBLOBVector containing blobs
                # the generator blob_xml_bytes yields bytes
                for binarydata in blob_xml_bytes(txdata):
                    # Send to the port
                    writer.write(binarydata)
                    await writer.drain()
            else:
                # its straight xml, send it out on the port
                binarydata = ET.tostring(txdata)
                # Send to the port
                writer.write(binarydata)
                await writer.drain()
            self.writerque.task_done()


    async def _run_rx(self, reader):
        "pass xml.etree.ElementTree data to readerque"
        source = self._datasource(reader)
        while True:
            await asyncio.sleep(0)
            # get block of xml.etree.ElementTree data
            # from source and append it to  readerque
            rxdata = await anext(source)
            if rxdata is not None:
                # and place rxdata into readerque
                await self.readerque.put(rxdata)

    async def _datasource(self, reader):
        # get received data, parse it, and yield it as xml.etree.ElementTree object
        data_in = self._datainput(reader)
        message = b''
        messagetagnumber = None
        while True:
            await asyncio.sleep(0)
            # get blocks of data from _datainput
            data = await anext(data_in)
            if not data:
                continue
            if not message:
                # data is expected to start with <tag, first strip any newlines
                data = data.strip()
                for index, st in enumerate(_STARTTAGS):
                    if data.startswith(st):
                        messagetagnumber = index
                        break
                    elif st in data:
                        # remove any data prior to a starttag
                        positionofst = data.index(st)
                        data = data[positionofst:]
                        messagetagnumber = index
                        break
                else:
                    # data does not start with a recognised tag, so ignore it
                    # and continue waiting for a valid message start
                    continue
                # set this data into the received message
                message = data
                # either further children of this tag are coming, or maybe its a single tag ending in "/>"
                if message.endswith(b'/>'):
                    # the message is complete, handle message here
                    try:
                        root = ET.fromstring(message.decode("us-ascii"))
                    except Exception as e:
                        message = b''
                        messagetagnumber = None
                        continue
                    # xml datablock done, yield it up
                    yield root
                    # and start again, waiting for a new message
                    message = b''
                    messagetagnumber = None
                # and read either the next message, or the children of this tag
                continue
            # To reach this point, the message is in progress, with a messagetagnumber set
            # keep adding the received data to message, until an endtag is reached
            message += data
            if message.endswith(_ENDTAGS[messagetagnumber]):
                # the message is complete, handle message here
                try:
                    root = ET.fromstring(message.decode("us-ascii"))
                except Exception as e:
                    message = b''
                    messagetagnumber = None
                    continue
                # xml datablock done, yield it up
                yield root
                # and start again, waiting for a new message
                message = b''
                messagetagnumber = None


    async def _datainput(self, reader):
        "Generator producing binary string of data from the port"
        binarydata = b""
        while True:
            await asyncio.sleep(0)
            try:
                data = await reader.readuntil(separator=b'>')
            except asyncio.LimitOverrunError:
                data = await reader.read(n=32000)
            except Exception:
                binarydata = b""
                continue
            if not data:
                continue
            if b">" in data:
                binarydata = binarydata + data
                yield binarydata
                binarydata = b""
            else:
                # data has content but no > found
                binarydata += data
                # could put a max value here to stop this increasing indefinetly


    async def _rxhandler(self):
        """Populates the  events using data from self.readerque"""
        while True:
            # get block of data from the self.readerque
            await asyncio.sleep(0)
            root = await self.readerque.get()
            devicename = root.get("device")
            try:
                if devicename is None:
                    if root.tag == "message":
                        # state wide message
                        self.messages.appendleft( root.get("timestamp", datetime.utcnow().isoformat()) )
                        # create event
                        event = events.message(root)
                    else:
                        # if no devicename and not message, do nothing
                        self.readerque.task_done()
                        continue
                elif devicename in self:
                    # device is known about
                    device = self[devicename]
                    event = device.rxvector(root)
                elif root.tag in DEFTAGS:
                    # device not known, but a def is received
                    newdevice = _Device(devicename, self)
                    event = newdevice.rxvector(root)
                    # no error has occurred, so add this device to self.data
                    self[devicename] = newdevice
                else:
                    # device not known, not a def, so ignore it
                    self.readerque.task_done()
                    continue
                # give a script the chance to handle the event
                await self.rxevent(event)
            except ParseException as pe:
                # if an EventException is raised, it is because received data is malformed
                # so print to stderr and continue
                reporterror(str(pe))
            self.readerque.task_done()


    async def send_getProperties(self, devicename=None, vectorname=None):
        """Sends a getProperties request."""
        xmldata = ET.Element('getProperties')
        xmldata.set("version", "1.7")
        if devicename is None:
            await self.send(xmldata)
            return
        xmldata.set("device", devicename)
        if vectorname is None:
            await self.send(xmldata)
            return
        xmldata.set("name", vectorname)
        await self.send(xmldata)


    async def _check_connection(self):
        "check if connection available, clear data if not"
        while True:
            if not self.connected:
                if len(self):
                    # clear devices etc
                    self.clear()
                if not self.writerque.empty():
                    # empty the queue
                    while not self.writerque.empty():
                        xmldata = self.writerque.get_nowait()
                        self.writerque.task_done()
                if not self.readerque.empty():
                    # empty the queue
                    while not self.readerque.empty():
                        xmldata = self.readerque.get_nowait()
                        self.readerque.task_done()
                await asyncio.sleep(2)
                continue
            if not len(self):
                # no devices, so send a getProperties
                await self.send_getProperties()
                # wait for a response
                await asyncio.sleep(5)
                continue
            # so this point is reached if the client is connected
            # and has received properties
            await asyncio.sleep(0)


    async def rxevent(self, event):
        """Override this if this client is operating a script to act on received data.
           On receiving data, this is called, and should handle any necessary actions.
           event is an object with attributes according to the data received."""
        pass


    async def control(self):
        """Override this to operate your own scripts, and transmit updates"""
        while True:
            await asyncio.sleep(0)



    async def asyncrun(self):
        """Gathers tasks to be run simultaneously"""
        await asyncio.gather(self._comms(),            # Create a connection to an INDI port, and parse data
                             self._check_connection(), # check if connection available, clear data if not
                             self.control(),           # task to operate client algorithms, and transmit updates
                             self._rxhandler()         # task to handle incoming received data
                            )




class _Device(collections.UserDict):

    """An instance of this should be created for each device.
    """

    def __init__(self, devicename, client):
        super().__init__()

        # This device name
        self.devicename = devicename

        # and the device has a reference to its client
        self._client = client

        # if self.enable is False, this device has been 'deleted'
        self.enable = True

        # this is a dictionary of property name to propertyvector this device owns
        self.data = {}


    def rxvector(self, root):
        """Handle received data, sets new propertyvector into self.data,
           or updates existing property vector and returns an event"""
        if not self.enable:
            raise ParseException
        if root.tag == "delProperty":
            return events.delProperty(root, self._client)
        elif root.tag == "defSwitchVector":
            return events.defSwitchVector(root, self, self._client)
        elif root.tag == "setSwitchVector":
            return events.setSwitchVector(root, self, self._client)
        elif root.tag == "defLightVector":
            return events.defLightVector(root, self, self._client)
        elif root.tag == "setLightVector":
            return events.setLightVector(root, self, self._client)
        elif root.tag == "defTextVector":
            return events.defTextVector(root, self, self._client)
        elif root.tag == "setTextVector":
            return events.setTextVector(root, self, self._client)
        elif root.tag == "defNumberVector":
            return events.defNumberVector(root, self, self._client)
        elif root.tag == "setNumberVector":
            return events.setNumberVector(root, self, self._client)
        elif root.tag == "defBLOBVector":
            return events.defBLOBVector(root, self, self._client)
        elif root.tag == "setBLOBVector":
            return events.setBLOBVector(root, self, self._client)
        else:
            raise ParseException
