

import collections, asyncio, time, copy, json, pathlib, logging

from datetime import datetime, timezone

import xml.etree.ElementTree as ET

from . import events

from .propertymembers import ParseException

logger = logging.getLogger(__name__)


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
        b'setBLOBVector',
        b'getProperties'       # for snooping
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



class IPyClient(collections.UserDict):

    """This class can be used to create your own scripts or client, and provides
       a connection to an INDI service, with parsing of the XML protocol.
       You should create your own class, inheriting from this, and overriding the
       rxevent method.
       The argument clientdata provides any named arguments you may wish to pass
       into the object when instantiating it.
       The IPyClient object is also a mapping of devicename to device object, which
       is populated as devices and their vectors are learned from the INDI protocol."""


    def __init__(self, indihost="localhost", indiport=7624, **clientdata):
        "An instance of this is a mapping of devicename to device object"
        super().__init__()

        # The UserDict will create self.data which will become
        # a dictionary of devicename to device object

        # the user_string is available to be any string a user of
        # this client may wish to set
        self.user_string = ""

        self.indihost = indihost
        self.indiport = indiport

        # dictionary of optional data
        self.clientdata = clientdata

        # These will be created when a connection is made using
        # await asyncio.open_connection(self.indihost, self.indiport)
        self._writer = None
        self._reader = None

        # self.messages is a deque of (Timestamp, message) tuples
        self.messages = collections.deque(maxlen=8)

        # note, messages are added with 'appendleft'
        # so newest message is messages[0]
        # oldest message is messages[-1] or can be obtained with .pop()


        #####################
        # The following sets of timers are only enabled if this is True
        self.timeout_enable = True

        # vector timeouts are used to check that when a new vector is sent
        # a reply setvector will be received within the given time
        self.vector_timeout_min = 2
        self.vector_timeout_max = 10

        # idle_timer is set when either data is transmitted or received.
        # If nothing is sent or received after idle_timeout reached, then a getProperties is transmitted
        self.idle_timer = time.time()
        self.idle_timeout = 20
        # self.idle_timeout is set to two times self.vector_timeout_max

        # tx_timer is set when any data is transmitted,
        # it is used to check when any data is received,
        # at which point it becomes None again.
        # if there is no answer after self.respond_timeout seconds,
        # assume the connection has failed and close the connection
        self.tx_timer = None
        self.respond_timeout = 40
        # self.respond_timeout is set to four times self.vector_timeout_max
        ######################

        # and shutdown routine sets this to True to stop coroutines
        self._stop = False
        # this is set when asyncrun is finished
        self.stopped = asyncio.Event()

        # Indicates how verbose the debug xml logs will be when created.
        self._verbose = 1

        # Enables reports, by adding INFO logs to client messages
        self.enable_reports = True

        # holds dictionary of initial user strings
        self.user_string_dict = {}

        # set and unset BLOBfolder
        self._BLOBfolder = None
        self._blobfolderchanged = False
        # This is the default enableBLOB value
        self._enableBLOBdefault = "Never"


    @property
    def connected(self):
        "property showing connected status, True or False"
        if self._writer is None:
            return False
        else:
            return True


    # The enableBLOBdefault default should typically be set before asyncrun is
    # called, so if set to Also, this will ensure all BLOBs will be received without
    # further action
    @property
    def enableBLOBdefault(self):
        return self._enableBLOBdefault

    @enableBLOBdefault.setter
    def enableBLOBdefault(self, value):
        if value in ("Never", "Also", "Only"):
            self._enableBLOBdefault = value

    # Setting a BLOBfolder forces all BLOBs will be received and saved as files to the given folder

    def _get_BLOBfolder(self):
        return self._BLOBfolder

    def _set_BLOBfolder(self, value):
        """Setting the BLOBfolder to a folder will automatically set all devices to Also
           Setting it to None, will set all devices to self._enableBLOBdefault"""
        if value:
            if isinstance(value, pathlib.Path):
                blobpath = value
            else:
                blobpath = pathlib.Path(value).expanduser().resolve()
            if not blobpath.is_dir():
                raise KeyError("If given, the BLOB's folder should be an existing directory")
            for device in self.values():
                device._enableBLOB = "Also"
                for vector in device.values():
                    if vector.vectortype == "BLOBVector":
                        vector._enableBLOB = "Also"
        else:
            blobpath = None
            if self._BLOBfolder is None:
                # no change
                return
            for device in self.values():
                device._enableBLOB = self._enableBLOBdefault
                for vector in device.values():
                    if vector.vectortype == "BLOBVector":
                        vector._enableBLOB = self._enableBLOBdefault
        self._BLOBfolder = blobpath
        self._blobfolderchanged = True


    BLOBfolder = property(
        fget=_get_BLOBfolder,
        fset=_set_BLOBfolder,
        doc= """Setting the BLOBfolder to a folder will automatically transmit an enableBLOB
for all devices set to Also, and will save incoming BLOBs to that folder.
Setting it to None will transmit an enableBLOB for all devices set to the enableBLOBdefault value"""
        )


    def set_user_string(self, devicename, vectorname, membername, user_string = ""):
        """Each device, vector and member has a user_string attribute, initially set to empty strings,
           and can be changed to any string you may require. These strings may be used for any purpose,
           such as setting associated id values for a database perhaps.
           It is suggested they should be limited to strings, so if JSON snapshots
           are taken, they are easily converted to JSON values.
           This method can be called before asyncrun is called, and before the devices are learnt, which
           would only be useful for those scripts which know in advance what devices they are connecting to.
           As soon as the device, vector or member becomes learnt it will then be set with the user string.
           If membername is None, the user_string is applied to the vector, if vectorname is None
           it applies to the device.
           """
        if not devicename:
            raise KeyError("A devicename must be given to set_user_string")
        if membername and (not vectorname):
            raise KeyError("If a membername is specified, a vectorname must also be given")

        if not vectorname:
            self.user_string_dict[devicename, None, None] = user_string
            if devicename in self:
                self[devicename].user_string = user_string

        elif not membername:
            self.user_string_dict[devicename, vectorname, None] = user_string
            if devicename in self:
                if vectorname in self[devicename]:
                    self[devicename][vectorname].user_string = user_string

        else:
            self.user_string_dict[devicename, vectorname, membername] = user_string
            if devicename in self:
                if vectorname in self[devicename]:
                    vector = self[devicename][vectorname]
                    if membername in vector:
                        member = vector.member(membername)
                        member.user_string = user_string


    def get_user_string(self, devicename, vectorname, membername):
        """Each device, vector and member has a user_string attribute. If devicename,
           vectorname and membername are given this method returns the user string of the member.
           If membername is None, the user_string of the vector is returned, if vectorname is None
           as well, the user_string of the device is returned. If no object can be found, and no
           initial string has been set with the set_user_string method, None will be returned."""
        if not devicename:
            raise KeyError("A devicename must be given to set_user_string")
        if membername and (not vectorname):
            raise KeyError("If a membername is specified, a vectorname must also be given")

        if vectorname and membername:
            if devicename in self:
                device = self[devicename]
                if vectorname in device:
                    vector = device[vectorname]
                    if membername in vector:
                        return vector.member(membername).user_string
            return self.user_string_dict.get( (devicename, vectorname, membername) )

        if vectorname:
            if devicename in self:
                device = self[devicename]
                if vectorname in device:
                    return device[vectorname].user_string
            return self.user_string_dict.get( (devicename, vectorname, None) )

        if devicename in self:
            return self[devicename].user_string

        return self.user_string_dict.get( (devicename, None, None) )


    def debug_verbosity(self, verbose):
        """Set how verbose the debug xml logs will be when created.

           |  0 no xml logs will be generated
           |  1 for transmitted/received vector tags only,
           |  2 for transmitted/received vectors, members and contents (apart from BLOBs)
           |  3 for all transmitted/received data including BLOBs."""
        if verbose not in (0,1,2,3):
            raise ValueError
        self._verbose = verbose

    async def hardware(self):
        """This is started when asyncrun is called. As default does nothing so stops immediately.
           It is available to be overriden if required."""
        pass

    def shutdown(self):
        "Shuts down the client, sets the flag self._stop to True"
        self._stop = True

    @property
    def stop(self):
        "returns self._stop, being the instruction to stop the client"
        return self._stop


    async def report(self, message):
        """The given string message will be logged at level INFO,
           and if self.enable_reports is True will be injected into
           the received data, which will be picked up by the rxevent method.
           It is a way to set a message on to your client display, in the
           same way messages come from the INDI service."""
        try:
            logger.info(message)
            if not self.enable_reports:
                return
            timestamp = datetime.now(tz=timezone.utc)
            timestamp = timestamp.replace(tzinfo=None)
            xmldata = ET.fromstring(f"<message timestamp=\"{timestamp.isoformat(sep='T')}\" message=\"{message}\" />")
            # and call the receive handler, as if this was received data
            await self._rxhandler(xmldata)
        except Exception :
            logger.exception("Exception report from IPyClient.report method")


    async def warning(self, message):
        """The given string message will be logged at level WARNING,
           and will be injected into the received data, which will be
           picked up by the rxevent method.
           It is a way to set a message on to your client display, in the
           same way messages come from the INDI service."""
        try:
            logger.warning(message)
            timestamp = datetime.now(tz=timezone.utc)
            timestamp = timestamp.replace(tzinfo=None)
            xmldata = ET.fromstring(f"<message timestamp=\"{timestamp.isoformat(sep='T')}\" message=\"{message}\" />")
            # and call the receive handler, as if this was received data
            await self._rxhandler(xmldata)
        except Exception :
            logger.exception("Exception report from IPyClient.warning method")


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
                t2 = None
                t3 = None
                try:
                    # start by openning a connection
                    await self.warning(f"Attempting to connect to {self.indihost}:{self.indiport}")
                    self._reader, self._writer = await asyncio.open_connection(self.indihost, self.indiport)
                    self.messages.clear()
                    # clear devices etc
                    self.clear()
                    await self.warning(f"Connected to {self.indihost}:{self.indiport}")
                    t2 = asyncio.create_task(self._run_rx())
                    t3 = asyncio.create_task(self._check_alive())
                    await asyncio.gather(t2, t3)
                except ConnectionRefusedError:
                    await self.warning(f"Connection refused on {self.indihost}:{self.indiport}")
                except ConnectionError:
                    await self.warning(f"Connection Lost on {self.indihost}:{self.indiport}")
                except OSError as e:
                    await self.warning(f"Connection Error on {self.indihost}:{self.indiport}")
                except Exception:
                    logger.exception(f"Connection Error on {self.indihost}:{self.indiport}")
                    await self.warning("Connection failed")
                await self._clear_connection()
                # connection has failed, ensure all tasks are done
                if t2:
                    while not t2.done():
                        await asyncio.sleep(0)
                if t3:
                    while not t3.done():
                        await asyncio.sleep(0)
                if self._stop:
                    break
                else:
                    await self.warning("Connection failed, re-trying...")
                # wait five seconds before re-trying, but keep checking
                # that self._stop has not been set
                count = 0
                while not self._stop:
                    await asyncio.sleep(0.5)
                    count += 1
                    if count >= 10:
                        break
        except Exception:
            logger.exception("Exception report from IPyClient._comms method")
            raise
        finally:
            await self._clear_connection()
            self.shutdown()



    async def _clear_connection(self):
        "Clears a connection"
        try:
            if self._writer is not None:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception:
            logger.exception("Exception report from IPyClient._clear_connection method")
        await self.warning(f"Connection closed on {self.indihost}:{self.indiport}")
        self.tx_timer = None
        self._writer = None
        self._reader = None
        self.messages.clear()
        # clear devices etc
        self.clear()



    async def send(self, xmldata):
        """Transmits xmldata, this is an internal method, not normally called by a user.
           xmldata is an xml.etree.ElementTree object"""
        if not self.connected:
            return
        if self._stop:
            return
        try:
            # send it out on the port
            binarydata = ET.tostring(xmldata)
            # Send to the port
            self._writer.write(binarydata)
            await self._writer.drain()
            if self.timeout_enable:
                # data has been transmitted set timers going, do not set timer
                # for enableBLOB as no answer is expected for that
                if (self.tx_timer is None) and (xmldata.tag != "enableBLOB"):
                    self.tx_timer = time.time()
            self.idle_timer = time.time()
            if logger.isEnabledFor(logging.DEBUG):
                self._logtx(xmldata)
        except Exception:
            await self.warning(f"Sending Error on {self.indihost}:{self.indiport}")
            await self._clear_connection()


    async def _check_alive(self):
        "Checks timers, drops connection on error"

        try:
            count = -1 # increases by 1 every 0.1 seconds, after 5 seconds, goes to zero
            while self.connected and not self._stop:
                await asyncio.sleep(0.1)
                if self._stop:
                    break

                count += 1
                if count >= 50:      # 50 x 0.1 is 5 seconds
                    count = 0
                devices = list(device for device in self.data.values() if device.enable)

                # send a getProperties every five seconds if no devices have been learnt
                if not count:
                    # count is zero, on startup and every five seconds
                    if not devices:
                        # no devices, send a getProperties
                        await self.send_getProperties()
                        await self.report("getProperties sent")

                if not devices:
                    # no point doing any further tests, continue while loop
                    continue

                # devices exist

                # connection is up and devices exist
                if self._blobfolderchanged:
                    # devices all have an _enableBLOB attribute set
                    # when the BLOBfolder changed, this ensures an
                    # enableBLOB is sent with that value
                    self._blobfolderchanged = False
                    for device in devices:
                        await self.resend_enableBLOB(device.devicename)
                        if self._stop:
                            break
                        for vector in device.values():
                            if vector.enable and (vector.vectortype == "BLOBVector"):
                                await self.resend_enableBLOB(device.devicename, vector.name)
                                if self._stop:
                                    break
                        if self._stop:
                            break
                    # as enableBLOBs have been sent, leave
                    # checking timeouts for the next count (0.1 second)
                    continue

                if not self.timeout_enable:
                    # only test timeouts if this is True
                    continue

                # test these timers every 0.5 seconds
                if count % 5 :
                    continue

                nowtime = time.time()

                # if nothing received after self.respond_timeout, break out
                if self.tx_timer:
                    # data has been sent, waiting for reply
                    telapsed = nowtime - self.tx_timer
                    if telapsed > self.respond_timeout:
                        # no response to transmission self.respond_timeout seconds ago
                        if not self._stop:
                            await self.warning("Error: Connection timed out")
                        break

                # If nothing has been sent or received
                # for self.idle_timeout seconds, send a getProperties
                telapsed = nowtime - self.idle_timer
                if telapsed > self.idle_timeout:
                    await self.send_getProperties()

                # check if any vectors have timed out
                for device in devices:
                    for vector in device.values():
                        if not vector.enable:
                            continue
                        if vector.checktimedout(nowtime):
                            # Creat a VectorTimeOut event
                            event = events.VectorTimeOut(device, vector)
                            await self.rxevent(event)

        except Exception:
            logger.exception("Error in IPyClient._check_alive method")
            raise
        finally:
            await self._clear_connection()


    def _logtx(self, txdata):
        "log tx data with level debug, and detail depends on self._verbose"
        if not self._verbose:
            return
        startlog = "TX:: "
        if self._verbose == 3:
            binarydata = ET.tostring(txdata)
            logger.debug(startlog + binarydata.decode())
        elif self._verbose == 2:
            if txdata.tag == "newBLOBVector" or txdata.tag == "setBLOBVector":
                data = copy.deepcopy(txdata)
                for element in data:
                    element.text = "NOT LOGGED"
                binarydata = ET.tostring(data)
            else:
                binarydata = ET.tostring(txdata)
            logger.debug(startlog + binarydata.decode())
        elif self._verbose == 1:
            data = copy.deepcopy(txdata)
            for element in data:
                data.remove(element)
            data.text = ""
            binarydata = ET.tostring(data, short_empty_elements=False).split(b">")
            logger.debug(startlog + binarydata[0].decode()+">")


    def _logrx(self, rxdata):
        "log rx data to file"
        if not self._verbose:
            return
        startlog = "RX:: "
        if self._verbose == 3:
            binarydata = ET.tostring(rxdata)
            logger.debug(startlog + binarydata.decode())
        elif self._verbose == 2:
            data = copy.deepcopy(rxdata)
            tag = data.tag
            for element in data:
                if tag  == "newBLOBVector":
                    element.text = "NOT LOGGED"
            binarydata = ET.tostring(data)
            logger.debug(startlog + binarydata.decode())
        elif self._verbose == 1:
            data = copy.deepcopy(rxdata)
            for element in data:
                data.remove(element)
            data.text = ""
            binarydata = ET.tostring(data, short_empty_elements=False).split(b">")
            logger.debug(startlog + binarydata[0].decode() + ">")

    async def _run_rx(self):
        "pass xml.etree.ElementTree data receive handler"
        try:
            # get block of xml.etree.ElementTree data
            # from self._xmlinput
            while self.connected and (not self._stop):
                rxdata = await self._xmlinput()
                if rxdata is None:
                    return
                # and call the receive handler
                await self._rxhandler(rxdata)
                # log it, then continue with next block
                if logger.isEnabledFor(logging.DEBUG):
                    self._logrx(rxdata)
        except ConnectionError:
            raise
        except Exception:
            logger.exception("Exception report from IPyClient._run_rx")
            raise


    async def _xmlinput(self):
        """get received data, parse it, and return it as xml.etree.ElementTree object
           Returns None if notconnected/stop flags arises"""
        message = b''
        messagetagnumber = None
        while self.connected and (not self._stop):
            await asyncio.sleep(0)
            data = await self._datainput()
            # data is either None, or binary data ending in b">"
            if data is None:
                return
            if not self.connected:
                return
            if self._stop:
                return
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
                    except ET.ParseError:
                       # failed to parse the message, continue at beginning
                        message = b''
                        messagetagnumber = None
                        continue
                    # xml datablock done, return it
                    return root
                # and read either the next message, or the children of this tag
                continue
            # To reach this point, the message is in progress, with a messagetagnumber set
            # keep adding the received data to message, until an endtag is reached
            message += data
            if message.endswith(_ENDTAGS[messagetagnumber]):
                # the message is complete, handle message here
                try:
                    root = ET.fromstring(message.decode("us-ascii"))
                except ET.ParseError:
                    # failed to parse the message, continue at beginning
                    message = b''
                    messagetagnumber = None
                    continue
                # xml datablock done, return it
                return root
            # so message is in progress, with a messagetagnumber set
            # but no valid endtag received yet, so continue the loop


    async def _datainput(self):
        """Waits for binary string of data ending in > from the port
           Returns None if notconnected/stop flags arises"""
        binarydata = b""
        while self.connected and (not self._stop):
            await asyncio.sleep(0)
            try:
                data = await self._reader.readuntil(separator=b'>')
            except asyncio.LimitOverrunError:
                data = await self._reader.read(n=32000)
            except asyncio.IncompleteReadError:
                binarydata = b""
                await asyncio.sleep(0.1)
                continue
            if not data:
                await asyncio.sleep(0.01)
                continue
            # data received
            self.tx_timer = None
            self.idle_timer = time.time()
            if b">" in data:
                binarydata = binarydata + data
                return binarydata
            # data has content but no > found
            binarydata += data
            # could put a max value here to stop this increasing indefinetly


    async def _rxhandler(self, xmldata):
        """Populates the events using received data"""
        try:
            devicename = xmldata.get("device")
            try:
                if devicename is None:
                    if xmldata.tag == "message":
                        # create event
                        event = events.Message(xmldata, None, self)
                    elif xmldata.tag == "getProperties":
                        # create event
                        event = events.getProperties(xmldata, None, self)
                    else:
                        # if no devicename and not message or getProperties, do nothing
                        return
                elif devicename in self:
                    # device is known about
                    device = self[devicename]
                    event = device.rxvector(xmldata)
                elif xmldata.tag == "getProperties":
                    # device is not known about, but this is a getProperties, so raise an event
                    event = events.getProperties(xmldata, None, self)
                elif xmldata.tag in DEFTAGS:
                    # device not known, but a def is received
                    newdevice = Device(devicename, self)
                    event = newdevice.rxvector(xmldata)
                    # no error has occurred, so add this device to self.data
                    self.data[devicename] = newdevice
                else:
                    # device not known, not a def or getProperties, so ignore it
                    return
            except ParseException as pe:
                # if a ParseException is raised, it is because received data is malformed
                await self.warning(str(pe))
                return

            if event.eventtype == "DefineBLOB":
                # every time a defBLOBVector is received, send an enable BLOB instruction
                await self.resend_enableBLOB(event.devicename, event.vectorname)
            elif self._BLOBfolder and (event.eventtype == "SetBLOB"):
                # If this event is a setblob, and if blobfolder has been defined, then save the blob to
                # a file in blobfolder, and set the member.filename to the filename saved
                loop = asyncio.get_running_loop()
                # save the BLOB to a file, make filename from timestamp
                timestampstring = event.timestamp.strftime('%Y%m%d_%H_%M_%S')
                for membername, membervalue in event.items():
                    if not membervalue:
                        return
                    sizeformat = event.sizeformat[membername]
                    filename =  membername + "_" + timestampstring + sizeformat[1]
                    counter = 0
                    while True:
                        filepath = self._BLOBfolder / filename
                        if filepath.exists():
                            # append a digit to the filename
                            counter += 1
                            filename = membername + "_" + timestampstring + "_" + str(counter) + sizeformat[1]
                        else:
                            # filepath does not exist, so a new file with this filepath can be created
                            break
                    await loop.run_in_executor(None, filepath.write_bytes, membervalue)
                    # add filename to member
                    memberobj = event.vector.member(membername)
                    memberobj.filename = filename

            # call the user event handling function
            await self.rxevent(event)

        except Exception:
            logger.exception("Exception report from IPyClient._rxhandler method")



    def snapshot(self):
        """Take a snapshot of the client and returns an object which is a restricted copy
           of the current state of devices and vectors.
           Vector methods for sending data will not be available.
           These copies will not be updated by events. This is provided so that you can
           handle the client data, without fear of their values changing."""

        snap = Snap(self.indihost, self.indiport, self.connected, self.messages, self.user_string)
        if self.data:
            for devicename, device in self.data.items():
                snap[devicename] = device.snapshot()
        # return the snapshot
        return snap


    async def send_newVector(self, devicename, vectorname, timestamp=None, members={}):
        """Send a Vector with updated member values, members is a membername
           to value dictionary.

           Note, if this vector is a BLOB Vector, the members dictionary should be
           {membername:(value, blobsize, blobformat)}
           where value could be a bytes object, a pathlib.Path, or a string filepath.
           If blobsize of zero is used, the size value sent will be set to the number of bytes
           in the BLOB. The INDI standard specifies the size should be that of the BLOB
           before any compression, therefore if you are sending a compressed file, you
           should set the blobsize prior to compression.
           blobformat should be a file extension, such as '.png'. If it is an empty string
           and value is a filename, the extension will be taken from the filename."""

        device = self.data.get(devicename)
        if device is None:
            return
        propertyvector = device.get(vectorname)
        if propertyvector is None:
            return
        try:
            if propertyvector.vectortype == "SwitchVector":
                await propertyvector.send_newSwitchVector(timestamp, members)
            elif propertyvector.vectortype == "TextVector":
                await propertyvector.send_newTextVector(timestamp, members)
            elif propertyvector.vectortype == "NumberVector":
                await propertyvector.send_newNumberVector(timestamp, members)
            elif propertyvector.vectortype == "BLOBVector":
                await propertyvector.send_newBLOBVector(timestamp, members)
        except Exception:
            logger.exception("Exception report from IPyClient.send_newVector method")
            raise


    def set_vector_timeouts(self, timeout_enable=None, timeout_min=None, timeout_max=None):
        """The INDI protocol allows the server to suggest a timeout for each vector. This
           method allows you to set minimum and maximum timeouts which restricts the
           suggested values.

           These should be given as integer seconds. If any parameter
           is not provided (left at None) then that value will not be changed.

           If timeout_enable is set to False, no VectorTimeOut events will occur.

           As default, timeouts are enabled, minimum is set to 2 seconds, maximum 10 seconds.
           """
        if timeout_enable is not None:
            self.timeout_enable = timeout_enable
        if timeout_min is not None:
            self.vector_timeout_min = timeout_min
        if timeout_max is not None:
            self.vector_timeout_max = timeout_max
            self.idle_timeout = 2 * timeout_max
            self.respond_timeout = 4 * timeout_max


    async def send_getProperties(self, devicename=None, vectorname=None):
        """Sends a getProperties request. On startup the IPyClient object
           will automatically send getProperties, so typically you will
           not have to use this method."""
        if self.connected:
            xmldata = ET.Element('getProperties')
            xmldata.set("version", "1.7")
            if not devicename:
                await self.send(xmldata)
                return
            xmldata.set("device", devicename)
            if vectorname:
                xmldata.set("name", vectorname)
            await self.send(xmldata)

    async def send_enableBLOB(self, value, devicename, vectorname=None):
        """Sends an enableBLOB instruction. The value should be one of "Never", "Also", "Only"."""
        if self.connected:
            if value not in ("Never", "Also", "Only"):
                return
            xmldata = ET.Element('enableBLOB')
            if not devicename:
                # a devicename is required
                return
            if devicename not in self:
                return
            device = self[devicename]
            if not device.enable:
                return
            xmldata.set("device", devicename)
            if vectorname:
                if vectorname not in device:
                    return
                vector = device[vectorname]
                if not vector.enable:
                    return
                if vector.vectortype != "BLOBVector":
                    return
                xmldata.set("name", vectorname)
                vector._enableBLOB = value
            else:
                # no vectorname, so this applies to all BLOB vectors of this device
                device._enableBLOB = value
                for vector in device.values():
                    if vector.vectortype == "BLOBVector":
                        vector._enableBLOB = value
            xmldata.text = value
            await self.send(xmldata)


    async def resend_enableBLOB(self, devicename, vectorname=None):
        """Internal method used by the framework, which sends an enableBLOB instruction,
           repeating the last value sent.
           Used as an automatic reply to a def packet received, if no last value sent
           the default is the enableBLOBdefault value."""
        if self.connected:
            xmldata = ET.Element('enableBLOB')
            if not devicename:
                # a devicename is required
                return
            if devicename not in self:
                return
            device = self[devicename]
            if not device.enable:
                return
            xmldata.set("device", devicename)
            if vectorname:
                if vectorname not in device:
                    return
                vector = device[vectorname]
                if not vector.enable:
                    return
                if vector.vectortype != "BLOBVector":
                    return
                xmldata.set("name", vectorname)
                value = vector._enableBLOB
            else:
                # no vectorname, so this applies to the device
                value = device._enableBLOB
            xmldata.text = value
            await self.send(xmldata)


    def get_vector_state(self, devicename, vectorname):
        """Gets the state string of the given vectorname, if this vector does not exist
           returns None - this could be because the vector is not yet learnt.
           The vector state attribute will still be returned, even if vector.enable is False"""
        device = self.data.get(devicename)
        if device is None:
            return
        propertyvector = device.get(vectorname)
        if propertyvector is None:
            return
        return propertyvector.state


    async def rxevent(self, event):
        """Override this.
           On receiving data, this is called, and should handle any necessary actions.
           event is an object with attributes according to the data received."""
        pass


    async def asyncrun(self):
        "Await this method to run the client."
        self._stop = False
        try:
            await asyncio.gather(self._comms(), self.hardware())
        except asyncio.CancelledError:
            self._stop = True
            raise
        finally:
            self.stopped.set()
            self._stop = True


