
import collections, datetime, sys

import asyncio

import xml.etree.ElementTree as ET

from .propertymembers import SwitchMember, LightMember, TextMember, NumberMember, BLOBMember

from .error import ParseException, reporterror


class Vector(collections.UserDict):

    def __init__(self, name, label, group, state, timestamp, message):
        super().__init__()

        self.name = name
        self.label = label
        self.group = group
        self._state = state
        self.timestamp = timestamp
        self.message = message
        self.vectortype = None
        self.devicename = None
        self._rule = None
        self._perm = None
        self.timeout = None

        # this is a dictionary of member name to member this vector owns
        self.data = {}

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def rule(self):
        return self._rule

    @rule.setter
    def rule(self, value):
        self._rule = value

    @property
    def perm(self):
        return self._perm

    @perm.setter
    def perm(self, value):
        self._perm = value

    def __setitem__(self, membername, value):
        self.data[membername].membervalue = value

    def __getitem__(self, membername):
        return self.data[membername].membervalue

    def members(self):
        "Returns a dictionary of member objects"
        return self.data



class PropertyVector(Vector):
    "Parent class of SwitchVector etc.."

    def __init__(self, name, label, group, state, timestamp, message, device, client):
        super().__init__(name, label, group, state, timestamp, message)
        self.vectortype = self.__class__.__name__
        self._client = client
        self.device = device
        self.devicename = device.devicename
        # if self.enable is False, this property ignores incoming traffic
        self.enable = True


    def checkvalue(self, value, allowed):
        "allowed is a list of values, checks if value is in it"
        if value not in allowed:
            raise ParseException
        return value

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = self.checkvalue(value, ['Idle','Ok','Busy','Alert'])


    def __setitem__(self, membername, value):
        "Members are added by being learnt from the driver, they cannot be manually added"
        raise KeyError

    def __getitem__(self, membername):
        return self.data[membername].membervalue

    def _setvector(self, event):
        "Updates this vector with new values after a set... vector has been received"
        if event.state:
            self.state = event.state
        if event.timestamp:
            self.timestamp = event.timestamp
        if event.message:
            self.message = event.message
        if hasattr(event, 'timeout') and event.timeout:
            self.timeout = event.timeout
        for membername, membervalue in event.items():
            member = self.data[membername]
            member.membervalue = membervalue


    def _snapshot(self):
        snapvector = Vector(self.name, self.label, self.group, self.state, self.timestamp, self.message)
        snapvector.vectortype = self.vectortype
        snapvector.devicename = self.devicename
        if hasattr(self, 'rule'):
            snapvector.rule = self.rule
        if hasattr(self, 'perm'):
            snapvector.perm = self.perm
        if hasattr(self, 'timeout'):
            snapvector.timeout = self.timeout
        for membername, member in self.data:
            snapvector.data[membername] = member._snapshot()
        return snapvector


