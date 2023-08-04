Summary
=======

The following summarises how a client could be structured, describing the control of an LED On or Off switch. The driver for this switch is described at:

https://indipydriver.readthedocs.io


In this example, the actual control is from a thread running a console 'input' command. This is a simple client dedicted to the LED switch driver. A more complex general purpose client would learn about the remote drivers from the mappings of th IPyClient object.


The client
^^^^^^^^^^

You would normally start by creating a subclass of IPyClient, for example::

    import asyncio, time

    from indipyclient import IPyClient, setSwitchVector

    # Create a subclass of IPyClient, with your own rxevent and control methods

    class LEDClient(IPyClient):

        async def rxevent(self, event):
            # This example prints the LED switch value when received from the driver
            match event:
                case setSwitchVector(devicename="led", vectorname="ledswitchvector") if 'ledswitchmember' in event.vector:
                    ledvalue = event.vector['ledswitchmember']
                    print(f"\nReceived value : {ledvalue}")

        async def control(self):
            """This runs the function 'switchinstructions' in a separate thread"""
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, switchinstructions, self, loop)


    # In this example the control of the client runs in a separate thread

    def switchinstructions(ledclient, loop):
        # wait until the client has received info from the driver
        while True:
            if not ledclient.connected:
                time.sleep(2)
                continue
            try:
                # the client will receive the device and vector from the driver
                vector = ledclient['led']['ledswitchvector']
            except KeyError:
                # ledclient does not have the vector info yet
                time.sleep(2)
                continue
            time.sleep(0.5)
            value = input("Input On, or Off:")
            if value not in ("On", "Off"):
                print("Invalid instruction")
                continue
            # Send the new switch instruction, this calls the vector send_newSwitchVector method, which being
            # a coroutine, needs to be called in the event loop of the main thread.
            future = asyncio.run_coroutine_threadsafe(vector.send_newSwitchVector(members={'ledswitchmember':value}),
                                                      loop)
            print(f"Instruction to turn LED {value} is sent")
            # Wait for the result:
            result = future.result()


    client = LEDClient(blobfolder="~/blobs")
    asyncio.run(client.asyncrun())
