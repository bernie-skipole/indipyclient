
import asyncio, threading

class SyncMethods():
    "An instance is created if synchronous operations are required"

    def __init__(self, client):
        self._client = client

    def snapshot(self):
        "Take snapshot of the devices"
        with threading.Lock():
            # other threads cannot change the client.data dictionary
            snap = {}
            if self._client.data:
                for devicename, device in self._client.data.items():
                    if not device.enable:
                        continue
                    snap[devicename] = device._snapshot()
        # other threads can now access client.data
        # return the snapshot
        return snap


    def send_newVector(self, devicename, vectorname, timestamp=None, members={}):
        "Synchronous version to send a new Vector"
        sendcoro = self._client.send_newVector(devicename, vectorname, timestamp, members)
        future = asyncio.run_coroutine_threadsafe(sendcoro,
                                                  self._client.loop)
        future.result()


    def send_getProperties(self, devicename=None, vectorname=None):
        "Synchronous version of send_getProperties"
        sendcoro = self._client.send_getProperties(devicename, vectorname)
        future = asyncio.run_coroutine_threadsafe(sendcoro, self._client.loop)
        future.result()


    def send_enableBLOB(self, value, devicename, vectorname=None)
        "Synchronous version of send_enableBLOB"
        sendcoro = self._client.send_enableBLOB(value, devicename, vectorname)
        future = asyncio.run_coroutine_threadsafe(sendcoro, self._client.loop)
        future.result()


class Device(collections.UserDict):

    def __init__(self, devicename):
        super().__init__()

        # This device name
        self.devicename = devicename

        # this is a dictionary of property name to propertyvector this device owns
        self.data = {}


class Vector(collections.UserDict):

    def __init__(self, vectortype, name, label, group, state):
        super().__init__()

        self.vectortype = vectortype
        self.name = name
        self.label = label
        self.group = group
        self.state = state
        self.rule = None
        self.perm = None

        # this is a dictionary of member name to member this vector owns
        self.data = {}
