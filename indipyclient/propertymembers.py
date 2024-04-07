
import xml.etree.ElementTree as ET

import sys, math, pathlib

from .error import ParseException


class Member():

    def __init__(self, name, label=None, membervalue=None):
        self.name = name
        if label:
            self.label = label
        else:
            self.label = name
        self._membervalue = membervalue

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        self._membervalue = value



class PropertyMember(Member):
    "Parent class of SwitchMember etc"

    def checkvalue(self, value, allowed):
        "allowed is a list of values, checks if value is in it"
        if value not in allowed:
            raise ParseException(f"Error: Invalid value:{value}")
        return value

    def _snapshot(self):
        snapmember = Member(self.name, self.label, self._membervalue)
        return snapmember


class SwitchMember(PropertyMember):
    """A SwitchMember can only have one of 'On' or 'Off' values"""

    def __init__(self, name, label=None, membervalue="Off"):
        super().__init__(name, label, membervalue)
        if membervalue not in ('On', 'Off'):
            raise ParseException(f"Error: Invalid value {membervalue}, should be On or Off")

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not value:
            raise ParseException("Error: No value given, should be On or Off")
        newvalue = self.checkvalue(value, ['On', 'Off'])
        if self._membervalue != newvalue:
            self._membervalue = newvalue

    def oneswitch(self, newvalue):
        """Returns xml of a oneSwitch with the new value to send"""
        xmldata = ET.Element('oneSwitch')
        xmldata.set("name", self.name)
        xmldata.text = newvalue
        return xmldata


class LightMember(PropertyMember):
    """A LightMember can only have one of 'Idle', 'Ok', 'Busy' or 'Alert' values"""

    def __init__(self, name, label=None, membervalue="Idle"):
        super().__init__(name, label, membervalue)
        if membervalue not in ('Idle','Ok','Busy','Alert'):
            raise ParseException(f"Error: Invalid light value {membervalue}")

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not value:
            raise ParseException("Error: No light value given")
        newvalue = self.checkvalue(value, ['Idle','Ok','Busy','Alert'])
        if self._membervalue != newvalue:
            self._membervalue = newvalue


class TextMember(PropertyMember):
    """Contains a text string"""

    def __init__(self, name, label=None, membervalue=""):
        super().__init__(name, label, membervalue)
        if not isinstance(membervalue, str):
            raise ParseException("Error: The text value should be a string")

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not isinstance(value, str):
            raise ParseException("Error: The text value should be a string")
        if self._membervalue != value:
            self._membervalue = value

    def onetext(self, newvalue):
        """Returns xml of a oneText"""
        xmldata = ET.Element('oneText')
        xmldata.set("name", self.name)
        xmldata.text = newvalue
        return xmldata


