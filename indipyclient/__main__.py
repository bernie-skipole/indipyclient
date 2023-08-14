
"""Usage is

python3 -m indipyclient

"""


import argparse, asyncio

import urwid

from . import version

from .console.consoleclient import ConsoleClient

if __name__ == "__main__":


    parser = argparse.ArgumentParser(usage="python3 -m indipyclient [options]",
        description="INDI client communicating to indi service.")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the indiserver (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname of the indi service (default localhost).")

    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()


    client = ConsoleClient(indihost=args.host, indiport=args.port)

    aloop = asyncio.new_event_loop()
    iclienttask = aloop.create_task(client.asyncrun())

    evl = urwid.AsyncioEventLoop(loop=aloop)
    txt = urwid.Text(u"Hello World")
    fill = urwid.Filler(txt, 'top')
    loop = urwid.MainLoop(fill, event_loop=evl)

    loop.run()
