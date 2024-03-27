
"""Usage is

python3 -m indipyclient

"""


import os, sys, argparse, asyncio, collections, contextlib, pathlib


from . import version

from .console.consoleclient import ConsoleClient, ConsoleControl


async def runclient(client, control):
    try:
        t1 = asyncio.create_task(client.asyncrun())
        t2 = asyncio.create_task(control.asyncrun())
        await asyncio.gather(t1, t2)
    except Exception:
         t1.cancel()
         t2.cancel()
    # wait for tasks to be done
    while (not t1.done()) and (not t2.done()):
        await asyncio.sleep(0)



def main():
    """The main routine."""

    parser = argparse.ArgumentParser(usage="python3 -m indipyclient [options]",
                                     description="INDI console client communicating to indi service.",
                                     epilog="The BLOB's folder can also be set from within the console.")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the indiserver (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname of the indi service (default localhost).")
    parser.add_argument("-b", "--blobs", help="Optional folder where BLOB's will be saved.")

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
    # Monitors eventque and acts on the events, creates the console screens
    control = ConsoleControl(client, blobfolder=blobfolder)

    asyncio.run(runclient(client, control))
    return 0


if __name__ == "__main__":
    sys.exit(main())
