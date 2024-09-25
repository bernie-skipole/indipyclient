# indipyclient

This indipyclient package provides a terminal client, which connects to a port, allowing an instrument to be viewed and controlled from a terminal session.

The instrument port is typically served using the indipydriver package which provides classes which can be used by your own Python program controlling some form of instrument, with switches, indicators or measurement data.

indipydriver and indipyclient communicate with the INDI protocol.

INDI - Instrument Neutral Distributed Interface.

See https://en.wikipedia.org/wiki/Instrument_Neutral_Distributed_Interface

The companion package 'indipydriver' is available on Pypi and developed at.

https://github.com/bernie-skipole/indipydriver

The indipyclient terminal client can be started from the command line, and can also be imported if required, in which case it provides a set of classes which can be used to create scripts to control the remote instrument.

The client can be run with

indipyclient [options]

or with

python3 -m indipyclient [options]

The package help is:

    usage: indipyclient [options]

    Terminal client to communicate to an INDI service.

    options:
      -h, --help            show this help message and exit
      -p PORT, --port PORT  Port of the INDI server (default 7624).
      --host HOST           Hostname/IP of the INDI server (default localhost).
      -b BLOBS, --blobs BLOBS
                            Optional folder where BLOB's will be saved.
      --loglevel LOGLEVEL   Enables logging, value 1, 2, 3 or 4.
      --logfile LOGFILE     File where logs will be saved
      --version             show program's version number and exit

    The BLOB's folder can also be set from within the session.
    Setting loglevel and logfile should only be used for brief
    diagnostic purposes, the logfile could grow very big.
    loglevel:1 Information and error messages only,
    loglevel:2 As 1 plus xml vector tags without members or contents,
    loglevel:3 As 1 plus xml vectors and members - but not BLOB contents,
    loglevel:4 As 1 plus xml vectors and all contents


A typical session would look like:

![Terminal screenshot](https://github.com/bernie-skipole/indipyclient/raw/main/docs/source/usage/image.png)

The INDI protocol is defined to operate with any INDI client.

The protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object). The client is general purpose, taking the format of switches, numbers etc., from the protocol.

INDI is often used with astronomical instruments, but is a general purpose protocol which can be used for any instrument control.

Further documentation is available at:

https://indipyclient.readthedocs.io

The package can be installed from:

https://pypi.org/project/indipyclient

and indipydriver is available at:

https://pypi.org/project/indipydriver
