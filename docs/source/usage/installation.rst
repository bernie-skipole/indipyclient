Installation
============

indipyclient requires python 3.10 or later, and has been written for Linux.

The package is available on Pypi, it has no dependencies other than the Python standard library.

However the terminal output uses the python standard library Curses package, which is not available on Windows.

indipyclient can be installed, like any other package, into a virtual environment using pip, in which case, with the environment activated, it can be invoked with:

python -m indipyclient <options>

or even just

indipyclient <options>

As it is a command line program it can also be simply installed using tools such as pipx, which take care of the virtual environment for you.

Without any options the client will attempt to connect to localhost.

You could run the INDI server on one machine, and indipyclient on another using the options to specify the host and port. However a more secure method would be to run both on the same machine using the default localhost, without the server opening the port to network connections.  You can still use the terminal remotely, by calling the machine using SSH, and in the SSH session, open the client by running indipyclient.

**For Import**

You can import the indipyclient package to create your own clients or scripts.

You would typically install indipyclient into a virtual environment. You can then create a script which imports indipyclient, create a class inheriting from the IPyClient class, and write your own code to interface with the class which will transmit and receive INDI data.

If you are using a GUI framework, you may prefer to use a framework native to your system, since importing a GUI framework may be complex. In which case use the --system-site-packages option to allow your script to use system packages::

    python3 -m venv --system-site-packages my_env_directory

    source my_env_directory/bin/activate

    pip install indipyclient


Where 'my_env_directory' is conventionally named .venv or venv in the project directory, or under a container directory for lots of virtual environments, such as ~/.virtualenvs