class Snap(collections.UserDict):

    """An instance of this object is returned when a snapshot is
       taken of the client.
       It is a mapping of device name to device snapshots, which
       are in turn mappings of vectorname to vector snapshots.
       These snapshots record values and attributes, at the
       moment of the snapshot.
       Unlike IPyClient this has no send_newVector method, and the
       snap vectors do not have the send methods."""

    def __init__(self, indihost, indiport, connected, messages, user_string):
        super().__init__()
        self.indihost = indihost
        self.indiport = indiport
        self.connected = connected
        self.messages = list(messages)
        self.user_string = user_string

    def enabledlen(self):
        "Returns the number of enabled devices"
        return sum(map(lambda x:1 if x.enable else 0, self.data.values()))


    def get_vector_state(self, devicename, vectorname):
        """Gets the state string of the given vectorname, if this vector does not exist
           returns None"""
        device = self.data.get(devicename)
        if device is None:
            return
        propertyvector = device.get(vectorname)
        if propertyvector is None:
            return
        return propertyvector.state


    def dictdump(self, inc_blob=False):
        """Returns a dictionary of this client information
           and is used to generate the JSON output.
           If any BLOB vectors are included and inc_blob is False, the
           BLOB values will be given as None in the dictionary, set inc_blob
           to True to also include the BLOB in the dictionary."""
        messlist = []
        for message in self.messages:
            messlist.append([message[0].isoformat(sep='T'), message[1]])
        devdict = {}
        for devicename, device in self.items():
            devdict[devicename] = device.dictdump(inc_blob)
        return {"indihost":self.indihost,
                "indiport":self.indiport,
                "connected":self.connected,
                "user_string":self.user_string,
                "messages":messlist,
                "devices":devdict}

    def dumps(self, indent=None, separators=None, inc_blob=False):
        """Returns a JSON string of the snapshot.
           If any BLOB vectors are included and inc_blob is False, the
           BLOB values will be given as Null in the string, set inc_blob
           to True to also include the BLOB."""
        return json.dumps(self.dictdump(inc_blob), indent=indent, separators=separators)


    def dump(self, fp, indent=None, separators=None, inc_blob=False):
        """Serialize the snapshot as a JSON formatted stream to fp, a file-like object.
           This uses the Python json module which always produces str objects, not bytes
           objects. Therefore, fp.write() must support str input.
           If any BLOB vectors are included and inc_blob is False, the
           BLOB values will be given as Null in the file, set inc_blob
           to True to also include the BLOB."""
        return json.dump(self.dictdump(inc_blob), fp, indent=indent, separators=separators)



