
"""Usage is

python3 -m indipyclient

"""


import argparse, asyncio

import urwid

from . import version

from .console.consoleclient import ConsoleClient


def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()


if __name__ == "__main__":


    parser = argparse.ArgumentParser(usage="python3 -m indipyclient [options]",
        description="INDI client communicating to indi service.")
    parser.add_argument("-p", "--port", type=int, default=7624, help="Port of the indiserver (default 7624).")
    parser.add_argument("--host", default="localhost", help="Hostname of the indi service (default localhost).")

    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    palette = [
        ('banner', 'black', 'light gray'),
        ('streak', 'black', 'dark red'),
        ('bg', 'black', 'dark blue'),]

    txt = urwid.Text(('banner', u" Hello World "), align='center')
    map1 = urwid.AttrMap(txt, 'streak')
    fill = urwid.Filler(map1)
    map2 = urwid.AttrMap(fill, 'bg')

    widgets = {'utxt':txt, 'umap1':map1}

    client = ConsoleClient(indihost=args.host, indiport=args.port, **widgets)
    aloop = asyncio.new_event_loop()
    clienttast = aloop.create_task(client.asyncrun())

    evl = urwid.AsyncioEventLoop(loop=aloop)
    loop = urwid.MainLoop(map2, palette, unhandled_input=exit_on_q, event_loop=evl)
    loop.run()
