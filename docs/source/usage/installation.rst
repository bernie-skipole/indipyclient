Installation
============

indipyclient requires python 3.10 or later.

If you are only using the terminal client, I recommend pipx.

sudo apt install pipx

To install indipyclient you would then use:

pipx install indipyclient

or if you want to run it, without installing:

pipx run indipyclient


For Import
==========

If you are intending to import the indipyclient package to use the classes to create scripts, then you would normally install it with pip, usually into a virtual environment.

If you are using Debian, you may need the Python3 version of pip to obtain packages from Pypi.

sudo apt install python3-pip

If you need further information on pip and virtual environments, try:

https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/

Then, activate your virtual environment, and install indipyclient with:

pip install indipyclient


Notes
=====

You could run the INDI service and drivers on one machine, and indipyclient on another if you specify the host and ports to connect to. However a more secure method would be to run both on the same machine using the default localhost, and do not open the port to network connections.  You can still uses the terminal remotely, by calling the machine using SSH, and in the SSH session, open the client by running indipyclient.

You should note that indipyclient relies on the Python Curses standard library package, and this is not available on Windows, in which case using an SSH connection and running indipyclient on the server is the best option.

The Curses library depends on the terminal providing support for terminal control sequences, if your terminal program is not compatable you may find the layout distorted, or certain features such as selecting fields by mouse click not working. In which case, if possible, pick a different emulation.