class _ParentDevice(collections.UserDict):
    "Each device is a mapping of vector name to vector object."

    def __init__(self, devicename):
        super().__init__()
        # self.data is created by UserDict and will become a
        # dictionary of vector name to vector this device owns

        # This device name
        self.devicename = devicename


    @property
    def enable(self):
        "Returns True if any vector of this device has enable True, otherwise False"
        for vector in self.data.values():
            if vector.enable:
                return True
        return False

    def disable(self):
        "If called, disables the device"
        for vector in self.data.values():
            vector.enable = False


class SnapDevice(_ParentDevice):
    """This object is used as a snapshot of this device
       It is a mapping of vector name to vector snapshots"""

    def __init__(self, devicename, messages, user_string):
        super().__init__(devicename)
        self.messages = list(messages)
        self.user_string = user_string

    def dictdump(self, inc_blob=False):
        """Returns a dictionary of this device information
           and is used to generate the JSON output.
           If any BLOB vectors are included and inc_blob is False, the
           BLOB values will be given as None in the dictionary, set inc_blob
           to True to also include the BLOB in the dictionary."""
        messlist = []
        for message in self.messages:
            messlist.append([message[0].isoformat(sep='T'), message[1]])
        vecdict = {}
        for vectorname, vector in self.items():
            vecdict[vectorname] = vector.dictdump(inc_blob)
        return {"devicename":self.devicename,
                "enable":self.enable,
                "user_string":self.user_string,
                "messages":messlist,
                "vectors":vecdict}

    def dumps(self, indent=None, separators=None, inc_blob=False):
        """Returns a JSON string of the snapshot.
           If any BLOB vectors are included and inc_blob is False, the
           BLOB values will be given as Null in the string, set inc_blob
           to True to also include the BLOB."""
        return json.dumps(self.dictdump(inc_blob), indent=indent, separators=separators)


    def dump(self, fp, indent=None, separators=None, inc_blob=False):
        """Serialize the snapshot as a JSON formatted stream to fp, a file-like object.
           This uses the Python json module which always produces str objects, not bytes
           objects. Therefore, fp.write() must support str input.
           If any BLOB vectors are included and inc_blob is False, the
           BLOB values will be given as Null in the file, set inc_blob
           to True to also include the BLOB."""
        return json.dump(self.dictdump(inc_blob), fp, indent=indent, separators=separators)



