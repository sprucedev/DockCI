""" Session interface switcher """

from flask.sessions import SecureCookieSessionInterface, SessionMixin

from dockci.util import is_api_request


class FakeSession(dict, SessionMixin):
    """ Transient session-like object """
    pass


class SessionSwitchInterface(SecureCookieSessionInterface):
    """
    Session interface that uses ``SecureCookieSessionInterface`` methods,
    unless there's no session cookie and it's an API request
    """

    def __init__(self, app):
        self.app = app

    def open_session(self, app, request):
        session_id = request.cookies.get(self.app.session_cookie_name)

        if not session_id and is_api_request():
            return FakeSession()

        return super(SessionSwitchInterface, self).open_session(
            app, request,
        )

    def save_session(self, app, session, response):
        if isinstance(session, FakeSession):
            return

        return super(SessionSwitchInterface, self).save_session(
            app, session, response,
        )
