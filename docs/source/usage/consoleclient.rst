ConsoleClient
=============

The class indipyclient.console.ConsoleClient is primarily intended to be run from the command line.

Inspect indipyclient.\_\_main\_\_.py to see how that is done.

This class calls on the standard library curses package to create the terminal client.

.. autoclass:: indipyclient.console.ConsoleClient
   :members: debug_verbosity, shutdown, console_reset, asyncrun

**Attributes**

Important attributes are:

**self.connected**

Set to True if a connection is made.

**self.stopped**

This is an asyncio.Event object, which is set when asyncrun is finished.

awaiting self.stopped.wait() will wait until the client has shutdown. This could be used to clear up after a client has closed.


DriverClient
============

A possible reason to import ConsoleClient is to run the console, driver and instrument in a single script. The example below imports 'make_driver' from example1 of the indipydriver documentation, and also the ConsoleClient, and runs them together::


    import asyncio

    # stop anything going to the screen
    import logging
    logger = logging.getLogger()
    logger.addHandler(logging.NullHandler())

    from indipyclient.console import ConsoleClient
    from example1 import make_driver

    async def main(client, driver):
        """Run the client and driver"""

        # start the driver
        drivertask = asyncio.create_task( driver.asyncrun() )

        # start the client, and wait for it to close
        try:
            await client.asyncrun()
        finally:
            # Ensure the terminal is cleared
            client.console_reset()
        print("Shutting down, please wait")

        # ask the driver to stop
        driver.shutdown()

        # wait for the driver to shutdown
        await drivertask


    if __name__ == "__main__":

        # make a driver for the thermostat
        thermodriver = make_driver("Thermostat", 15)
        # set driver listening on localhost
        thermodriver.listen()
        # create a ConsoleClient calling localhost
        client = ConsoleClient()
        # run all coroutines
        asyncio.run( main(client, thermodriver) )
