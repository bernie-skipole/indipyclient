.. _queclient:


QueClient
=========

If you prefer to run the async code in one thread, and perhaps a GUI display or other blocking code, in another, a common method would be to introduce queues to pass data between threads.

A class 'QueClient' in module indipyclient.queclient is available if you wish to use it, together with a function that when called with transmit and receive queues will instantiate and run the class.


.. autoclass:: indipyclient.queclient.QueClient
   :members: debug_verbosity, asyncrun

As QueClient inherits from PyClient it also has methods send_newVector etc., but these would not normally be called, since the point of this class is to send and receive all data via the two queues. The format of the items in these queues is described below.

A function runqueclient is provided which can be used to create and run a QueClient.

.. autofunction:: indipyclient.queclient.runqueclient

This is normally used by first creating two queues::

    txque = queue.Queue(maxsize=4)
    rxque = queue.Queue(maxsize=4)

Then run the function runqueclient in its own thread::

    clientthread = threading.Thread(target=runqueclient, args=(txque, rxque))
    clientthread.start()

Then run your own code, reading rxque, and transmitting on txque.

To exit, use txque.put(None) to shut down the queclient, and finally wait for the clientthread to stop::

    txque.put(None)
    clientthread.join()


The events transmitted as items in these queues are described as:


txque
=====

txque can be either a queue.Queue, an asyncio.Queue, or a collections.deque object.

Your code should place items for transmission onto this queue, typically in response to a user action.

If you have set txque to be a collections.deque object, you should use txque.append(item) to set items on the right of the queue, as the QueClient will read it with popleft.

The possible items are:


**"snapshot"**

Sending this string is a request for the current snapshot of the client, which will be returned via the rxque.

Your code could send this on startup, to obtain an initial working snapshot of client data.


**None**

This indicates the QueClient should shut down.


**(devicename, vectorname, value)**

A three item tuple or list, where value is normally a membername to membervalue dictionary.

If this vector is a BLOB Vector, the value dictionary should be {membername:(blobvalue, blobsize, blobformat)...}

The blobvalue could be a bytes object, a pathlib.Path, a string path to a file or a file-like object. If blobsize of zero is used, the size value sent will be set to the number of bytes in the BLOB.

Instead of a value dictionary, if value is set to a string, one of  "Never", "Also", "Only" an enableBLOB with this value will be sent.


rxque
=====

rxque can be either a queue.Queue, an asyncio.Queue, or a collections.deque object.

As data is received from the server, the QueClient will place items on this queue which your code should receive.  If you have set rxque to be a collections.deque object, the items will be appended on the right of the queue, so your code should use popleft.

The items placed will be a named tuple with five attributes:

**item.eventtype**

A string, normally one of "Message", "getProperties", "Delete", "Define", "DefineBLOB", "Set" or "SetBLOB".

These indicate data is received from the client, and the type of event.

It could also be the string "snapshot", which does not indicate a received event, but is a response to a snapshot request received from txque.

It could also be the string "TimeOut", which indicates an expected update has not occurred.

**item.devicename**

Either the device name causing the event, or None for a system message, or for the snapshot request, where a device name is not relevant.

**item.vectorname**

Either the vector name causing the event, or None for a system message, or device message, or for the snapshot request.

**item.timestamp**

The event timestamp, or None for the snapshot request.

**item.snapshot**

A Snap object, being a snapshot of the client, which has been updated by the event. This holds all device, vector and member values.

Your code would typically inspect the snapshot, and operate any function you require on the updated values.


Example GUI client
==================

If you are using a GUI framework, you may prefer to use a framework native to your system. In which case, when creating a virtual environment, use the --system-site-packages option to allow your script to use system packages::

    python3 -m venv --system-site-packages my_env_directory

    source my_env_directory/bin/activate

    pip install indipyclient


Where 'my_env_directory' is conventionally named .venv or venv in the project directory, or under a container directory for lots of virtual environments, such as ~/.virtualenvs

An example GUI client, (ledguiclient.py) created with tkinter and using QueClient, has been written at:

https://github.com/bernie-skipole/inditest/tree/main/gui

It is a simple client meant to operate with an LED driver, also listed in the above directory.

It generates a window:

.. image:: ./ledclient.png

A further, very similar example, ledguiclient2.py which uses Python GTK+ 3 has also been written, and is in the same directory, it produces an almost identical window.
