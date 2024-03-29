Installation
============


indipyclient requires python 3.10 or later.


If you are only using the terminal client, I recommed pipx, so to install you would use:

pipx install indipyclient

or if you want to run it, without installing:

pipx run indipyclient


If you are intending to import the indipyclient package to use the classes to create scripts, then you would normally install it with pip, usually into a virtual environment.

If you are using Debian, you may need the Python3 version of pip to obtain packages from Pypi.

apt-get install python3-pip

If you need further information on pip and virtual environments, try:https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/

Then install indipyclient from pypi with:

python3 -m pip install indipyclient
