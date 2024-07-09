
"""Creates a terminal client

Try

python3 -m indipyclient --help

For a description of options
"""


import sys, argparse, asyncio, pathlib, logging

logger = logging.getLogger()

# logger is the root logger, with level and handler set here
# by the arguments given. If no logging option is given, it
# has a NullHandler() added

from . import version

from .console import ConsoleClient


def setlogging(client, level, logfile):
    """Sets the logging level and logfile, returns the level on success, None on failure.
       level should be an integer, one of 1, 2, 3 or 4."""

    # loglevel:1 Information and error messages only
    # loglevel:2 log vector tags without members or contents
    # loglevel:3 log vectors and members - but not BLOB contents
    # loglevel:4 log vectors and all contents

    try:
        if not level in (1, 2, 3, 4):
            return
        logfile = pathlib.Path(logfile).expanduser().resolve()

        if level == 4:
            logger.setLevel(logging.DEBUG)
            client.debug_verbosity(3)
        elif level == 3:
            logger.setLevel(logging.DEBUG)
            client.debug_verbosity(2)
        elif level == 2:
            logger.setLevel(logging.DEBUG)
            client.debug_verbosity(1)
        elif level == 1:
            logger.setLevel(logging.INFO)
            client.debug_verbosity(0)
            # If logging debug not enabled, reduce traceback info
            sys.tracebacklimit = 0

        fh = logging.FileHandler(logfile)
        logger.addHandler(fh)
    except Exception:
        return
    return level


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

    if args.loglevel:
        if args.loglevel not in ("1", "2", "3", "4"):
            print("Error: If given, the loglevel should be 1, 2, 3 or 4")
            return 1


    client = ConsoleClient(indihost=args.host, indiport=args.port, blobfolder=blobfolder)

    if args.loglevel and args.logfile:
        loglevel = int(args.loglevel)
        level = setlogging(client, loglevel, args.logfile)
        if level != loglevel:
            print("Error: Failed to set logging")
            return 1
    else:
        logger.addHandler(logging.NullHandler())

    try:
        # Starts the client, creates the console screens
        asyncio.run(client.asyncrun())
    finally:
        # clear curses setup
        client.console_reset()

    return 0


if __name__ == "__main__":
    sys.exit(main())
