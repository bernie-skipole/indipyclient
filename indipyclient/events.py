
import sys

from datetime import datetime, timezone

from base64 import standard_b64decode

from collections import UserDict

import xml.etree.ElementTree as ET

from . import propertyvectors

from . import propertymembers

from .error import ParseException



def _parse_timestamp(timestamp_string):
    """Parse a timestamp string and return either None on failure, or a datetime object
       If the given timestamp_string is None, return the datetime for the current time.
       Everything is UTC"""
    if timestamp_string:
        try:
            if '.' in timestamp_string:
                # remove fractional part, not supported by datetime.fromisoformat
                timestamp_string, remainder = timestamp_string.rsplit('.', maxsplit=1)
                if len(remainder) < 6:
                    remainder = "{:<06}".format(remainder)
                elif len(remainder) > 6:
                    remainder = remainder[:6]
                remainder = int(remainder)
                timestamp = datetime.fromisoformat(timestamp_string)
                timestamp = timestamp.replace(microsecond=remainder, tzinfo=timezone.utc)
            else:
                timestamp = datetime.fromisoformat(timestamp_string)
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except:
            timestamp = None
    else:
        timestamp = datetime.now(tz=timezone.utc)
    return timestamp


class Event:
    "Parent class for events received from drivers"
    def __init__(self, root, device, client):
        self.device = device
        self._client = client
        self.vectorname = None
        if device is None:
            self.devicename = None
        else:
            self.devicename = self.device.devicename
        self.root = root
        self.timestamp = _parse_timestamp(root.get("timestamp"))

    def __str__(self):
        return ET.tostring(self.root, encoding='unicode')



class Message(Event):
    """This contains attribute 'message' with the message string sent by the remote driver.
       Attribute devicename could be None if the driver is sending a system wide message."""

    def __init__(self, root, device, client):
        super().__init__(root, device, client)
        self.message = root.get("message", "")
        if device is None:
            # state wide message
            client.messages.appendleft( (self.timestamp, self.message) )
        else:
            device.messages.appendleft( (self.timestamp, self.message) )


class delProperty(Event):
    """The remote driver is instructing the client to delete either a device or a vector property.
       This contains attribute vectorname, if it is None, then the whole device is to be deleted.
       A 'message' attribute contains any message sent by the client with this instruction."""

    def __init__(self, root, device, client):
        super().__init__(root, device, client)
        if self.devicename is None:
            raise ParseException
        if not self.device.enable:
            # already deleted
            raise ParseException
        self.vectorname = root.get("name")
        self.message = root.get("message", "")
        # properties is a dictionary of property name to propertyvector this device owns
        # This method updates a property vector and sets it into properties
        properties = device.data
        if self.vectorname:
            # does this vector already exist, if it does, disable it
            if vector := properties.get(self.vectorname):
                vector.enable = False
        else:
            # No vectorname given, disable all properties
            for vector in properties.values():
                vector.enable = False


class defVector(Event, UserDict):
    "Parent to def vectors, adds a mapping of membername:value"
    def __init__(self, root, device, client):
        Event.__init__(self, root, device, client)
        UserDict.__init__(self)
        self.vectorname = root.get("name")
        if self.vectorname is None:
            raise ParseException
        self.label = root.get("label", self.vectorname)
        self.group = root.get("group", "DEFAULT GROUP")
        state = root.get("state")
        if not state:
            raise ParseException
        if not state in ('Idle','Ok','Busy','Alert'):
            raise ParseException
        self.state = state
        self.message = root.get("message", "")


    def __setitem__(self, membername):
        raise KeyError


