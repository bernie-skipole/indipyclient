Events
======


You would typically create a subclass of IPyClient, and overwrite the method::

    async def rxevent(self, event):

If your client needs to act as events are received from the driver, this method could be written using match and case to determine the type of event, and read the event contents, and then take any appropriate action.



.. autoclass:: indipyclient.Message

.. autoclass:: indipyclient.delProperty


def Vector events also all have attributes vectorname, label, group, state and message. They are also a mapping of membername:value, which should contain all the vector member names, so for example event['membername'] would give the value of that member.

.. autoclass:: indipyclient.defSwitchVector

.. autoclass:: indipyclient.defTextVector

.. autoclass:: indipyclient.defNumberVector

.. autoclass:: indipyclient.defLightVector

.. autoclass:: indipyclient.defBLOBVector


set Vector events all have attributes vectorname, message and state (which could be None if not given due to no change of state). These events are also a mapping of membername:value, so for example event['membername'] would give the value of that member. However this object may not include members if they have not changed.


.. autoclass:: indipyclient.setSwitchVector

.. autoclass:: indipyclient.setTextVector

.. autoclass:: indipyclient.setNumberVector

.. autoclass:: indipyclient.setLightVector

.. autoclass:: indipyclient.setBLOBVector
