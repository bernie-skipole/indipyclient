

import os, sys, collections, threading, asyncio, pathlib, time, traceback, copy

from time import sleep

from datetime import datetime, timezone

from base64 import standard_b64encode

import xml.etree.ElementTree as ET

from . import events

from .error import ParseException, ConnectionTimeOut


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


    def __init__(self, indihost="localhost", indiport=7624, **clientdata):
        "An instance of this is a mapping of devicename to device object"

        self.indihost = indihost
        self.indiport = indiport

        # dictionary of optional data
        self.clientdata = clientdata

        # create queue where client will put xml data to be transmitted
        self.writerque = collections.deque()

        # and create readerque where received xmldata will be put
        self.readerque = asyncio.Queue(4)
        # self.data is a dictionary of devicename to device object
        self.data = {}
        # self.messages is a deque of "Timestamp space message"
        self.messages = collections.deque(maxlen=8)

        # note, messages are added with 'appendleft'
        # so newest message is messages[0]
        # oldest message is messages[-1] or can be obtained with .pop()

        # self.connected is True if connection has been made
        self.connected = False

        # tx_timer is set when data is transmitted, it is used to check when data is received,
        # at which point it becomes None again.
        # if there is no answer after self.respond_timeout seconds, close connection
        self.tx_timer = None
        self.respond_timeout = 15
        # idle_timer is set when either data is transmitted or received.
        # If nothing sent or received after idle_timeout reached, then a getProperties is transmitted
        self.idle_timer = time.time()
        self.idle_timeout = 20

        # vector timeouts are used to check that when a new vector is sent
        # a reply setvector will be received within the given time
        self.vector_timeout_enable = True
        self.vector_timeout_min = 2
        self.vector_timeout_max = 10

        # and shutdown routine sets this to True to stop coroutines
        self._stop = False
        # this is set to True when asyncrun is finished
        self.stopped = False

        # logging level and filepointer to logfile
        # level, None for no logging, 1 for parsed vector tags only,
        #                             2 for parsed vectors and members (apart from BLOB's)
        #                             3 for raw unparsed data
        self.level = None
        self.logfile = None
        self.logfp = None

    def setlogging(self, level, logfile):
        "Sets the logging level and logfile, returns the level, which will be None on failure"
        try:
            if level is None:
                self.level = None
                if self.logfp:
                    self.logfp.close()
                self.logfp = None
                self.logfile = None
                return None
            if level in (1, 2, 3):
                self.level = level
            else:
                self.level = None
                if self.logfp:
                    self.logfp.close()
                self.logfp = None
                self.logfile = None
                return None
            logfile = pathlib.Path(logfile).expanduser().resolve()
            self.logfp = open(logfile, "wb")
            if not self.logfp.writable():
                self.logfp.close()
                self.level = None
                self.logfp = None
                self.logfile = None
                return None
        except:
            self.level = None
            if self.logfp:
                self.logfp.close()
            self.logfp = None
            self.logfile = None
            return None
        self.logfile = logfile
        return self.level

    def shutdown(self):
        "Shuts down the client"
        if self.logfp:
            self.logfp.close()
            self.level = None
            self.logfp = None
            self.logfile = None
        self._stop = True

    async def report(self, message):
        timestamp = datetime.now(tz=timezone.utc)
        timestamp = timestamp.replace(tzinfo=None)
        root = ET.fromstring(f"<message timestamp=\"{timestamp.isoformat(sep='T')}\" message=\"{message}\" />")
        event = events.Message(root, None, self)
        await self.rxevent(event)

    def enabledlen(self):
        "Returns the number of enabled devices"
        return sum(map(lambda x:1 if x.enable else 0, self.data.values()))


    def __setitem__(self, device):
        "Devices are added by being learnt from the driver, they cannot be manually added"
        raise KeyError


    async def _comms(self):
        "Create a connection to an INDI port"
        try:
            while not self._stop:
                self.tx_timer = None
                self.idle_timer = time.time()
                try:
                    # start by openning a connection
                    # clear messages
                    self.messages.clear()
                    await self.report("Attempting to connect")
                    reader, writer = await asyncio.open_connection(self.indihost, self.indiport)
                    self.connected = True
                    self.messages.clear()
                    await self.report(f"Connected to {self.indihost}:{self.indiport}")
                    await asyncio.gather(self._run_tx(writer),
                                         self._run_rx(reader),
                                         self._check_alive(writer)
                                         )
                except ConnectionRefusedError:
                    await self.report(f"Error: Connection refused on {self.indihost}:{self.indiport}")
                except ConnectionResetError:
                    await self.report("Error: Connection Lost")
                self._clear_connection()
                if self._stop:
                    break
                else:
                    await self.report(f"Connection failed, re-trying...")

                # wait five seconds before re-trying, but keep checking
                # that self._stop has not been set
                count = 0
                while not self._stop:
                    await asyncio.sleep(0.5)
                    count += 1
                    if count >= 10:
                        break
        finally:
            self.shutdown()


    def _clear_connection(self):
        "On a connection closing down, clears queues"
        self.connected = False
        self.tx_timer = None
        # clear devices etc
        self.clear()
        # clear the writerque
        self.writerque.clear()
        if not self.readerque.empty():
            # empty the queue
            while True:
                try:
                    xmldata = self.readerque.get_nowait()
                    self.readerque.task_done()
                except asyncio.QueueEmpty:
                    break



    def send(self, xmldata):
        "Transmits xmldata, this is an internal method, not normally called by a user."
        if self.connected:
            self.writerque.append(xmldata)

    async def _check_alive(self, writer):
        try:
            while self.connected and (not self._stop):
                await asyncio.sleep(0)
                if self.tx_timer:
                    # data has been sent, waiting for reply
                    telapsed = time.time() - self.tx_timer
                    if telapsed > self.respond_timeout:
                        # no response to transmission self.respond_timeout seconds ago
                       writer.close()
                       await writer.wait_closed()
                       self._clear_connection()
                       if not self._stop:
                           await self.report("Error: Connection timed out")
            if self.connected and self._stop:
                writer.close()
                await writer.wait_closed()
                self._clear_connection()
        except KeyboardInterrupt:
            self.shutdown()
        finally:
            self.connected = False


    def _logtx(self, txdata):
        "log data to file"
        self.logfp.write(b"\nTX:: ")
        if self.level == 1:
            for element in txdata:
                txdata.remove(element)
            txdata.text = ""
            binarydata = ET.tostring(txdata, short_empty_elements=False)
            self.logfp.write(binarydata)
        if self.level == 2:
            tag = txdata.tag
            for element in txdata:
                if tag  == "newBLOBVector":
                    element.text = "NOT LOGGED"
            binarydata = ET.tostring(txdata)
            self.logfp.write(binarydata)
        if self.level == 3:
            if txdata.tag == "newBLOBVector" and len(txdata):
                # txdata is a newBLOBVector containing blobs
                # the generator blob_xml_bytes yields bytes
                for binarydata in blob_xml_bytes(txdata):
                    self.logfp.write(binarydata)
            else:
                binarydata = ET.tostring(txdata)
                self.logfp.write(binarydata)




    async def _run_tx(self, writer):
        "Monitors self.writerque and if it has data, uses writer to send it"
        try:
            while self.connected and (not self._stop):
                await asyncio.sleep(0)
                try:
                    txdata = self.writerque.popleft()
                except IndexError:
                    continue

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

                # data has been transmitted set timers going, do not set timer
                # for enableBLOB as no answer is expected for that
                if (self.tx_timer is None) and (txdata.tag != "enableBLOB"):
                    self.tx_timer = time.time()
                self.idle_timer = time.time()

                if self.level:
                    self._logtx(txdata)
        except KeyboardInterrupt:
            self.shutdown()

    def _logrx(self, rxdata):
        "log data to file"
        data = copy.deepcopy(rxdata)
        self.logfp.write(b"\nRX:: ")
        if self.level == 1:
            for element in data:
                data.remove(element)
            data.text = ""
            binarydata = ET.tostring(data, short_empty_elements=False)
            self.logfp.write(binarydata)
        if self.level == 2:
            tag = data.tag
            for element in data:
                if tag  == "newBLOBVector":
                    element.text = "NOT LOGGED"
            binarydata = ET.tostring(data)
            self.logfp.write(binarydata)
        if self.level == 3:
            binarydata = ET.tostring(data)
            self.logfp.write(binarydata)


    async def _run_rx(self, reader):
        "pass xml.etree.ElementTree data to readerque"
        try:
            source = self._datasource(reader)
            while self.connected and (not self._stop):
                await asyncio.sleep(0)
                # get block of xml.etree.ElementTree data
                # from source and append it to  readerque
                rxdata = await anext(source)
                if rxdata is not None:
                    # and place rxdata into readerque
                    try:
                        self.readerque.put_nowait(rxdata)
                    except asyncio.QueueFull:
                        # The queue is full, something may be wrong
                        # discard this data and continue
                        pass
                if self.level:
                    self._logrx(rxdata)
        except RuntimeError:
            # catches StopAsyncIteration and stops this coroutine
            pass
        except KeyboardInterrupt:
            self.shutdown()


    async def _datasource(self, reader):
        # get received data, parse it, and yield it as xml.etree.ElementTree object
        data_in = self._datainput(reader)
        message = b''
        messagetagnumber = None
        try:
            while self.connected and (not self._stop):
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
                        except ET.ParseError as e:
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
                    except KeyboardInterrupt:
                        self.shutdown()
                        break
                    except ET.ParseError as e:
                        message = b''
                        messagetagnumber = None
                        continue
                    # xml datablock done, yield it up
                    yield root
                    # and start again, waiting for a new message
                    message = b''
                    messagetagnumber = None
        except KeyboardInterrupt:
            self.shutdown()
        except asyncio.CancelledError:
            self.shutdown()
            raise


    async def _datainput(self, reader):
        "Generator producing binary string of data from the port"
        binarydata = b""
        try:
            while self.connected and (not self._stop):
                await asyncio.sleep(0)
                try:
                    data = await reader.readuntil(separator=b'>')
                except asyncio.LimitOverrunError:
                    data = await reader.read(n=32000)
                except asyncio.IncompleteReadError:
                    binarydata = b""
                    continue
                if not data:
                    continue
                # data received
                self.tx_timer = None
                self.idle_timer = time.time()
                if b">" in data:
                    binarydata = binarydata + data
                    yield binarydata
                    binarydata = b""
                else:
                    # data has content but no > found
                    binarydata += data
                    # could put a max value here to stop this increasing indefinetly
        except KeyboardInterrupt:
            self.shutdown()
        except asyncio.CancelledError:
            self.shutdown()
            raise



    async def _rxhandler(self):
        """Populates the events using data from self.readerque"""
        try:
            while not self._stop:
                # get block of data from the self.readerque
                await asyncio.sleep(0)
                try:
                    root = self.readerque.get_nowait()
                except asyncio.QueueEmpty:
                    # nothing to read, continue while loop which re-checks the _stop flag
                    continue
                devicename = root.get("device")
                # block any other thread from accessing data until update is done
                try:
                    with threading.Lock():
                        if devicename is None:
                            if root.tag == "message":
                                # create event
                                event = events.Message(root, None, self)
                            else:
                                # if no devicename and not message, do nothing
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
                            self.data[devicename] = newdevice
                        else:
                            # device not known, not a def, so ignore it
                            continue
                except ParseException as pe:
                    # if a ParseException is raised, it is because received data is malformed
                    await self.report(f"Error: {pe}")
                    continue
                finally:
                    self.readerque.task_done()
                # and to get here, continue has not been called
                # and an event has been created, call the user event handling function
                await self.rxevent(event)
        finally:
            self.shutdown()


    def snapshot(self):
        "Take snapshot of the devices"
        with threading.Lock():
            # other threads cannot change the client.data dictionary
            snap = {}
            if self.data:
                for devicename, device in self.data.items():
                    snap[devicename] = device._snapshot()
        # other threads can now access client.data
        # return the snapshot
        return snap


    def send_newVector(self, devicename, vectorname, timestamp=None, members={}):
        """Send a new Vector, note members is a membername to value dictionary,
           It could also be a vector, which is itself a membername to value mapping"""
        if devicename not in self.data:
            return
        device = self.data[devicename]
        if vectorname not in device:
            return
        try:
            propertyvector = device[vectorname]
            if propertyvector.vectortype == "SwitchVector":
                propertyvector.send_newSwitchVector(timestamp, members)
            elif propertyvector.vectortype == "TextVector":
                propertyvector.send_newTextVector(timestamp, members)
            elif propertyvector.vectortype == "NumberVector":
                propertyvector.send_newNumberVector(timestamp, members)
            elif propertyvector.vectortype == "BLOBVector":
                propertyvector.send_newBLOBVector(timestamp, members)
        except KeyboardInterrupt:
            self.shutdown()

    def set_vector_timeouts(self, timeout_enable=None, timeout_min=None, timeout_max=None):
        if not timeout_enable is None:
            self.vector_timeout_enable = timeout_enable
        if not timeout_min is None:
            self.vector_timeout_min = timeout_min
        if not timeout_max is None:
            self.vector_timeout_max = timeout_max


    async def _timeout_monitor(self):
        """Sends a getProperties every five seconds if no devices have been learnt
           or every self.idle_timeout seconds if nothing has been transmitted or received"""
        try:
            count = 0
            while (not self._stop):
                await asyncio.sleep(0.5)
                # This loop tests timeout values every half second
                if not self.connected:
                    count = 0
                else:
                    # so the connection is up, check devices exist
                    if len(self.data):
                        # connection is up and devices exist, if nothing has been
                        # sent or received for self.idle_timeout seconds, send a getProperties
                        nowtime = time.time()
                        telapsed = nowtime - self.idle_timer
                        if telapsed > self.idle_timeout:
                            self.send_getProperties()
                        elif self.vector_timeout_enable:
                            # check if any vectors have timed out
                            for device in self.data.values():
                                for vector in device.values():
                                    if not vector.enable:
                                        continue
                                    if vector.checktimedout(nowtime):
                                        # Creat a VectorTimeOut event
                                        event = events.VectorTimeOut(device, vector)
                                        await self.rxevent(event)
                    else:
                        # no devices
                        # then send a getProperties, every five seconds, when count is zero
                        if not count:
                            self.send_getProperties()
                            await self.report("getProperties sent")
                        count += 1
                        if count >= 10:
                            count = 0
        except KeyboardInterrupt:
            self.shutdown()
        except asyncio.CancelledError:
            self.shutdown()
            raise



    def send_getProperties(self, devicename=None, vectorname=None):
        """Sends a getProperties request."""
        if self.connected:
            xmldata = ET.Element('getProperties')
            xmldata.set("version", "1.7")
            if not devicename:
                self.send(xmldata)
                return
            xmldata.set("device", devicename)
            if vectorname:
                xmldata.set("name", vectorname)
            self.send(xmldata)

    def send_enableBLOB(self, value, devicename, vectorname=None):
        """Sends an enableBLOB instruction."""
        if self.connected:
            if value not in ("Never", "Also", "Only"):
                return
            xmldata = ET.Element('enableBLOB')
            if not devicename:
                # a devicename is required
                return
            xmldata.set("device", devicename)
            if vectorname:
                xmldata.set("name", vectorname)
            xmldata.text = value
            self.send(xmldata)

    async def rxevent(self, event):
        """Override this if this client is operating a script to act on received data.
           On receiving data, this is called, and should handle any necessary actions.
           event is an object with attributes according to the data received."""
        pass


    async def asyncrun(self):
        """Gathers tasks to be run simultaneously"""
        self._stop = False
        await asyncio.gather(self._comms(), self._rxhandler(), self._timeout_monitor(), return_exceptions=True)
        self.stopped = True