class defSwitchVector(defVector):

    """The remote driver has sent this to define a switch vector property, it has further
       attributes perm, rule, timeout, and memberlabels which is a dictionary of
       membername:label."""

    def __init__(self, root, device, client):
        defVector.__init__(self, root, device, client)
        self.perm = root.get("perm")
        if self.perm is None:
            raise ParseException
        if self.perm not in ('ro', 'wo', 'rw'):
            raise ParseException
        self.rule = root.get("rule")
        if self.rule is None:
            raise ParseException
        if self.rule not in ('OneOfMany', 'AtMostOne', 'AnyOfMany'):
            raise ParseException
        self.timeout = root.get("timeout")
        # create object dictionary of member name to value
        # and another dictionary of self.memberlabels with key member name and value being label
        self.memberlabels = {}
        for member in root:
            if member.tag == "defSwitch":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                label = member.get("label", membername)
                self.memberlabels[membername] = label
                value = member.text.strip()
                if value == "On":
                    self.data[membername] = "On"
                elif value == "Off":
                    self.data[membername] = "Off"
                else:
                    raise ParseException
            else:
                raise ParseException
        if not self.data:
            raise ParseException

        # properties is a dictionary of property name to propertyvector this device owns
        # This method updates a property vector and sets it into properties
        properties = device.data

        # does this vector already exist
        if self.vectorname in properties:
            self.vector = properties[self.vectorname]
            # set changed values into self.vector by calling vector._defvector
            # with this event as its argument
            self.vector._defvector(self)
        else:
            # create a new SwitchVector
            self.vector = propertyvectors.SwitchVector(self)
            # add it to properties
            properties[self.vectorname] = self.vector


class defTextVector(defVector):

    """The remote driver has sent this to define a text vector property, it has further
       attributes perm, timeout, and memberlabels which is a dictionary of
       membername:label."""

    def __init__(self, root, device, client):
        defVector.__init__(self, root, device, client)
        self.perm = root.get("perm")
        if self.perm is None:
            raise ParseException
        if self.perm not in ('ro', 'wo', 'rw'):
            raise ParseException
        self.timeout = root.get("timeout")
        # create object dictionary of member name to value
        # and another dictionary of self.memberlabels with key member name and value being label
        self.memberlabels = {}
        for member in root:
            if member.tag == "defText":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                label = member.get("label", membername)
                self.memberlabels[membername] = label
                self.data[membername] = member.text
            else:
                raise ParseException
        if not self.data:
            raise ParseException

        # properties is a dictionary of property name to propertyvector this device owns
        # This method updates a property vector and sets it into properties
        properties = device.data

        # does this vector already exist
        if self.vectorname in properties:
            self.vector = properties[self.vectorname]
            # set changed values into self.vector by calling vector._defvector
            # with this event as its argument
            self.vector._defvector(self)
        else:
            # create a new TextVector
            self.vector = propertyvectors.TextVector(self)
            # add it to properties
            properties[self.vectorname] = self.vector




class defNumberVector(defVector):

    """The remote driver has sent this to define a number vector property, it has further
       attributes perm, timeout, and memberlabels which is a dictionary of
       membername:(label, format, min, max, step)."""

    def __init__(self, root, device, client):
        defVector.__init__(self, root, device, client)
        self.perm = root.get("perm")
        if self.perm is None:
            raise ParseException
        if self.perm not in ('ro', 'wo', 'rw'):
            raise ParseException
        self.timeout = root.get("timeout")
        # create object dictionary of member name to value
        # and another dictionary of self.memberlabels with key member name and
        # value being a tuple of (label, format, min, max, step)
        self.memberlabels = {}
        for member in root:
            if member.tag == "defNumber":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                label = member.get("label", membername)
                memberformat = member.get("format")
                if not memberformat:
                    raise ParseException
                membermin = member.get("min")
                if not membermin:
                    raise ParseException
                membermax = member.get("max")
                if not membermax:
                    raise ParseException
                memberstep = member.get("step")
                if not memberstep:
                    raise ParseException
                self.memberlabels[membername] = (label, memberformat, membermin, membermax, memberstep)
                self.data[membername] = member.text.strip()
            else:
                raise ParseException
        if not self.data:
            raise ParseException


        # properties is a dictionary of property name to propertyvector this device owns
        # This method updates a property vector and sets it into properties
        properties = device.data

        # does this vector already exist
        if self.vectorname in properties:
            self.vector = properties[self.vectorname]
            # set changed values into self.vector
            self.vector._defvector(self)

        else:
            # create a new NumberVector
            self.vector = propertyvectors.NumberVector(self)
            # add it to properties
            properties[self.vectorname] = self.vector



