Example
=======

The following example shows the control of an LED On or Off switch. The driver for this switch is described at:

https://indipydriver.readthedocs.io

This is a simple client dedicated to the LED switch driver. A more complex general purpose client would learn about the remote drivers from testing the mappings of the IPyClient object, and learning which devices and vectors were available.


The client
^^^^^^^^^^

You would normally start by creating a subclass of IPyClient, for example::


    import asyncio, sys

    from indipyclient import IPyClient, setSwitchVector


    class LEDClient(IPyClient):

        """This is a console client, specific to a remote device with name 'led',
           with vector name 'ledswitchvector' and member 'ledswitchmember'."""

        async def rxevent(self, event):
            "The remote device is expected to send a value if the led changes state"
            match event:
                case setSwitchVector(devicename="led", vectorname="ledswitchvector") if 'ledswitchmember' in event.vector:
                    ledvalue = event.vector['ledswitchmember']
                    print(f"\nReceived value : {ledvalue}")

    async def control(client):
        "Request a switch value from the console, and send it"
        while True:
            try:
                message = client.messages.popleft()
            except IndexError:
                pass
            else:
                print(message[1])
            if not client.connected:
                await asyncio.sleep(2)
                continue
            try:
                # the device and vector should be recorded in this mapping
                vector = client['led']['ledswitchvector']
            except KeyError:
                # The device and vector have not been received yet, send a getProperties
                # requesting info from the driver and wait a couple of seconds
                client.send_getProperties()
                await asyncio.sleep(2)
                continue
            # a normal input statement would block, so use this to get console input
            print("Input On, or Off, or q to quit:")
            value = await asyncio.to_thread(sys.stdin.readline)
            value = value.strip()
            if value == "q" or value == "Q":
                client.shutdown()
                print("Shutting down - Please wait")
                break
            if value not in ("On", "Off"):
                print("Invalid instruction")
                continue
            # Send the new switch instruction, this calls the vector send_newSwitchVector method
            vector.send_newSwitchVector(members={'ledswitchmember':value})
            print(f"Instruction to turn LED {value} is sent")
            # and wait a bit for a response, which should be printed by rxevent
            await asyncio.sleep(1)
            # then repeat - which should give a new input command on the console


    async def main():
        client = LEDClient()
        t1 = client.asyncrun()
        t2 = control(client)
        await asyncio.gather(t1, t2)
        print("Client exited")

    asyncio.run(main())
