
import asyncio, threading, math, collections

class Snap():
    """An instance is created and is available as client.snap, its methods
       may be useful if synchronous operations are required"""

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
        """Synchronous version to send a new Vector, note members is a membername to value dictionary,
           It could also be a vector, which is itself a membername to value mapping"""
        if devicename not in self._client:
            reporterror(f"Failed to send vector: Device {devicename} not recognised")
            return
        device = self._client[devicename]
        if vectorname not in device:
            reporterror(f"Failed to send vector: Vector {vectorname} not recognised")
            return
        try:
            propertyvector = device[vectorname]
            if propertyvector.vectortype == "SwitchVector":
                sendcoro = propertyvector.send_newSwitchVector(timestamp, members)
            elif propertyvector.vectortype == "TextVector":
                sendcoro = propertyvector.send_newTextVector(timestamp, members)
            elif propertyvector.vectortype == "NumberVector":
                sendcoro = propertyvector.send_newNumberVector(timestamp, members)
            elif propertyvector.vectortype == "BLOBVector":
                sendcoro = propertyvector.send_newBLOBVector(timestamp, members)
            else:
                reporterror(f"Failed to send invalid vector with devicename:{devicename}, vectorname:{vectorname}")
                return
            future = asyncio.run_coroutine_threadsafe(sendcoro,
                                                  self._client.loop)
            future.result()
        except Exception:
            reporterror(f"Failed to send vector with devicename:{devicename}, vectorname:{vectorname}")


    def send_getProperties(self, devicename=None, vectorname=None):
        "Synchronous version of send_getProperties"
        sendcoro = self._client.send_getProperties(devicename, vectorname)
        future = asyncio.run_coroutine_threadsafe(sendcoro, self._client.loop)
        future.result()


    def send_enableBLOB(self, value, devicename, vectorname=None):
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

    def __init__(self, vectortype, devicename, name, label, group, state, timestamp, message):
        super().__init__()

        self.vectortype = vectortype
        self.devicename = devicename
        self.name = name
        self.label = label
        self.group = group
        self.state = state
        self.timestamp = timestamp
        self.message = message
        self.rule = None
        self.perm = None
        self.timeout = None

        # this is a dictionary of member name to member this vector owns
        self.data = {}

    def __setitem__(self, membername, value):
        self.data[membername].membervalue = value

    def __getitem__(self, membername):
        return self.data[membername].membervalue

    def members(self):
        "Returns a dictionary of member objects"
        return self.data


class Member():

    def __init__(self, name, label=None, membervalue=None):
        self.name = name
        if label:
            self.label = label
        else:
            self.label = name
        self.membervalue = membervalue



class NumberMember(Member):

    def __init__(self, name, label=None, format='', min='0', max='0', step='0', membervalue='0'):
        super().__init__(name, label, membervalue)
        self.format = format
        self.min = min
        self.max = max
        self.step = step


    def getfloatvalue(self):
        """The INDI spec allows a number of different number formats, this returns a float.
           If an error occurs while parsing the number, a TypeError exception is raised."""
        value = self.membervalue
        try:
            if isinstance(value, float):
                return value
            if isinstance(value, int):
                return float(value)
            if not isinstance(value, str):
                raise TypeError
            # negative is True, if the value is negative
            value = value.strip()
            negative = value.startswith("-")
            if negative:
                value = value.lstrip("-")
            # Is the number provided in sexagesimal form?
            if value == "":
                parts = [0, 0, 0]
            elif " " in value:
                parts = value.split(" ")
            elif ":" in value:
                parts = value.split(":")
            elif ";" in value:
                parts = value.split(";")
            else:
                # not sexagesimal
                parts = [value, "0", "0"]
            # Any missing parts should have zero
            if len(parts) == 2:
                # assume seconds are missing, set to zero
                parts.append("0")
            assert len(parts) == 3
            number_strings = list(x if x else "0" for x in parts)
            # convert strings to integers or floats
            number_list = []
            for part in number_strings:
                try:
                    num = int(part)
                except ValueError:
                    num = float(part)
                number_list.append(num)
            floatvalue = number_list[0] + (number_list[1]/60) + (number_list[2]/360)
            if negative:
                floatvalue = -1 * floatvalue
        except:
            raise TypeError("Unable to parse the value")
        return floatvalue


    def getformattedvalue(self):
        """This returns a formatted string"""
        value = self.getfloatvalue()
        if (not self.format.startswith("%")) or (not self.format.endswith("m")):
            return self.format % value
        # sexagesimal format
        if value<0:
            negative = True
            value = abs(value)
        else:
            negative = False
        # number list will be degrees, minutes, seconds
        number_list = [0,0,0]
        if isinstance(value, int):
            number_list[0] = value
        else:
            # get integer part and fraction part
            fractdegrees, degrees = math.modf(value)
            number_list[0] = int(degrees)
            mins = 60*fractdegrees
            fractmins, mins = math.modf(mins)
            number_list[1] = int(mins)
            number_list[2] = 60*fractmins

        # so number list is a valid degrees, minutes, seconds
        # degrees
        if negative:
            number = f"-{number_list[0]}:"
        else:
            number = f"{number_list[0]}:"
        # format string is of the form  %<w>.<f>m
        w,f = self.format.split(".")
        w = w.lstrip("%")
        f = f.rstrip("m")
        if (f == "3") or (f == "5"):
            # no seconds, so create minutes value
            minutes = float(number_list[1]) + number_list[2]/60.0
            if f == "5":
                number += f"{minutes:04.1f}"
            else:
                number += f"{minutes:02.0f}"
        else:
            number += f"{number_list[1]:02d}:"
            seconds = float(number_list[2])
            if f == "6":
                number += f"{seconds:02.0f}"
            elif f == "8":
                number += f"{seconds:04.1f}"
            else:
                number += f"{seconds:05.2f}"

        # w is the overall length of the string, prepend with spaces to make the length up to w
        w = int(w)
        l = len(number)
        if w>l:
            number = " "*(w-l) + number
        return number
