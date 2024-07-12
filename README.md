# indipyclient
Terminal client to communicate to an INDI service.

INDI - Instrument Neutral Distributed Interface.

See https://en.wikipedia.org/wiki/Instrument_Neutral_Distributed_Interface

This is a pure Python package, with no dependencies, providing an INDI terminal client.

This is a companion package to 'indipydriver' which can be used to create and serve INDI drivers operating your own instrument code.

https://github.com/bernie-skipole/indipydriver

indipyclient provides a terminal which can be started from the command line, and also a set of classes which can be used to create an INDI client if required. A Python script could use this to generate the INDI protocol, and to create the connection to a port serving INDI drivers.

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


A typical sesssion would look like:

![Terminal screenshot](https://github.com/bernie-skipole/indipyclient/raw/main/docs/source/usage/image.png)

The INDI protocol is defined to operate with any INDI client.

The protocol defines the format of the data sent, such as light, number, text, switch or BLOB (Binary Large Object) and the client can send commands to control the instrument.  The client is general purpose, taking the format of switches, numbers etc., from the protocol.

INDI is often used with astronomical instruments, but is a general purpose protocol which can be used for any instrument control providing drivers are available.

Further documentation is available at:

https://indipyclient.readthedocs.io

The package can be installed from:

https://pypi.org/project/indipyclient

indipyclient requires python 3.10 or later.

If you are only using the terminal client, I recommend pipx, so to install you would use:

pipx install indipyclient

or if you want to run it, without installing:

pipx run indipyclient