class Device(collections.UserDict):

    def __init__(self, devicename):
        super().__init__()

        # This device name
        self.devicename = devicename

        # this is a dictionary of property name to propertyvector this device owns
        self.data = {}

    @property
    def enable(self):
        "Returns True if any vector of this device has enable True, otherwise False"
        ebl = False
        for vector in self.data.values():
            if vector.enable:
                return True
        return False


class _Device(Device):

    """An instance of this should be created for each device.
    """

    def __init__(self, devicename, client):
        super().__init__(devicename)

        # and the device has a reference to its client
        self._client = client

        # self.messages is a deque of tuples (timestamp, message)
        self.messages = collections.deque(maxlen=8)


    def __setitem__(self, propertyname, propertyvector):
        "Properties are added by being learnt from the driver, they cannot be manually added"
        raise KeyError


    def rxvector(self, root):
        """Handle received data, sets new propertyvector into self.data,
           or updates existing property vector and returns an event"""
        if root.tag == "delProperty":
            return events.delProperty(root, self._client)
        elif root.tag == "message":
            return events.Message(root, self, self._client)
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

    def _snapshot(self):
        snapdevice = Device(self.devicename)
        for vectorname, vector in self.data:
            snapdevice[vectorname] = vector._snapshot()
        snapdevice.messages = list(self.messages)
        return snapdevice
