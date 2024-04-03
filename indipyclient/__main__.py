
"""Usage is

python3 -m indipyclient

"""


import os, sys, argparse, asyncio, collections, contextlib, pathlib

from . import version

from .console.consoleclient import ConsoleClient, ConsoleControl


async def runclient(client, control):
    t1 = asyncio.create_task(client.asyncrun())
    t2 = asyncio.create_task(control.asyncrun())
    await asyncio.gather(t1, t2)
    # wait for tasks to be done
    while (not t1.done()) and (not t2.done()):
        await asyncio.sleep(0)


def main():
    """The main routine."""

    parser = argparse.ArgumentParser(usage="indipyclient [options]",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Terminal client to communicate to an INDI service.",
                                     epilog="""The BLOB's folder can also be set from within the session.
Setting loglevel and logfile should only be used for brief
diagnostic purposes, the logfile could grow very big.
loglevel:1 Information and error messages only,
loglevel:2 log vector tags without members or contents,
loglevel:3 log vectors and members - but not BLOB contents,
loglevel:4 log vectors and all contents
""")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the INDI server (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname/IP of the INDI server (default localhost).")
    parser.add_argument("-b", "--blobs", help="Optional folder where BLOB's will be saved.")
    parser.add_argument("--loglevel", help="Enables logging, value 1, 2, 3 or 4.")
    parser.add_argument("--logfile", help="File where logs will be saved")

    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    eventque = collections.deque(maxlen=4)

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

    # On receiving an event, the client appends it into eventque
    client = ConsoleClient(indihost=args.host, indiport=args.port, eventque=eventque)

    if args.loglevel and args.logfile:
        try:
            loglevel = int(args.loglevel)
            if loglevel not in (1,2,3,4):
                print("Error: If given, the loglevel should be 1, 2, 3 or 4")
                return 1
        except:
            print("Error: If given, the loglevel should be 1, 2, 3 or 4")
            return 1
        client.setlogging(loglevel, args.logfile)

    # Monitors eventque and acts on the events, creates the console screens
    control = ConsoleControl(client, blobfolder=blobfolder)

    asyncio.run(runclient(client, control))

    return 0


if __name__ == "__main__":
    sys.exit(main())
