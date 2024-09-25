"""
This module contains QueClient, which inherits from IPyClient and transmits
and receives data on two queues, together with function runqueclient.

This may be useful where the user prefers to write his own code in one thread,
and communicate via the queues to this client running in another thread.
"""



import asyncio, queue, collections

from .ipyclient import IPyClient


EventItem = collections.namedtuple('EventItem', ['eventtype', 'devicename', 'vectorname', 'timestamp', 'snapshot'])


class QueClient(IPyClient):

    """This inherits from IPyClient
       On receiving an event, appends an EventItem, which contains a client snapshot, into "rxque"
       Gets contents of "txque" and transmits updates"""


    async def rxevent(self, event):
        """Generates and adds an EventItem to rxque, where an EventItem is a named tuple with attributes:
           eventtype - a string, one of Message, getProperties, Delete, Define, DefineBLOB, Set, SetBLOB,
                       these indicate data is received from the client, and the type of event. It could
                       also be the string snapshot, which does not indicate a received event, but is a
                       response to a snapshot request received from txque.
           devicename - usually the device name causing the event, or None for a system message, or
                        for the snapshot request.
           vectorname - usually the vector name causing the event, or None for a system message, or
                        device message, or for the snapshot request.
           timestamp - the event timestamp, None for the snapshot request.
           snapshot - A Snap object, being a snapshot of the client, which has been updated by the event.
           """
        item = EventItem(event.eventtype, event.devicename, event.vectorname, event.timestamp, self.snapshot())
        while not self._stop:
            try:
                self.clientdata['rxque'].put_nowait(item)
            except queue.Full:
                await asyncio.sleep(0.02)
            else:
                break


    async def hardware(self):
        """Read txque and send data to server
           Item passed in the queue could be the string "snapshot" this is
           a request for the current snapshot, which will be sent via the rxque.
           If the item is None, this indicates the client should shut down.
           Otherwise the item should be a tuple or list of (devicename, vectorname, value)
           where value is normally a membername to membervalue dictionary, and these updates
           will be transmitted.
           If value is a string, one of  "Never", "Also", "Only" then an enableBLOB with this
           value will be sent.
           """
        while not self._stop:
            try:
                item = self.clientdata['txque'].get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.02)
                continue
            if item is None:
                # A None in the queue is a shutdown indicator
                self.shutdown()
                return
            if item == "snapshot":
                # The queue is requesting a snapshot
                item = EventItem("snapshot", None, None, None, self.snapshot())
                while not self._stop:
                    try:
                        self.clientdata['rxque'].put_nowait(item)
                    except queue.Full:
                        await asyncio.sleep(0.02)
                    else:
                        break
                continue
            if len(item) != 3:
                # invalid item
                continue
            if item[2] in ("Never", "Also", "Only"):
                await self.send_enableBLOB(item[2], item[0], item[1])
            else:
                await self.send_newVector(item[0], item[1], members=item[2])


def runqueclient(txque, rxque, indihost="localhost", indiport=7624):
    """Blocking call which runs a QueClient asyncio loop,
       This is typically run in a thread.

       This is used by first creating two queues
       rxque = queue.Queue(maxsize=4)
       txque = queue.Queue(maxsize=4)

       Then run the client in its own thread
       clientthread = threading.Thread(target=runqueclient, args=(txque, rxque))
       clientthread.start()

       Then run your own code, reading rxque, and transmitting on txque.

       Use txque.put(None) to shut down the queclient.

       Finally wait for the clientthread to stop
       clientthread.join()
       """
    # create a QueClient object
    client = QueClient(indihost, indiport, txque=txque, rxque=rxque)
    asyncio.run(client.asyncrun())
