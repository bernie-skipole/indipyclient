
import collections, datetime, sys

import asyncio

import xml.etree.ElementTree as ET

from .propertymembers import SwitchMember, LightMember, TextMember, NumberMember, BLOBMember

from .error import ParseException, reporterror


class PropertyVector(collections.UserDict):
    "Parent class of SwitchVector etc.."

    def __init__(self, name, label, group, state, device, client):
        super().__init__()
        self._client = client
        self.device = device
        self.devicename = device.devicename
        self.name = name
        self.label = label
        self.group = group
        self.state = state
        # if self.enable is False, this property ignores incoming traffic
        # and (apart from delProperty) does not transmit anything
        self.enable = True
        # the device places data in this dataque
        # for the vector to act upon
        self.dataque = asyncio.Queue(4)

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
        self.data[membername].membervalue = value

    def __getitem__(self, membername):
        return self.data[membername].membervalue

    def _setvector(self, event):
        "Updates this vector with new values after a set... vector has been received"
        if event.state:
            self.state = event.state
        for membername, membervalue in event.items():
            member = self.data[membername]
            member.membervalue = membervalue



class SwitchVector(PropertyVector):

    """A SwitchVector sends and receives one or more members with values 'On' or 'Off'. It
       also has the extra attribute 'rule' which can be one of 'OneOfMany', 'AtMostOne', 'AnyOfMany'.
       These are hints to the client how to display the switches in the vector.

       OneOfMany - of the SwitchMembers in this vector, one (and only one) must be On.

       AtMostOne - of the SwitchMembers in this vector, one or none can be On.

       AnyOfMany - multiple switch members can be On.
       """

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state, event.device, event._client)
        self.perm = event.perm
        self.rule = event.rule
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
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = SwitchMember(membername, event.memberlabels[membername], membervalue)

    async def send_newSwitchVector(self, timestamp=None, members=[]):
        """Transmits the vector (newSwitchVector) and members with their values to the driver.
           members is a list of member names to be sent.
           This method will change the state to busy
           and send the new vector to the driver."""
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            reporterror("Aborting sending newSwitchVector: The send_newSwitchVector timestamp must be a datetime.datetime object")
            return
        self.state = 'Busy'
        xmldata = ET.Element('newSwitchVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        # for rule 'OneOfMany' the standard indicates 'Off' should precede 'On'
        # so make all 'On' values last
        Offswitches = (switch for switch in self.data.values() if switch.membervalue == 'Off' and switch.name in members)
        Onswitches = (switch for switch in self.data.values() if switch.membervalue == 'On' and switch.name in members)
        for switch in Offswitches:
            xmldata.append(switch.oneswitch())
        for switch in Onswitches:
            xmldata.append(switch.oneswitch())
        await self._client.send(xmldata)



class LightVector(PropertyVector):

    """A LightVector is an instrument indicator, and sends one or more members
       with values 'Idle', 'Ok', 'Busy' or 'Alert'. In general a client will
       indicate this state with different colours."""

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state, event.device, event._client)
        # self.data is a dictionary of light name : lightmember
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = LightMember(membername, event.memberlabels[membername], membervalue)

    @property
    def perm(self):
        return "ro"


    def _defvector(self, event):
        "Updates this vector with new values after a def... vector has been received"
        if event.label:
            self.label = event.label
        if event.group:
            self.group = event.group
        if event.state:
            self.state = event.state
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = LightMember(membername, event.memberlabels[membername], membervalue)





class TextVector(PropertyVector):

    """A TextVector is used to send and receive text between instrument and client."""


    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state, event.device, event._client)
        self.perm = event.perm
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
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = TextMember(membername, event.memberlabels[membername], membervalue)



class NumberVector(PropertyVector):

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state, event.device, event._client)
        self.perm = event.perm
        # self.data is a dictionary of number name : numbermember
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = NumberMember(membername, *event.memberlabels[membername], membervalue)

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
        # create  members
        for membername, membervalue in event.items():
            self.data[membername] = NumberMember(membername, *event.memberlabels[membername], membervalue)


 
class BLOBVector(PropertyVector):

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state, event.device, event._client)
        self.perm = event.perm
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
        # create  members
        for membername, label in event.memberlabels.items():
            self.data[membername] = BLOBMember(membername, label)



