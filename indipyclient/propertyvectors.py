
import collections, datetime, sys

import asyncio

import xml.etree.ElementTree as ET

from .propertymembers import SwitchMember, LightMember, TextMember, NumberMember, BLOBMember

from .error import ParseException


class PropertyVector(collections.UserDict):
    "Parent class of SwitchVector etc.."

    def __init__(self, name, label, group, state):
        super().__init__()
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


    def _reporterror(self, message):
        "Prints message to stderr"
        print(message, file=sys.stderr)

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
        super().__init__(event.vectorname, event.label, event.group, event.state)
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


    async def send_setVector(self, message='', timestamp=None, timeout='0', allvalues=True):
        """Transmits the vector (setSwitchVector) and members with their values to the client.
           Typically the vector 'state' should be set, and any changed member value prior to
           transmission.

           message is any suitable string for the client.

           timestamp should be a datetime.datetime object or None, in which case a
           datetime.datetime.utcnow() value will be inserted.

           The timeout value should be '0' if not used, or a string value indicating
           to the client how long this data is valid.

           If allvalues is True, all values are sent.

           If allvalues is False, only values that have changed will be sent, saving bandwidth.
           If no values have changed, the vector will not be sent, if you need to ensure the
           vector message, state or time values are sent to the client, then use the more
           explicit send_setVectorMembers method instead.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setSwitchVector: The given send_setVector timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setSwitchVector: The given send_setVector timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setSwitchVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        # for rule 'OneOfMany' the standard indicates 'Off' should precede 'On'
        # so make all 'On' values last
        Offswitches = (switch for switch in self.data.values() if switch.membervalue == 'Off')
        Onswitches = (switch for switch in self.data.values() if switch.membervalue == 'On')
        # set a flag to test if at least one member is included
        membersincluded = False
        for switch in Offswitches:
            # only send member if its value has changed or if allvalues is True
            if allvalues or switch.changed:
                xmldata.append(switch.oneswitch())
                switch.changed = False
                membersincluded = True
        for switch in Onswitches:
            # only send member if its value has changed or if allvalues is True
            if allvalues or switch.changed:
                xmldata.append(switch.oneswitch())
                switch.changed = False
                membersincluded = True
        if membersincluded:
            # only send xmldata if a member is included in the vector
            await self.driver.send(xmldata)


    async def send_setVectorMembers(self, message='', timestamp=None, timeout='0', members=[]):
        """Transmits the vector (setSwitchVector) and members with their values to the client.
           Similar to the send_setVector method however the members list specifies the
           member names which will have their values sent.

           This allows members to be explicitly specified. If the members list is empty
           then a vector will still be sent, empty of members, which may be required if
           just a state or message is to be sent.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setSwitchVector: The given send_setVectorMembers timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setSwitchVector: The given send_setVectorMembers timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setSwitchVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        # for rule 'OneOfMany' the standard indicates 'Off' should precede 'On'
        # so make all 'On' values last
        Offswitches = (switch for switch in self.data.values() if switch.membervalue == 'Off' and switch.name in members)
        Onswitches = (switch for switch in self.data.values() if switch.membervalue == 'On' and switch.name in members)
        for switch in Offswitches:
            xmldata.append(switch.oneswitch())
            switch.changed = False
        for switch in Onswitches:
            xmldata.append(switch.oneswitch())
            switch.changed = False
        await self.driver.send(xmldata)


class LightVector(PropertyVector):

    """A LightVector is an instrument indicator, and sends one or more members
       with values 'Idle', 'Ok', 'Busy' or 'Alert'. In general a client will
       indicate this state with different colours."""

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state)
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


    async def send_setVector(self, message='', timestamp=None, timeout='0', allvalues=True):
        """Transmits the vector (setLightVector) and members with their values to the client.
           Typically the vector 'state' should be set, and any changed member value prior to
           transmission.

           message is any suitable string for the client.

           timestamp should be a datetime.datetime object or None, in which case a
           datetime.datetime.utcnow() value will be inserted.

           For Light Vectors the timeout value is not used, but is included in the arguments
           to match other send_vectors.

           If allvalues is True, all values are sent.

           If allvalues is False, only values that have changed will be sent, saving bandwidth.
           If no values have changed, the vector will not be sent, if you need to ensure the
           vector message, state or time values are sent to the client, then use the more
           explicit send_setVectorMembers method instead.
        """
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setLightVector: The given send_setVector timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setLightVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        if message:
            xmldata.set("message", message)
        # set a flag to test if at least one member is included
        membersincluded = False
        for light in self.data.values():
            # only send member if its value has changed or if allvalues is True
            if allvalues or light.changed:
                xmldata.append(light.onelight())
                light.changed = False
                membersincluded = True
        if membersincluded:
            # only send xmldata if a member is included in the vector
            await self.driver.send(xmldata)

    async def send_setVectorMembers(self, message='', timestamp=None, timeout='0', members=[]):
        """Transmits the vector (setLightVector) and members with their values to the client.
           Similar to the send_setVector method however the members list specifies the
           member names which will have their values sent.

           This allows members to be explicitly specified. If the members list is empty
           then a vector will still be sent, empty of members, which may be required if
           just a state or message is to be sent.
        """
        # Note timeout is not used
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setLightVector: The given send_setVectorMembers timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setLightVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        if message:
            xmldata.set("message", message)
        for light in self.data.values():
            if light.name in  members:
                xmldata.append(light.onelight())
                light.changed = False
        await self.driver.send(xmldata)



