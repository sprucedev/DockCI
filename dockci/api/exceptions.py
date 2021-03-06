""" Exceptions relating to API issues """
from werkzeug.exceptions import HTTPException


class BaseActionExceptionMixin(HTTPException):
    """ An HTTP exception for when an action can't be performed """
    response = None
    no_rollbar = True

    def __init__(self, action=None):
        super(BaseActionExceptionMixin, self).__init__()
        if action is not None:
            self.action = action

    @property
    def description(self):
        """ Description of the action that couldn't be performed """
        return self.message_fs % self.action


class OnlyMeError(BaseActionExceptionMixin):
    """
    Raised when a user tries an action on another user that can only be
    performed on themselves
    """
    code = 401
    action = "do this"
    message_fs = "Can not %s for another user"


class WrongAuthMethodError(BaseActionExceptionMixin):
    """ Raised when user authenticated with an invalid auth method """
    code = 400
    action = "another method"
    message_fs = "Must authenticate with %s"


class NoModelError(BaseActionExceptionMixin):
    """ Raised when a model couldn't be found for setting the relation """
    code = 400
    action = "Object"
    message_fs = "%s couldn't be found"


class WrappedException(HTTPException):
    """
    Wraps an exception in HTTPException so that it can have a status code
    """
    response = None
    no_rollbar = True

    def __init__(self, ex):
        super(WrappedException, self).__init__()
        self.description = str(ex)


class WrappedTokenError(WrappedException):
    """ Wrapper for the JWT TokenError to return HTTP 400 """
    code = 400


class WrappedValueError(WrappedException):
    """ Wrapper for the ValueError to return HTTP 400 """
    code = 400
