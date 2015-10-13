from werkzeug.exceptions import HTTPException


class BaseActionException(HTTPException):
    response = None

    def __init__(self, action=None):
        if action is not None:
            self.action = action

    @property
    def description(self):
        return self.message_fs % self.action


class OnlyMeError(BaseActionException):
    code = 401
    action = "do this"
    message_fs = "Can not %s for another user"


class WrongAuthMethodError(BaseActionException):
    code = 400
    action = "another method"
    message_fs = "Must authenticate with %s"


class WrappedException(HTTPException):
    response = None

    def __init__(self, ex):
        self.description = str(ex)


class WrappedTokenError(WrappedException):
    code = 400


class WrappedValueError(WrappedException):
    code = 400