class TextVector(PropertyVector):

    """A TextVector is used to send and receive text between instrument and client."""


    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state)
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


    async def send_setVector(self, message='', timestamp=None, timeout='0', allvalues=True):
        """Transmits the vector (setTextVector) and members with their values to the client.
           Typically the vector 'state' should be set, and any changed member value prior to
           transmission.

           message is any suitable string for the client.

           timestamp should be a datetime.datetime object or None, in which case a
           datetime.datetime.utcnow() value will be inserted.

           The timeout value should be '0' if not used, or a string value
           indicating to the client how long this data is valid.

           If allvalues is True, all values are sent.

           If allvalues is False, only values that have changed will be sent, saving bandwidth.
           If no values have changed, the vector will not be sent, if you need to ensure the
           vector message, state or time values are sent to the client, then use the more
           explicit send_setVectorMembers method instead.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setTextVector: The given send_setVector timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setTextVector: The given send_setVector timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setTextVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        # set a flag to test if at least one member is included
        membersincluded = False
        for text in self.data.values():
            # only send member if its value has changed or if allvalues is True
            if allvalues or text.changed:
                xmldata.append(text.onetext())
                text.changed = False
                membersincluded = True
        if membersincluded:
            # only send xmldata if a member is included in the vector
            await self.driver.send(xmldata)

    async def send_setVectorMembers(self, message='', timestamp=None, timeout='0', members=[]):
        """Transmits the vector (setTextVector) and members with their values to the client.
           Similar to the send_setVector method however the members list specifies the
           member names which will have their values sent.

           This allows members to be explicitly specified. If the members list is empty
           then a vector will still be sent, empty of members, which may be required if
           just a state or message is to be sent.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setTextVector: The given send_setVectorMembers timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setTextVector: The given send_setVectorMembers timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setTextVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        for text in self.data.values():
            if text.name in members:
                xmldata.append(text.onetext())
                text.changed = False
        await self.driver.send(xmldata)


class NumberVector(PropertyVector):

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state)
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


    async def send_setVector(self, message='', timestamp=None, timeout='0', allvalues=True):
        """Transmits the vector (setNumberVector) and members with their values to the client.
           Typically the vector 'state' should be set, and any changed member value prior to
           transmission.

           message is any suitable string for the client.

           timestamp should be a datetime.datetime object or None, in which case a
           datetime.datetime.utcnow() value will be inserted.

           The timeout value should be '0' if not used, or a string value
           indicating to the client how long this data is valid.

           If allvalues is True, all values are sent.

           If allvalues is False, only values that have changed will be sent, saving bandwidth.
           If no values have changed, the vector will not be sent, if you need to ensure the
           vector message, state or time values are sent to the client, then use the more
           explicit send_setVectorMembers method instead.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setNumberVector: The given send_setVector timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setNumberVector: The given send_setVector timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setNumberVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        # set a flag to test if at least one member is included
        membersincluded = False
        for number in self.data.values():
            # only send member if its value has changed or if allvalues is True
            if allvalues or number.changed:
                xmldata.append(number.onenumber())
                number.changed = False
                membersincluded = True
        if membersincluded:
            # only send xmldata if a member is included in the vector
            await self.driver.send(xmldata)

    async def send_setVectorMembers(self, message='', timestamp=None, timeout='0', members=[]):
        """Transmits the vector (setNumberVector) and members with their values to the client.
           Similar to the send_setVector method however the members list specifies the
           member names which will have their values sent.

           This allows members to be explicitly specified. If the members list is empty
           then a vector will still be sent, empty of members, which may be required if
           just a state or message is to be sent.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setNumberVector: The given send_setVectorMembers timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setNumberVector: The given send_setVectorMembers timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setNumberVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        for number in self.data.values():
            if number.name in members:
                xmldata.append(number.onenumber())
                number.changed = False
        await self.driver.send(xmldata)


class BLOBVector(PropertyVector):

    def __init__(self, event):
        super().__init__(event.vectorname, event.label, event.group, event.state)
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
            self._reporterror("blobsize rejected, must be an integer object")
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


    # NOTE: BLOBVectors do not have a send_setVector method
    #       only the more explicit send_setVectorMembers is available

    async def send_setVectorMembers(self, message='', timestamp=None, timeout='0', members=[]):
        """Transmits the vector (setBLOBVector) and members with their values to the client.
           The members list specifies the member names which will have their values sent.

           Members contain either a bytes string, a file-like object, or a path to a file. If
           a file-like object is given, its contents will be read and its close() method
           will be called, so you do not have to close it.
        """
        if not isinstance(timeout, str):
            self._reporterror("Aborting sending setBLOBVector: The given send_setVectorMembers timeout value must be a string object")
            return
        if not self.device.enable:
            return
        if not self.enable:
            return
        if not timestamp:
            timestamp = datetime.datetime.utcnow()
        if not isinstance(timestamp, datetime.datetime):
            self._reporterror("Aborting sending setBLOBVector: The given send_setVectorMembers timestamp must be a datetime.datetime object")
            return
        xmldata = ET.Element('setBLOBVector')
        xmldata.set("device", self.devicename)
        xmldata.set("name", self.name)
        xmldata.set("state", self.state)
        # note - limit timestamp characters to :21 to avoid long fractions of a second
        xmldata.set("timestamp", timestamp.isoformat(sep='T')[:21])
        xmldata.set("timeout", timeout)
        if message:
            xmldata.set("message", message)
        for blob in self.data.values():
            if (blob.name in members) and (blob.membervalue is not None):
                xmldata.append(blob.oneblob())
        await self.driver.send(xmldata)
