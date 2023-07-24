
import sys


class ParseException(Exception):
    "Raised if an error occurs when parsing received data"
    pass


def reporterror(message):
    "Prints message to stderr"
    print(message, file=sys.stderr)
