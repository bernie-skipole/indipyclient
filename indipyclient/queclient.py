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

    def __init__(self, txque, rxque, indihost="localhost", indiport=7624):
        """txque and rxque should be instances of one of queue.Queue, asyncio.Queue, or collections.deque"""
        super().__init__(indihost, indiport, txque=txque, rxque=rxque)


    async def _set_rxque_item(self, eventtype, devicename, vectorname, timestamp, snapshot):
        rxque = self.clientdata['rxque']
        item = EventItem(eventtype, devicename, vectorname, timestamp, snapshot)
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

        await self._set_rxque_item(event.eventtype, event.devicename, event.vectorname, event.timestamp, self.snapshot())


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
                await self._set_rxque_item("snapshot", None, None, None, self.snapshot())
                continue
            if len(item) != 3:
                # invalid item
                continue
            if item[2] in ("Never", "Also", "Only"):
                await self.send_enableBLOB(item[2], item[0], item[1])
            else:
                timestamp = datetime.now(tz=timezone.utc)
                await self.send_newVector(item[0], item[1], timestamp, members=item[2])
                # a send_newVector will cause a State response
                await self._set_rxque_item("State", item[0], item[1], timestamp, self.snapshot())



def runqueclient(txque, rxque, indihost="localhost", indiport=7624):
    """Blocking call which creates a QueClient object and runs its
       asyncrun method."""
    # create a QueClient object
    client = QueClient(txque, rxque, indihost, indiport)
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
#  clientthread.join()
