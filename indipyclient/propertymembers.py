
import collections, io, asyncio

from datetime import datetime

import xml.etree.ElementTree as ET

from .error import ParseException


class PropertyMember:
    "Parent class of SwitchMember etc"

    def __init__(self, name, label=None):
        self.name = name
        if label:
            self.label = label
        else:
            self.label = name

    def checkvalue(self, value, allowed):
        "allowed is a list of values, checks if value is in it"
        if value not in allowed:
            raise ParseException(f"Invalid value:{value}")
        return value


class SwitchMember(PropertyMember):
    """A SwitchMember can only have one of 'On' or 'Off' values"""

    def __init__(self, name, label=None, membervalue="Off"):
        super().__init__(name, label)
        # membervalue should be either 'Off' or 'On'
        self._membervalue = membervalue

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not value:
            raise ParseException("No value given, should be either On or Off")
        newvalue = self.checkvalue(value, ['On', 'Off'])
        if self._membervalue != newvalue:
            self._membervalue = newvalue

    def oneswitch(self):
        """Returns xml of a oneSwitch"""
        xmldata = ET.Element('oneSwitch')
        xmldata.set("name", self.name)
        xmldata.text = self._membervalue
        return xmldata


class LightMember(PropertyMember):
    """A LightMember can only have one of 'Idle', 'Ok', 'Busy' or 'Alert' values"""

    def __init__(self, name, label=None, membervalue="Idle"):
        super().__init__(name, label)
        self._membervalue = membervalue

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not value:
            raise ParseException("No value given, should be one of 'Idle','Ok','Busy','Alert'")
        newvalue = self.checkvalue(value, ['Idle','Ok','Busy','Alert'])
        if self._membervalue != newvalue:
            self._membervalue = newvalue

    def onelight(self):
        """Returns xml of a oneLight"""
        xmldata = ET.Element('oneLight')
        xmldata.set("name", self.name)
        xmldata.text = self._membervalue
        return xmldata


class TextMember(PropertyMember):
    """Contains a text string"""

    def __init__(self, name, label=None, membervalue=""):
        super().__init__(name, label)
        self._membervalue = membervalue

    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if self._membervalue != value:
            self._membervalue = value

    def onetext(self):
        """Returns xml of a oneText"""
        xmldata = ET.Element('oneText')
        xmldata.set("name", self.name)
        xmldata.text = self.membervalue
        return xmldata


class NumberMember(PropertyMember):
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
        super().__init__(name, label)
        self.format = format
        if not isinstance(min, str):
            raise ParseException("minimum value must be given as a string")
        self.min = min
        if not isinstance(max, str):
            raise ParseException("maximum value must be given as a string")
        self.max = max
        if not isinstance(step, str):
            raise ParseException("step value must be given as a string")
        self.step = step
        if not isinstance(membervalue, str):
            raise ParseException("number value must be given as a string")
        self._membervalue = membervalue


    @property
    def membervalue(self):
        return self._membervalue

    @membervalue.setter
    def membervalue(self, value):
        if not isinstance(value, str):
            raise ParseException("number value must be given as a string")
        if not value:
            raise ParseException("No number value given")
        if self._membervalue != value:
            self._membervalue = value

    def format_number(self, value):
        """This takes a float, and returns a formatted string
        """
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


    def onenumber(self):
        """Returns xml of a oneNumber"""
        xmldata = ET.Element('oneNumber')
        xmldata.set("name", self.name)
        xmldata.text = self._membervalue
        return xmldata


class BLOBMember(PropertyMember):
    """Contains a 'binary large object' such as an image, the value should be
       either a bytes object, a file-like object, or a path to a file.

       blobsize is the size of the BLOB before any compression, if left at
       zero, the length of the BLOB will be used.

       The BLOB format should be a string describing the BLOB, such as .jpeg
    """

    def __init__(self, name, label=None, blobsize=0, blobformat='', membervalue=None):
        super().__init__(name, label)
        if not isinstance(blobsize, int):
            raise ParseException("blobsize must be given as an integer")
        # membervalue can be a byte string, path, string path or file like object
        self._membervalue = membervalue
        self.blobsize = blobsize
        self.blobformat = blobformat


    @property
    def membervalue(self):
        return self._membervalue


    @membervalue.setter
    def membervalue(self, value):
        if not value:
            raise ParseException("No BLOB value given")
        self._membervalue = value


    def oneblob(self):
        """Returns xml of a oneBLOB"""
        xmldata = ET.Element('oneBLOB')
        xmldata.set("name", self.name)
        xmldata.set("size", str(self.blobsize))
        xmldata.set("format", self.blobformat)
        # the value set in the xmldata object should be a bytes object
        if isinstance(self._membervalue, bytes):
            xmldata.text = self._membervalue
        elif hasattr(self._membervalue, "read") and callable(self._membervalue.read):
            # a file-like object
            # set seek(0) so is read from start of file
            self._membervalue.seek(0)
            bytescontent = self._membervalue.read()
            self._membervalue.close()
            if not isinstance(bytescontent, bytes):
                raise ParseException("The read BLOB is not a bytes object")
            if bytescontent == b"":
                raise ParseException("The read BLOB value is empty")
            xmldata.text = bytescontent
        else:
            # could be a path to a file
            try:
                with open(self._membervalue, "rb") as fp:
                    bytescontent = fp.read()
            except:
                raise ParseException("Unable to read the given file")
            if bytescontent == b"":
                raise ParseException("The read BLOB value is empty")
            xmldata.text = bytescontent
        return xmldata
