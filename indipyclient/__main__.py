
"""Creates a terminal client

Try

python3 -m indipyclient --help

For a description of options
"""


import sys, argparse, asyncio, pathlib

import logging
logger = logging.getLogger('indipyclient')

from . import version

from .console.consoleclient import ConsoleClient, ConsoleControl


async def runclient(client, control):
    await asyncio.gather(client.asyncrun(), control.asyncrun())


def main():
    """The commandline entry point to run the terminal client."""

    parser = argparse.ArgumentParser(usage="indipyclient [options]",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Terminal client to communicate to an INDI service.",
                                     epilog="""The BLOB's folder can also be set from within the session.
Setting loglevel and logfile should only be used for brief
diagnostic purposes, the logfile could grow very big.
loglevel:1 Information and error messages only,
loglevel:2 As 1 plus xml vector tags without members or contents,
loglevel:3 As 1 plus xml vectors and members - but not BLOB contents,
loglevel:4 As 1 plus xml vectors and all contents
""")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the INDI server (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname/IP of the INDI server (default localhost).")
    parser.add_argument("-b", "--blobs", help="Optional folder where BLOB's will be saved.")
    parser.add_argument("--loglevel", help="Enables logging, value 1, 2, 3 or 4.")
    parser.add_argument("--logfile", help="File where logs will be saved")

    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    if args.blobs:
        try:
            blobfolder = pathlib.Path(args.blobs).expanduser().resolve()
        except Exception:
            print("Error: If given, the BLOB's folder should be an existing directory")
            return 1
        else:
            if not blobfolder.is_dir():
                print("Error: If given, the BLOB's folder should be an existing directory")
                return 1
    else:
        blobfolder = None

    # ConsoleClient is a subclass of IPyClient, with its rxevent(event) method created
    # to add events to a queue. First a queue is created and passed into ConsoleClient
    eventque = asyncio.Queue(maxsize=4)

    # On receiving an event, the client appends it into eventque
    client = ConsoleClient(indihost=args.host, indiport=args.port, eventque=eventque)

    # Monitors eventque and acts on the events, creates the console screens
    # and calls the send vector methods of client to transmit data
    control = ConsoleControl(client, blobfolder=blobfolder)

    loglevel = 0

    if args.loglevel and args.logfile:
        try:
            loglevel = int(args.loglevel)
            if loglevel not in (1,2,3,4):
                print("Error: If given, the loglevel should be 1, 2, 3 or 4")
                return 1
            level = control.setlogging(loglevel, args.logfile)
            if level != loglevel:
                print("Error: Failed to set logging")
                return 1
        except Exception:
            print("Error: If given, the loglevel should be 1, 2, 3 or 4")
            return 1

    if loglevel < 2:
        # If logging debug not enabled, reduce traceback info
        sys.tracebacklimit = 0

    try:
        asyncio.run(runclient(client, control))
    finally:
        # clear curses setup
        control.console_reset()

    return 0


if __name__ == "__main__":
    sys.exit(main())
