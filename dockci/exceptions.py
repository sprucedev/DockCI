"""
DockCI exceptions
"""

import requests.exceptions

from requests.packages.urllib3.exceptions import ProtocolError


class HumanOutputError(object):
    """
    Mixin for an Exception that can be handled by user output of the string
    repr
    """
    human_str = True


class InvalidOperationError(Exception):
    """
    Raised when a call is not valid at the current time
    """
    pass


class AlreadyBuiltError(Exception):
    """
    Raised when a versioned job already exists in the repository
    """
    pass


class AlreadyRunError(InvalidOperationError):
    """
    Raised when a job or stage is attempted to be run that has already been
    started/completed
    """
    runnable = None

    def __init__(self, runnable):
        super(AlreadyRunError, self).__init__()
        self.runnable = runnable


class DockerUnreachableError(Exception, HumanOutputError):
    """ Raised when Docker is unreachable for some reason """
    def __init__(self, client, exception, message=None):
        super(DockerUnreachableError, self).__init__()
        self.client = client
        self.exception = exception
        self.message = message

    def __str__(self):
        if self.message is not None:
            message = self.message
        else:
            message = str(self.root_exception())

        host = getattr(self.client, 'base_url', str(self.client))

        return "Error with the Docker server '{host}': {message}".format(
            host=host,
            message=message,
        )

    def root_exception(self, exception=None):
        """
        Unwrap the tangled mess of requests exceptions to get the root cause
        of the given exception
        """
        if exception is None:
            exception = self.exception

        if exception is None:
            raise ValueError("No exception given")

        if isinstance(exception, requests.exceptions.SSLError):
            if isinstance(exception.args[0], Exception):
                return self.root_exception(exception.args[0])

            return exception.args[1]

        elif isinstance(exception, requests.exceptions.ConnectionError):
            return self.root_exception(exception.args[0])
        elif isinstance(exception, ProtocolError):
            return self.root_exception(exception.args[1])

        return exception
