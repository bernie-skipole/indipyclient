import asyncio, queue, threading, collections




from .ipyclient import IPyClient


EventItem = collections.namedtuple('EventItem', ['eventtype', 'devicename', 'vectorname', 'timestamp', 'snapshot'])


class QueClient(IPyClient):

    """Overrides IPyClient
       On receiving an event, appends a snapshot into self.rxque
       Gets contents of self.txque and transmits updates"""


    async def rxevent(self, event):
        """Add EventItem to rxque, where an EventItem is a named tuple with attributes:
           eventtype - one of .....
           devicename
           vectorname
           timestamp
           snapshot
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
           Item passed in the queue should be a tuple or list of (devicename, vectorname, value)
           where value is normally a membername to membervalue dictionary
           If value is a string, one of  "Never", "Also", "Only" then an enableBLOB will be sent
           If the item is None, this indicates the client should shut down"""
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
                item = EventItem(None, None, None, None, self.snapshot())
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
    """Blocking call which runs a QueClient, typically run in a thread.

       This is used by first creating two queues
       rxque = queue.Queue(maxsize=4)
       txque = queue.Queue(maxsize=4)

       Then run the client in its own thread
       clientapp = threading.Thread(target=runqueclient, args=(txque, rxque))
       clientapp.start()

       Then run your own code, reading rxque, and transmitting on txque.

       Use txque.put(None) to shut down the queclient.

       Finally wait for the clientapp thread to stop
       clientapp.join()
       """
    # create a QueClient object
    client = QueClient(indihost, indiport, txque=txque, rxque=rxque)
    asyncio.run(client.asyncrun())