class Device(_ParentDevice):

    """An instance of this is created for each device
       as data is received.
    """

    def __init__(self, devicename, client):
        super().__init__(devicename)

        # the user_string is available to be any string a user of
        # this device may wish to set
        self.user_string = client.user_string_dict.get((devicename, None, None), "")

        # and the device has a reference to its client
        self._client = client

        # self.messages is a deque of tuples (timestamp, message)
        self.messages = collections.deque(maxlen=8)

        # only applicable to BLOB vectors
        if client._BLOBfolder is None:
            self._enableBLOB = client._enableBLOBdefault
        else:
            self._enableBLOB = "Also"


    def __setitem__(self, propertyname, propertyvector):
        "Properties are added by being learnt from the driver, they cannot be manually added"
        raise KeyError


    def rxvector(self, root):
        """Handle received data, sets new propertyvector into self.data,
           or updates existing property vector and returns an event"""

        if (root.tag in DEFTAGS) and (not self.enable):
            # if this device is disabled, but about to become enabled
            # this action will set its enableBLOB value
            if self._client._BLOBfolder is None:
                self._enableBLOB = self._client._enableBLOBdefault
            else:
                self._enableBLOB = "Also"
        try:
            if root.tag == "delProperty":
                return events.delProperty(root, self, self._client)
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
            elif root.tag == "getProperties":
                return events.getProperties(root, self, self._client)
            else:
                raise ParseException("Unrecognised tag received")
        except ParseException:
            raise
        except Exception:
            logger.exception("Exception report from IPyClient.rxvector method")
            raise ParseException("Error while attempting to parse received data")


    def snapshot(self):
        """Take a snapshot of the device and returns an object which is a restricted copy
           of the current state of the device and its vectors.
           Vector methods for sending data will not be available.
           This copy will not be updated by events. This is provided so that you can
           handle the device data, without fear of the value changing."""
        snapdevice = SnapDevice(self.devicename, self.messages, self.user_string)
        for vectorname, vector in self.data.items():
            snapdevice[vectorname] = vector.snapshot()
        return snapdevice
