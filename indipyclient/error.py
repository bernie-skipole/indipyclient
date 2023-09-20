

class ParseException(Exception):
    "Raised if an error occurs when parsing received data"
    pass


class ConnectionTimeOut(Exception):
    "Raised if the connection has failed"
    pass
