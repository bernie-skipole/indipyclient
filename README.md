# indipyclient
INDI console client to communicate to an indi service.

This is under development and not yet ready for use

This is a pure python package, with no dependencies, providing an INDI client terminal

It also provides a set of classes which can be used to create an INDI client. Either a script, or a GUI implementation could use this to generate the INDI protocol XML, and to create the connection to a port serving INDI drivers.

The client can be called with python3 -m indipyclent.

    usage: python3 -m indipyclient [options]

    INDI console client communicating to indi service.

    options:
      -h, --help            show this help message and exit
      -p PORT, --port PORT  Port of the indi server (default 7624).
      --host HOST           Hostname/IP of the indi server (default localhost).
      -b BLOBS, --blobs BLOBS
                            Optional folder where BLOB's will be saved.
      --loglevel LOGLEVEL   Enables logging, value 1, 2 or 3.
      --logfile LOGFILE     File where logs will be saved
      --version             show program's version number and exit

    The BLOB's folder can also be set from within the console. Setting loglevel and logfile should only be used for brief diagnostic
    purposes, the logfile could grow very big. loglevel:1 log vector tags without members or contents, loglevel:2 log vectors and
    members - but not BLOB contents, loglevel:3 log vectors and all contents


This is a companion package to 'indipydriver' which can be used to create INDI drivers.

INDI - Instrument Neutral Distributed Interface.

See https://en.wikipedia.org/wiki/Instrument_Neutral_Distributed_Interface

The INDI protocol is defined so that drivers should operate with any INDI client.

The protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object) and the client can send commands to control the instrument.  The client can be general purpose, taking the format of switches, numbers etc., from the protocol.

INDI is often used with astronomical instruments, but is a general purpose protocol which can be used for any instrument control providing drivers are available.
