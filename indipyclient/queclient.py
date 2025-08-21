"""
This module contains QueClient, which inherits from IPyClient and transmits
and receives data on two queues, together with function runqueclient.

This may be useful where the user prefers to write his own code in one thread,
and communicate via the queues to this client running in another thread.
"""



import asyncio, queue, collections

from datetime import datetime, timezone

from .ipyclient import IPyClient


EventItem = collections.namedtuple('EventItem', ['eventtype', 'devicename', 'vectorname', 'timestamp', 'snapshot'])


class QueClient(IPyClient):

    """This inherits from IPyClient.

       On receiving an event, it sets derived data (including a client snapshot), into "rxque" which your code can accept and act on.

       It checks the contents of "txque", which your own code populates, and transmits this data to the server."""

    def __init__(self, txque, rxque, indihost="localhost", indiport=7624, blobfolder=None):
        """txque and rxque should be instances of one of queue.Queue, asyncio.Queue, or collections.deque
           If blobfolder is given, received blobs will be saved to that folder and the appropriate
           member.filename will be set to the last filename saved
        """
        super().__init__(indihost, indiport, txque=txque, rxque=rxque)
        # self.clientdata will contain keys txque, rxque

        if blobfolder:
            self.BLOBfolder = blobfolder


    async def _set_rxque_item(self, eventtype, devicename, vectorname, timestamp):
        """This generates and adds an EventItem to rxque,
           where an EventItem is a named tuple with attributes:

           eventtype -  a string, one of Message, getProperties, Delete, Define, DefineBLOB, Set, SetBLOB,
                        snapshot, TimeOut, State, ConnectionMade, ConnectionLost.
                        The first seven indicate data is received from the client, and the type of event.
                        "snapshot", is a response to a snapshot request received from txque.
                        "TimeOut" indicates an expected update has not occurred
                        "State" indicates you have just transmitted a new vector, and
                        therefore the snapshot will have your vector state set to Busy.
                        "ConnectionMade", "ConnectionLost" are self explanotary.
           devicename - usually the device name causing the event, or None if not applicable.
           vectorname - usually the vector name causing the event, or None if not applicable.
           timestamp -  the event timestamp, None for the snapshot request.
           snapshot -   For anything other than eventtype 'snapshot' it will be a full snapshot of the client.
                        If the eventtype is 'snapshot' and devicename and vectorname are None, it will be a
                        client snapshot, if devicename only is given it will be a device snapshot, or if both
                        devicename and vectorname are given it will be a vector snapshot."""
        rxque = self.clientdata['rxque']
        if eventtype == "snapshot":
            if devicename:
                if vectorname:
                    item = EventItem("snapshot", devicename, vectorname, None, self[devicename][vectorname].snapshot())
                else:
                    item = EventItem("snapshot", devicename, None, None, self[devicename].snapshot())
            else:
                item = EventItem("snapshot", None, None, None, self.snapshot())
        else:
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
            while not self._stop:
                try:
                    await asyncio.wait_for(rxque.put(item), 0.1)
                except asyncio.TimeoutError:
                    # queue is full, continue while loop, checking stop flag
                    continue
                else:
                    break
        elif isinstance(rxque, collections.deque):
            # append item to right side of rxque
            rxque.append(item)
        else:
            raise TypeError("rxque should be either a queue.Queue, asyncio.Queue, or collections.deque")


    async def rxevent(self, event):
        """On being called when an event is received, this calls self._set_rxque_item
           to generate and add an EventItem to rxque"""

        # set this event into rxque
        await self._set_rxque_item(event.eventtype, event.devicename, event.vectorname, event.timestamp)


    async def hardware(self):
        """Read txque and send data to server

           The item passed in the queue could be None, which indicates the client should shut down.
           Otherwise it should be a list or tuple of three members: (devicename, vectorname, value)

           The value could be a string, one of  "snapshot", "Get", "Never", "Also", or "Only".

           If the value is the string "snapshot" this is a request for the current snapshot, which will
           be returned via the rxque. In this case if devicename and vectorname are specified the snapshot
           will be for the approprate devie or vector, if both are None it will be a full client snapshot.

           If the value is the string "Get", then a getProperties will be sent to the server.

           If the value is one of "Never", "Also", or "Only" then an enableBLOB with this value will be sent.

           Otherwise the value should be a membername to membervalue dictionary, which will be transmitted to the server.

           If the specified vector is a BLOB Vector, the value dictionary should be {membername:(blobvalue, blobsize, blobformat)...}
           where blobvalue could be either a bytes object or a filepath.

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
                    item = await asyncio.wait_for(txque.get(), timeout=0.1)
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
            if len(item) != 3:
                # invalid item
                continue

            # item 0 is devicename or None
            # item 1 is vectorname or None
            # item 2 is a value

            if item[2] == "snapshot":
                # The queue is requesting a snapshot
                if item[0]:  # devicename
                    if item[1]: # vectorname
                        await self._set_rxque_item("snapshot", item[0], item[1], None)
                    else:
                        await self._set_rxque_item("snapshot", item[0], None, None)
                else:
                    await self._set_rxque_item("snapshot", None, None, None)
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
       If blobfolder is given, received blobs will be saved to that folder and the
       appropriate member.filename will be set to the last filename saved"""

    # create a QueClient object
    client = QueClient(txque, rxque, indihost, indiport, blobfolder)
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
