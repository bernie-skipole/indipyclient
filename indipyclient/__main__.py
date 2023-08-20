
"""Usage is

python3 -m indipyclient

"""


import argparse, asyncio


from . import version

from .console.consoleclient import ConsoleClient, ConsoleControl


async def main(client, control):

    t1 = client.asyncrun()
    t2 = control.asyncrun()
    await asyncio.gather(t1, t2)
    print("Client exited")


if __name__ == "__main__":


    parser = argparse.ArgumentParser(usage="python3 -m indipyclient [options]",
        description="INDI client communicating to indi service.")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the indiserver (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname of the indi service (default localhost).")

    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    # eventque where received events will be placed and passed to control
    eventque = asyncio.Queue(4)

    client = ConsoleClient(indihost=args.host, indiport=args.port, eventque=eventque)
    control = ConsoleControl(client, eventque)

    asyncio.run(main(client, control))