class SwitchVector(PropertyVector):

    """A SwitchVector sends and receives one or more members with values 'On' or 'Off'. It
       also has the extra attribute 'rule' which can be one of 'OneOfMany', 'AtMostOne', 'AnyOfMany'.
       These are hints to the client how to display the switches in the vector.

       OneOfMany - of the SwitchMembers in this vector, one (and only one) must be On.

       AtMostOne - of the SwitchMembers in this vector, one or none can be On.

       AnyOfMany - multiple switch members can be On.
       """

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state,
                         event.timestamp, event.message, event.device, event._client)
        self._perm = event.perm
        self._rule = event.rule
        self.timeout = event.timeout
        # self.data is a dictionary of switch name : switchmember
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = SwitchMember(membername, event.memberlabels[membername], membervalue)

    @property
    def perm(self):
        return self._perm

    @perm.setter
    def perm(self, value):
        self._perm = self.checkvalue(value, ['ro','wo','rw'])

    @property
    def rule(self):
        return self._rule

    @rule.setter
    def rule(self, value):
        self._rule = self.checkvalue(value, ['OneOfMany','AtMostOne','AnyOfMany'])


    def _defvector(self, event):
        "Updates this vector with new values after a def... vector has been received"
        if event.label:
            self.label = event.label
        if event.group:
            self.group = event.group
        if event.perm:
            self.perm = event.perm
        if event.rule:
            self.rule = event.rule
        if event.state:
            self.state = event.state
        if event.timestamp:
            self.timestamp = event.timestamp
        if event.message:
            self.message = event.message
        if event.timeout:
            self.timeout = event.timeout
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = SwitchMember(membername, event.memberlabels[membername], membervalue)

    def _newSwitchVector(self, timestamp=None, members={}):
        "Creates the xmldata for sending a newSwitchVector"
        if not self.device.enable:
            return
        if not self.enable:
            return
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            reporterror("Aborting sending newSwitchVector: The newSwitchVector timestamp must be a datetime.datetime object")
            return
        self.state = 'Busy'
        xmldata = ET.Element('newSwitchVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        # set member values to send
        sendvalues = {}
        for membername, value in members.items():
            # check this membername exists
            if membername in self:
                sendvalues[membername] = value
        # for rule 'OneOfMany' the standard indicates 'Off' should precede 'On'
        # so make all 'On' values last
        Offswitches = []
        Onswitches = []
        for mname, value in sendvalues.items():
            if value == 'Off':
                # create list of (memberswitch, new value) tuples
                Offswitches.append( ( self.data[mname], value ) )
            elif value == 'On':
               Onswitches.append( ( self.data[mname], value ) )
        for switch,value in Offswitches:
            xmldata.append(switch.oneswitch(value))
        for switch, value in Onswitches:
            xmldata.append(switch.oneswitch(value))
        return xmldata


    def send_newSwitchVector(self, timestamp=None, members={}):
        """Transmits the vector (newSwitchVector) and the members given in the members
           dictionary which consists of member names:values to be sent.
           This method will transmit the xml, and change the vector state to busy."""
        xmldata = self._newSwitchVector(timestamp, members)
        if xmldata is None:
            return
        self._client.send(xmldata)


class LightVector(PropertyVector):

    """A LightVector is an instrument indicator, and has one or more members
       with values 'Idle', 'Ok', 'Busy' or 'Alert'. In general a client will
       indicate this state with different colours.

       This class has no 'send_newLightVector method, since lights are read-only"""

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state,
                         event.timestamp, event.message, event.device, event._client)
        self._perm = "ro"
        # self.data is a dictionary of light name : lightmember
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = LightMember(membername, event.memberlabels[membername], membervalue)

    @property
    def perm(self):
        return "ro"

    @perm.setter
    def perm(self, value):
        pass


    def _defvector(self, event):
        "Updates this vector with new values after a def... vector has been received"
        if event.label:
            self.label = event.label
        if event.group:
            self.group = event.group
        if event.state:
            self.state = event.state
        if event.timestamp:
            self.timestamp = event.timestamp
        if event.message:
            self.message = event.message
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = LightMember(membername, event.memberlabels[membername], membervalue)

    def _snapshot(self):
        snapvector = PropertyVector._snapshot(self)
        snapvector.perm = "ro"
        return snapvector