class ParentNumberMember(Member):

    def __init__(self, name, label=None, format='', min='0', max='0', step='0', membervalue='0'):
        super().__init__(name, label, membervalue)
        self.format = format
        self.min = min
        self.max = max
        self.step = step

    def getfloatvalue(self):
        """The INDI spec allows a number of different number formats, this method returns
           this members value as a float.
           If an error occurs while parsing the number, a TypeError exception is raised."""
        return self.getfloat(self._membervalue)


    def getfloat(self, value):
        """The INDI spec allows a number of different number formats, given a number,
           this returns a float.
           If an error occurs while parsing the number, a TypeError exception is raised."""
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
                parts = ["0", "0", "0"]
            elif " " in value:
                parts = value.split(" ")
            elif ":" in value:
                parts = value.split(":")
            elif ";" in value:
                parts = value.split(";")
            else:
                # not sexagesimal
                parts = [value, "0", "0"]
            if len(parts) > 3:
                raise TypeError
            # Any missing parts should have zero
            if len(parts) == 1:
                parts.append("0")
                parts.append("0")
            if len(parts) == 2:
                parts.append("0")
            assert len(parts) == 3
            # a part could be empty string, ie if 2:5: is given
            numbers = list(float(x) if x else 0.0 for x in parts)
            floatvalue = numbers[0] + (numbers[1]/60) + (numbers[2]/3600)
            if negative:
                floatvalue = -1 * floatvalue
        except:
            raise TypeError("Error: Unable to parse number value")
        return floatvalue


    def getformattedvalue(self):
        """This method returns this members value as a string float."""
        return self.getformattedstring(self._membervalue)


    def getformattedstring(self, value):
        """Given a number this returns a formatted string"""
        try:
            value = self.getfloat(value)
            if (not self.format.startswith("%")) or (not self.format.endswith("m")):
                return self.format % value
            # sexagesimal
            # format string is of the form  %<w>.<f>m
            w,f = self.format.split(".")
            w = w.lstrip("%")
            f = f.rstrip("m")

            if value<0:
                negative = True
            else:
                negative = False
            absvalue = abs(value)

            # get integer part and fraction part
            degrees = math.floor(absvalue)
            minutes = (absvalue - degrees) * 60.0

            if f == "3":   # three fractional values including the colon ":mm"
                # create nearest integer minutes
                minutes = round(minutes)
                if minutes == 60:
                    minutes = 0
                    degrees = degrees + 1
                valstring = f"{'-' if negative else ''}{degrees}:{minutes:02d}"
                # w is the overall length of the string, prepend with spaces to make the length up to w
                if w:
                    return valstring.rjust(int(w), ' ')
                # it is possible w is an empty string
                return valstring

            if f == "5":  # five fractional values including the colon and decimal point ":mm.m"
                minutes = round(minutes,1)
                if minutes == 60.0:
                    minutes = 0.0
                    degrees = degrees + 1
                valstring = f"{'-' if negative else ''}{degrees}:{minutes:04.1f}"
                if w:
                    return valstring.rjust(int(w), ' ')
                return valstring

            integerminutes = math.floor(minutes)
            seconds = (minutes - integerminutes) * 60.0

            if f == "6":    # six fractional values including two colons ":mm:ss"
                seconds = round(seconds)
                if seconds == 60:
                    seconds = 0
                    integerminutes = integerminutes + 1
                    if integerminutes == 60:
                        integerminutes = 0
                        degrees = degrees + 1
                valstring = f"{'-' if negative else ''}{degrees}:{integerminutes:02d}:{seconds:02d}"
                if w:
                    return valstring.rjust(int(w), ' ')
                return valstring


            if f == "8":    # eight fractional values including two colons and decimal point ":mm:ss.s"
                seconds = round(seconds,1)
                if seconds == 60.0:
                    seconds = 0.0
                    integerminutes = integerminutes + 1
                    if integerminutes == 60:
                        integerminutes = 0
                        degrees = degrees + 1
                valstring = f"{'-' if negative else ''}{degrees}:{integerminutes:02d}:{seconds:04.1f}"
                if w:
                    return valstring.rjust(int(w), ' ')
                return valstring

            fn = int(f)
            if fn>8 and fn<15:    # make maximum of 14
                seconds = round(seconds,1)
                if seconds == 60.0:
                    seconds = 0.0
                    integerminutes = integerminutes + 1
                    if integerminutes == 60:
                        integerminutes = 0
                        degrees = degrees + 1
                valstring = f"{'-' if negative else ''}{degrees}:{integerminutes:02d}:{seconds:0{fn-4}.{fn-7}f}"
                if w:
                    return valstring.rjust(int(w), ' ')
                return valstring

        except:
            raise TypeError("Error: Unable to parse number value")

        # no other options accepted
        raise TypeError("Error: Unable to process number format")