class defLightVector(defVector):

    """The remote driver has sent this to define a light vector property, it has further
       attribute memberlabels which is a dictionary of membername:label."""

    def __init__(self, root, device, client):
        defVector.__init__(self, root, device, client)
        # create object dictionary of member name to value
        # and another dictionary of self.memberlabels with key member name and value being label
        self.memberlabels = {}
        for member in root:
            if member.tag == "defLight":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                label = member.get("label", membername)
                self.memberlabels[membername] = label
                value = member.text.strip()
                if not value in ('Idle','Ok','Busy','Alert'):
                    raise ParseException
                self.data[membername] = value
            else:
                raise ParseException
        if not self.data:
            raise ParseException


        # properties is a dictionary of property name to propertyvector this device owns
        # This method updates a property vector and sets it into properties
        properties = device.data

        # does this vector already exist
        if self.vectorname in properties:
            self.vector = properties[self.vectorname]
            # set changed values into self.vector by calling vector._defvector
            # with this event as its argument
            self.vector._defvector(self)
        else:
            # create a new LightVector
            self.vector = propertyvectors.LightVector(self)
            # add it to properties
            properties[self.vectorname] = self.vector



class defBLOBVector(Event):

    """The remote driver has sent this to define a BLOB vector property, it has further
       attributes perm, timeout, and memberlabels which is a dictionary of
       membername:label.

       However this class does not have an object mapping of member name to value, since
       values are not given in defBLOBVectors"""

    def __init__(self, root, device, client):
        Event.__init__(self, root, device, client)
        if self.devicename is None:
            raise ParseException
        self.vectorname = root.get("name")
        if self.vectorname is None:
            raise ParseException
        self.label = root.get("label", self.vectorname)
        self.group = root.get("group", "DEFAULT GROUP")
        state = root.get("state")
        if not state:
            raise ParseException
        if not state in ('Idle','Ok','Busy','Alert'):
            raise ParseException
        self.state = state
        self.message = root.get("message", "")
        self.perm = root.get("perm")
        if self.perm is None:
            raise ParseException
        if self.perm not in ('ro', 'wo', 'rw'):
            raise ParseException
        self.timeout = root.get("timeout")
        # create a dictionary of self.memberlabels with key member name and value being label
        self.memberlabels = {}
        for member in root:
            if member.tag == "defBLOB":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                label = member.get("label", membername)
                self.memberlabels[membername] = label
            else:
                raise ParseException(f"Invalid child tag {member.tag} of defBLOBVector received")
        if not self.memberlabels:
            raise ParseException

        # properties is a dictionary of property name to propertyvector this device owns
        # This method updates a property vector and sets it into properties
        properties = device.data

        # does this vector already exist
        if self.vectorname in properties:
            self.vector = properties[self.vectorname]
            # set changed values into self.vector by calling vector._defvector
            # with this event as its argument
            self.vector._defvector(self)
        else:
            # create a new BLOBVector
            self.vector = propertyvectors.BLOBVector(self)
            # add it to properties
            properties[self.vectorname] = self.vector


class setVector(Event, UserDict):
    "Parent to set vectors, adds dictionary"
    def __init__(self, root, device, client):
        Event.__init__(self, root, device, client)
        UserDict.__init__(self)
        if self.devicename is None:
            raise ParseException
        self.vectorname = root.get("name")
        if self.vectorname is None:
            raise ParseException
        # This vector must already exist, properties is a dictionary of property name to propertyvector this device owns
        properties = device.data
        # if it exists, check enable status
        if vector := properties.get(self.vectorname):
            if not vector.enable:
                raise ParseException
        else:
            raise ParseException
        state = root.get("state")
        if state and (state in ('Idle','Ok','Busy','Alert')):
            self.state = state
        else:
            self.state = None
        self.message = root.get("message", "")

    def __setitem__(self, membername):
        raise KeyError