class TextVector(PropertyVector):

    """A TextVector is used to send and receive text between instrument and client."""


    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state,
                         event.timestamp, event.message, event.device, event._client)
        self._perm = event.perm
        self.timeout = event.timeout
        # self.data is a dictionary of text name : textmember
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = TextMember(membername, event.memberlabels[membername], membervalue)

    @property
    def perm(self):
        return self._perm

    @perm.setter
    def perm(self, value):
        self._perm = self.checkvalue(value, ['ro','wo','rw'])

    def _defvector(self, event):
        "Updates this vector with new values after a def... vector has been received"
        if event.label:
            self.label = event.label
        if event.group:
            self.group = event.group
        if event.perm:
            self.perm = event.perm
        if event.state:
            self.state = event.state
        if event.timestamp:
            self.timestamp = event.timestamp
        if event.message:
            self.message = event.message
        if event.timeout:
            self.timeout = event.timeout
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = TextMember(membername, event.memberlabels[membername], membervalue)


    def _newTextVector(self, timestamp=None, members={}):
        "Creates the xmldata for sending a newTextVector"
        if not self.device.enable:
            return
        if not self.enable:
            return
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            reporterror("Aborting sending newTextVector: The send_newTextVector timestamp must be a datetime.datetime object")
            return
        self.state = 'Busy'
        xmldata = ET.Element('newTextVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        # set member values to send
        for membername, textmember in self.data.items():
            if membername in members:
                xmldata.append(textmember.onetext(members[membername]))
            else:
                xmldata.append(textmember.onetext(textmember.membervalue))
        return xmldata


    def send_newTextVector(self, timestamp=None, members={}):
        """Transmits the vector (newTextVector) together with all text members.
           (The spec requires text vectors to be sent with all members)
           This method will transmit the vector and change the vector state to busy."""
        xmldata = self._newTextVector(timestamp, members)
        if xmldata is None:
            return
        self._client.send(xmldata)


class NumberVector(PropertyVector):

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state,
                         event.timestamp, event.message, event.device, event._client)
        self._perm = event.perm
        self.timeout = event.timeout
        # self.data is a dictionary of number name : numbermember
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = NumberMember(membername, *event.memberlabels[membername], membervalue)

    def getfloatvalue(self, membername):
        "Given a membername of this vector, returns the number as a float"
        if membername not in self:
            raise KeyError(f"Unrecognised member: {membername}")
        member = self.data[membername]
        return member.getfloatvalue()

    def getformattedvalue(self, membername):
        "Given a membername of this vector, returns the number as a formatted string"
        if membername not in self:
            raise KeyError(f"Unrecognised member: {membername}")
        member = self.data[membername]
        return member.getformattedvalue()

    @property
    def perm(self):
        return self._perm

    @perm.setter
    def perm(self, value):
        self._perm = self.checkvalue(value, ['ro','wo','rw'])

    def _defvector(self, event):
        "Updates this vector with new values after a def... vector has been received"
        if event.label:
            self.label = event.label
        if event.group:
            self.group = event.group
        if event.perm:
            self.perm = event.perm
        if event.state:
            self.state = event.state
        if event.timestamp:
            self.timestamp = event.timestamp
        if event.message:
            self.message = event.message
        if event.timeout:
            self.timeout = event.timeout
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = NumberMember(membername, *event.memberlabels[membername], membervalue)


    def _newNumberVector(self, timestamp=None, members={}):
        "Creates the xmldata for sending a newNumberVector"
        if not self.device.enable:
            return
        if not self.enable:
            return
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            reporterror("Aborting sending newNumberVector: The send_newNumberVector timestamp must be a datetime.datetime object")
            return
        self.state = 'Busy'
        xmldata = ET.Element('newNumberVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        # set member values to send
        for membername, numbermember in self.data.items():
            if membername in members:
                xmldata.append(numbermember.onenumber(members[membername]))
            else:
                xmldata.append(numbermember.onenumber(numbermember.membervalue))
        return xmldata

    def send_newNumberVector(self, timestamp=None, members={}):
        """Transmits the vector (newNumberVector) with new number members
           togther with any unchanged numbers.
           (The spec requires number vectors to be sent with all members)
           This method will transmit the vector and change the vector state to busy."""
        xmldata = self._newNumberVector(timestamp, members)
        if xmldata is None:
            return
        self._client.send(xmldata)



class BLOBVector(PropertyVector):

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state,
                         event.timestamp, event.message, event.device, event._client)
        self._perm = event.perm
        self.timeout = event.timeout
        # self.data is a dictionary of blob name : blobmember
        # create  members
        for membername, label in event.memberlabels.items():
            self.data[membername] = BLOBMember(membername, label)



    def set_blobsize(self, membername, blobsize):
        """Sets the size attribute in the blob member. If the default of zero is used,
           the size will be set to the number of bytes in the BLOB. The INDI standard
           specifies the size should be that of the BLOB before any compression,
           therefore if you are sending a compressed file, you should set the blobsize
           prior to compression with this method."""
        if not isinstance(blobsize, int):
            reporterror("blobsize rejected, must be an integer object")
            return
        member = self.data.get[membername]
        if not member:
            return
        member.blobsize = blobsize

    @property
    def perm(self):
        return self._perm

    @perm.setter
    def perm(self, value):
        self._perm = self.checkvalue(value, ['ro','wo','rw'])

    def _defvector(self, event):
        "Updates this vector with new values after a def... vector has been received"
        if event.label:
            self.label = event.label
        if event.group:
            self.group = event.group
        if event.perm:
            self.perm = event.perm
        if event.state:
            self.state = event.state
        if event.timestamp:
            self.timestamp = event.timestamp
        if event.message:
            self.message = event.message
        if event.timeout:
            self.timeout = event.timeout
        # create  members
        for membername, label in event.memberlabels.items():
            self.data[membername] = BLOBMember(membername, label)
