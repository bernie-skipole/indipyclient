"""
This module contains QueClient, which inherits from IPyClient and transmits
and receives data on two queues, together with function runqueclient.

This may be useful where the user prefers to write his own code in one thread,
and communicate via the queues to this client running in another thread.
"""



import asyncio, queue, collections, pathlib

from datetime import datetime, timezone

from .ipyclient import IPyClient


EventItem = collections.namedtuple('EventItem', ['eventtype', 'devicename', 'vectorname', 'timestamp', 'snapshot'])


class QueClient(IPyClient):

    """This inherits from IPyClient.

       On receiving an event, it sets derived data (including a client snapshot), into "rxque" which your code can accept and act on.

       It checks the contents of "txque", which your own code populates, and transmits this data to the server."""

    def __init__(self, txque, rxque, indihost="localhost", indiport=7624, blobfolder=None):
        """txque and rxque should be instances of one of queue.Queue, asyncio.Queue, or collections.deque
           If blobfolder is given, and an enableBLOB is sent, received blobs will be
           saved to that folder and the appropriate member.user_string will be set to
           the last filename saved
        """
        if blobfolder:
            if isinstance(blobfolder, pathlib.Path):
                blobfolderpath = blobfolder
            else:
                blobfolderpath = pathlib.Path(blobfolder).expanduser().resolve()
            if not blobfolderpath.is_dir():
                raise KeyError("If given, the BLOB's folder should be an existing directory")
        else:
            blobfolderpath = None
        super().__init__(indihost, indiport, txque=txque, rxque=rxque, blobfolder=blobfolderpath)

        # self.clientdata will contain keys txque, rxque, blobfolder


    async def _set_rxque_item(self, eventtype, devicename, vectorname, timestamp):
        rxque = self.clientdata['rxque']
        item = EventItem(eventtype, devicename, vectorname, timestamp, self.snapshot())
        if isinstance(rxque, queue.Queue):
            while not self._stop:
                try:
                    rxque.put_nowait(item)
                except queue.Full:
                    await asyncio.sleep(0.02)
                else:
                    break
        elif isinstance(rxque, asyncio.Queue):
            await self.queueput(rxque, item, timeout=0.1)
        elif isinstance(rxque, collections.deque):
            # append item to right side of rxque
            rxque.append(item)
        else:
            raise TypeError("rxque should be either a queue.Queue, asyncio.Queue, or collections.deque")


    async def rxevent(self, event):
        """On being called when an event is received, this generates and adds an EventItem to rxque,
           where an EventItem is a named tuple with attributes:

           eventtype - a string, one of Message, getProperties, Delete, Define, DefineBLOB, Set, SetBLOB,
                       these indicate data is received from the client, and the type of event. It could
                       also be the string "snapshot", which does not indicate a received event, but is a
                       response to a snapshot request received from txque, or "TimeOut" which indicates an
                       expected update has not occurred, or "State" which indicates you have just transmitted
                       a new vector, and therefore the snapshot will have your vector state set to Busy.
           devicename - usually the device name causing the event, or None for a system message, or
                        for the snapshot request.
           vectorname - usually the vector name causing the event, or None for a system message, or
                        device message, or for the snapshot request.
           timestamp - the event timestamp, None for the snapshot request.
           snapshot - A Snap object, being a snapshot of the client, which has been updated by the event.
           """

        # If this event is a setblob, and if blobfolder has been defined, the save the blob to
        # a file in blobfolder, and set the member.user_string to the filename saved

        blobfolder = self.clientdata['blobfolder']
        if blobfolder and (event.eventtype == "SetBLOB"):
            # save the BLOB to a file, make filename from timestamp
            timestampstring = event.timestamp.strftime('%Y%m%d_%H_%M_%S')
            for membername, membervalue in event.items():
                if not membervalue:
                    continue
                sizeformat = event.sizeformat[membername]
                filename =  membername + "_" + timestampstring + sizeformat[1]
                counter = 0
                while True:
                    filepath = blobfolder / filename
                    if filepath.exists():
                        # append a digit to the filename
                        counter += 1
                        filename = membername + "_" + timestampstring + "_" + str(counter) + sizeformat[1]
                    else:
                        # filepath does not exist, so a new file with this filepath can be created
                        break
                filepath.write_bytes(membervalue)
                # add filename to members user_string
                memberobj = event.vector.member(membername)
                memberobj.user_string = filename

        # set this event into rxque
        await self._set_rxque_item(event.eventtype, event.devicename, event.vectorname, event.timestamp)


    async def hardware(self):
        """Read txque and send data to server
           Item passed in the queue could be the string "snapshot" this is
           a request for the current snapshot, which will be sent via the rxque.
           If the item is None, this indicates the client should shut down.
           Otherwise the item should be a tuple or list of (devicename, vectorname, value)
           where value is normally a membername to membervalue dictionary, and these updates
           will be transmitted.
           If this vector is a BLOB Vector, the value dictionary should be {membername:(blobvalue, blobsize, blobformat)...}
           If value is a string, one of  "Never", "Also", "Only" then an enableBLOB with this value will be sent.
           If value is the string "Get", then a getProperties will be sent
           """
        txque = self.clientdata['txque']
        while not self._stop:

            if isinstance(txque, queue.Queue):
                try:
                    item = txque.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.02)
                    continue
            elif isinstance(txque, asyncio.Queue):
                try:
                    item = await asyncio.wait_for(txque, timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                txque.task_done()
            elif isinstance(txque, collections.deque):
                try:
                    item = txque.popleft()
                except IndexError:
                    await asyncio.sleep(0.02)
                    continue
            else:
                raise TypeError("txque should be either a queue.Queue, asyncio.Queue, or collections.deque")
            if item is None:
                # A None in the queue is a shutdown indicator
                self.shutdown()
                return
            if item == "snapshot":
                # The queue is requesting a snapshot
                await self._set_rxque_item("snapshot", None, None, None)
                continue
            if len(item) != 3:
                # invalid item
                continue
            if item[2] in ("Never", "Also", "Only"):
                await self.send_enableBLOB(item[2], item[0], item[1])
            elif item[2] == "Get":
                await self.send_getProperties(item[0], item[1])
            elif not isinstance(item[2], dict):
                # item not recognised
                continue
            else:
                timestamp = datetime.now(tz=timezone.utc)
                await self.send_newVector(item[0], item[1], timestamp, members=item[2])
                # a send_newVector will cause a State response
                await self._set_rxque_item("State", item[0], item[1], timestamp)



def runqueclient(txque, rxque, indihost="localhost", indiport=7624, blobfolder=None):
    """Blocking call which creates a QueClient object and runs its asyncrun method.
       If blobfolder is given, and an enableBLOB is sent, received blobs will be
       saved to that folder and the appropriate member.user_string will be set to
       the last filename saved"""

    if blobfolder:
        if isinstance(blobfolder, pathlib.Path):
            blobfolderpath = blobfolder
        else:
            blobfolderpath = pathlib.Path(blobfolder).expanduser().resolve()
        if not blobfolderpath.is_dir():
            raise KeyError("If given, the BLOB's folder should be an existing directory")
    else:
        blobfolderpath = None

    # create a QueClient object
    client = QueClient(txque, rxque, indihost, indiport, blobfolderpath)
    asyncio.run(client.asyncrun())


# This is normally used by first creating two queues

#  rxque = queue.Queue(maxsize=4)
#  txque = queue.Queue(maxsize=4)

# Then run runqueclient in its own thread,

#  clientthread = threading.Thread(target=runqueclient, args=(txque, rxque))
#  clientthread.start()

# Then run your own code, reading rxque, and transmitting on txque.

# To exit, use txque.put(None) to shut down the queclient,
# and finally wait for the clientthread to stop

# txque.put(None)
# clientthread.join()