class setSwitchVector(setVector):
    """The remote driver is setting a Switch vector property, this
       has further attribute timeout."""

    def __init__(self, root, device, client):
        setVector.__init__(self, root, device, client)
        self.timeout = root.get("timeout")
        # create a dictionary of member name to value
        for member in root:
            if member.tag == "oneSwitch":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                value = member.text.strip()
                if value == "On":
                    self.data[membername] = "On"
                elif value == "Off":
                    self.data[membername] = "Off"
                else:
                    raise ParseException
            else:
                raise ParseException
        if not self.data:
            raise ParseException
        properties = device.data
        self.vector = properties[self.vectorname]
        # set changed values into self.vector
        self.vector._setvector(self)


class setTextVector(setVector):

    """The remote driver is setting a Text vector property, this
       has further attribute timeout."""

    def __init__(self, root, device, client):
        setVector.__init__(self, root, device, client)
        self.timeout = root.get("timeout")
        # create a dictionary of member name to value
        for member in root:
            if member.tag == "oneText":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                self.data[membername] = member.text
            else:
                raise ParseException
        if not self.data:
            raise ParseException
        properties = device.data
        self.vector = properties[self.vectorname]
        # set changed values into self.vector
        self.vector._setvector(self)


class setNumberVector(setVector):

    """The remote driver is setting a Number vector property, this
       has further attribute timeout. The number values of the
       membername:membervalue are string values."""

    def __init__(self, root, device, client):
        setVector.__init__(self, root, device, client)
        self.timeout = root.get("timeout")
        # create a dictionary of member name to value
        for member in root:
            if member.tag == "oneNumber":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                self.data[membername] = member.text.strip()
            else:
                raise ParseException
        if not self.data:
            raise ParseException
        properties = device.data
        self.vector = properties[self.vectorname]
        # set changed values into self.vector
        self.vector._setvector(self)


class setLightVector(setVector):

    """The remote driver is setting a Light vector property."""

    def __init__(self, root, device, client):
        setVector.__init__(self, root, device, client)
        # create a dictionary of member name to value
        for member in root:
            if member.tag == "oneLight":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                value = member.text.strip()
                if not value in ('Idle','Ok','Busy','Alert'):
                    raise ParseException
                self.data[membername] = value
            else:
                raise ParseException
        if not self.data:
            raise ParseException
        properties = device.data
        self.vector = properties[self.vectorname]
        # set changed values into self.vector
        self.vector._setvector(self)


class setBLOBVector(setVector):

    """The remote driver is setting a BLOB vector property, this
       has further attributes timeout and sizeformat which is a dictionary
       of membername:(size, format)."""

    def __init__(self, root, device, client):
        setVector.__init__(self, root, device, client)
        self.timeout = root.get("timeout")
        # create a dictionary of member name to value
        # and dictionary sizeformat
        # with key member name and value being a tuple of size, format
        self.sizeformat = {}
        for member in root:
            if member.tag == "oneBLOB":
                membername = member.get("name")
                if not membername:
                    raise ParseException
                membersize = member.get("size")
                if not membersize:
                    raise ParseException
                memberformat = member.get("format")
                if not memberformat:
                    raise ParseException
                try:
                    self.data[membername] = standard_b64decode(member.text.encode('ascii'))
                    memberize = int(member.get("size"))
                except:
                    raise ParseException
                self.sizeformat[membername] = (membersize, memberformat)
            else:
                raise ParseException
        if not self.data:
            raise ParseException
        properties = device.data
        self.vector = properties[self.vectorname]
        # set changed values into self.vector
        self.vector._setvector(self)
