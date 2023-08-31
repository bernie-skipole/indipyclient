
"""Usage is

python3 -m indipyclient

"""


import argparse, asyncio, collections, contextlib


from . import version

from .console.consoleclient import ConsoleClient, ConsoleControl


async def main(client, control):
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


if __name__ == "__main__":


    parser = argparse.ArgumentParser(usage="python3 -m indipyclient [options]",
        description="INDI client communicating to indi service.")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the indiserver (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname of the indi service (default localhost).")

    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    print("Client running...")

    eventque = collections.deque(maxlen=4)

    client = ConsoleClient(indihost=args.host, indiport=args.port, eventque=eventque)
    control = ConsoleControl(client)

    with open('err.txt', 'w') as f:
        with contextlib.redirect_stderr(f):
            asyncio.run(main(client, control))
