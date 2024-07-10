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

A possible reason to import ConsoleClient is to run the console, and a driver in a single script. The example below imports 'make_driver' from example1 of the indipydriver documentation, and also the ConsoleClient, and runs both together. Note that the client.stopped attribute is used to shut down the driver when quit is chosen on the client::


    import asyncio

    from indipyclient.console import ConsoleClient
    from example1 import make_driver


    async def monitor(client, driver):
        "This monitors the client, if it shuts down, it shuts down the driver"
        await client.stopped.wait()
        # the client has stopped, shut down the driver
        driver.shutdown()


    async def main(client, driver):
        "Run the driver and client together"
        try:
            await asyncio.gather(client.asyncrun(), driver.asyncrun(), monitor(client, driver))
        except asyncio.CancelledError:
            # avoid outputting stuff on the command line
            pass
        finally:
            # clear curses setup
            client.console_reset()


    if __name__ == "__main__":

        # Get driver, in this case from example1
        driver = make_driver()
        # set driver listening on localhost
        driver.listen()
        # create a ConsoleClient calling localhost
        client = ConsoleClient()
        # run them
        asyncio.run(main(client, driver))
