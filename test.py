
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




async def runit():

    client = ConsoleClient()
    t = asyncio.create_task(client.asyncrun())
    await asyncio.sleep(10)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    finally:
        # clear curses setup
        client.console_reset()



def main():
    """The commandline entry point to run the terminal client."""



    logger.addHandler(logging.NullHandler())

    # Starts the client, creates the console screens
    asyncio.run(runit())


    return 0


if __name__ == "__main__":
    sys.exit(main())