class NumberMember(ParentNumberMember):
    """Contains a number, the attributes inform the client how the number should be
       displayed.

       format is a C printf style format, for example %7.2f means the client should
       display the number string with seven characters (including the decimal point
       as a character and leading spaces should be inserted if necessary), and with
       two decimal digits after the decimal point.

       min is the minimum value

       max is the maximum, if min is equal to max, the client should ignore these.

       step is incremental step values, set to string of zero if not used.

       The above numbers, and the member value must be set as a string, this explicitly
       controls how numbers are placed in the xml protocol.
    """

    def __init__(self, name, label=None, format='', min='0', max='0', step='0', membervalue='0'):
        super().__init__(name, label, format, min, max, step, membervalue)
        self.format = format
        if not isinstance(min, str):
            raise ParseException("Error: minimum value must be given as a string")
        self.min = min
        if not isinstance(max, str):
            raise ParseException("Error: maximum value must be given as a string")
        self.max = max
        if not isinstance(step, str):
            raise ParseException("Error: step value must be given as a string")
        self.step = step
        if not isinstance(membervalue, str):
            raise ParseException("Error: number value must be given as a string")

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not isinstance(value, str):
            raise ParseException("Error: number value must be given as a string")
        if not value:
            raise ParseException("Error: no number value given")
        if self._membervalue != value:
            self._membervalue = value


    def onenumber(self, newvalue):
        """Returns xml of a oneNumber"""
        xmldata = ET.Element('oneNumber')
        xmldata.set("name", self.name)
        xmldata.text = newvalue
        return xmldata

    def _snapshot(self):
        snapmember = ParentNumberMember(self.name, self.label, self.format, self.min, self.max, self.step, self._membervalue)
        return snapmember


class ParentBLOBMember(Member):

    def __init__(self, name, label=None, blobsize=0, blobformat='', membervalue=None):
        super().__init__(name, label, membervalue)
        self.blobsize = blobsize
        self.blobformat = blobformat


class BLOBMember(ParentBLOBMember):
    """Contains a 'binary large object' such as an image.

       blobsize is the size of the BLOB before any compression, if left at
       zero, the length of the BLOB will be used.

       The BLOB format should be a string describing the BLOB, such as .jpeg
    """

    def __init__(self, name, label=None, blobsize=0, blobformat='', membervalue=None):
        super().__init__(name, label, membervalue)
        if not isinstance(blobsize, int):
            raise ParseException("Error: blobsize must be given as an integer")
        # membervalue can be a byte string, path, string path or file like object
        self.blobsize = blobsize
        self.blobformat = blobformat

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not value:
            raise ParseException("Error: No BLOB value given")
        self._membervalue = value


    def oneblob(self, newvalue, newsize, newformat):
        """Returns xml of a oneBLOB"""
        xmldata = ET.Element('oneBLOB')
        xmldata.set("name", self.name)
        xmldata.set("format", newformat)
        xmldata.set("size", str(newsize))
        # the value set in the xmldata object should be a bytes object
        if isinstance(newvalue, bytes):
            xmldata.text = newvalue
        elif isinstance(newvalue, pathlib.Path):
            try:
                xmldata.text = newvalue.read_bytes()
            except:
                raise ParseException("Error: Unable to read the given file")
        elif hasattr(newvalue, "seek") and hasattr(newvalue, "read") and callable(newvalue.read):
            # a file-like object
            # set seek(0) so is read from start of file
            newvalue.seek(0)
            bytescontent = newvalue.read()
            newvalue.close()
            if not isinstance(bytescontent, bytes):
                raise ParseException("Error: The read BLOB is not a bytes object")
            if bytescontent == b"":
                raise ParseException("Error: The read BLOB value is empty")
            xmldata.text = bytescontent
        else:
            # could be a path to a file
            try:
                with open(newvalue, "rb") as fp:
                    bytescontent = fp.read()
            except:
                raise ParseException("Error: Unable to read the given file")
            if bytescontent == b"":
                raise ParseException("Error: The read BLOB value is empty")
            xmldata.text = bytescontent
        return xmldata


    def _snapshot(self):
        snapmember = ParentBLOBMember(self.name, self.label, self.blobsize, self.blobformat, self._membervalue)
        return snapmember
