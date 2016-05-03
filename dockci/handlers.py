""" Handlers for Flask, and Flask plugins """
import json
import logging

import jwt
import rollbar

from flask import (abort,
                   flash,
                   got_request_exception,
                   redirect,
                   request,
                   request_finished,
                   Response,
                   )
from flask_login import login_url
from flask_security.utils import verify_and_update_password
from redis.exceptions import RedisError

from .api.base import BaseRequestParser
from .api.util import clean_attrs
from .models.auth import User
from .server import APP, CONFIG, DB, MAIL, redis_pool
from .util import check_auth_fail, is_api_request


SECURITY_STATE = APP.extensions['security']
LOGIN_MANAGER = SECURITY_STATE.login_manager
LOGIN_FORM = BaseRequestParser()


@LOGIN_MANAGER.unauthorized_handler
def unauthorized_handler():
    """
    Handler for unauthorized user requests. If API request, handle with a basic
    auth dialog (for users) and a JSON response (for APIs). Otherwise, treat
    the login like ``flask-login`` treats them. In most cases (all cases for
    DockCI; extra code left for completeness), this redirects to the login
    form
    """
    message = None
    if LOGIN_MANAGER.login_message:
        message = LOGIN_MANAGER.login_message
        if LOGIN_MANAGER.localize_callback is not None:
            message = LOGIN_MANAGER.localize_callback(message)

    if is_api_request(request):
        args = clean_attrs(LOGIN_FORM.parse_args())
        if 'username' in args or 'password' in args or 'api_key' in args:
            message = "Invalid credentials"

        return Response(
            json.dumps({'message': message or "Unauthorized"}),
            401,
            {
                'Content-Type': 'application/json',
                'WWW-Authenticate': 'Basic realm="DockCI API"',
            },
        )

    else:
        if not LOGIN_MANAGER.login_view:
            abort(401)

        if message:
            flash(message, category=LOGIN_MANAGER.login_message_category)

        return redirect(login_url(LOGIN_MANAGER.login_view, request.url))


@LOGIN_MANAGER.request_loader
def request_loader(request_):
    """
    Request loader that first tries the ``LOGIN_FORM`` request parser (see
    ``try_reqparser``), then basic auth (see ``try_basic_auth``)
    """
    idents_set = set()
    try:
        with redis_pool() as redis_pool_:
            req_windows, unthrottled = check_auth_fail(
                (request_.remote_addr,), redis_pool_,
            )
            if not unthrottled:
                return None

            user = try_reqparser(idents_set) or try_basic_auth(idents_set)

            ident_windows, unthrottled = check_auth_fail(
                idents_set, redis_pool_,
            )
            if not unthrottled:
                return None

            if user is not None:
                return user

            # Only update where a login attempt was made
            if len(idents_set) > 0:
                # Unique value in all windows
                value = str(hash(request_))

                for window in req_windows + ident_windows:
                    window.add(value)

    except RedisError:
        logging.exception("Authentication throttling disabled")
        return try_reqparser(idents_set) or try_basic_auth(idents_set)


@SECURITY_STATE.send_mail_task
def security_mail_task(message):
    """ Handle mail failures in Flask-Security by flashing a message """
    try:
        MAIL.send(message)
    except Exception:  # pylint:disable=broad-except
        flash("Couldn't send email message", 'danger')


def try_jwt(token, idents_set):
    """ Check a JWT token """
    if token is None:
        return None

    try:
        jwt_data = jwt.decode(token, CONFIG.secret)
    except jwt.exceptions.InvalidTokenError:
        return None

    else:
        idents_set.add(str(jwt_data['sub']))
        user = User.query.get(jwt_data['sub'])
        if user is not None:
            idents_set.add(user.email.lower())
        return user


def try_user_pass(password, lookup, idents_set):
    """
    Try to authenticate a user based on first a user ID, if ``lookup`` can be
    parsed into an ``int``, othewise it's treated as a user email. Uses
    ``verify_and_update_password`` to check the password
    """
    if lookup is not None:
        idents_set.add(str(lookup).lower())

    if password is None or lookup is None:
        return None

    user = SECURITY_STATE.datastore.get_user(lookup)

    if not user:
        return None

    idents_set.add(user.email.lower())
    idents_set.add(str(user.id))

    if verify_and_update_password(password, user):
        return user

    return None


def try_all_auth(api_key, password, username, idents_set):
    """ Attempt auth with the API key, then username/password """
    user = try_jwt(api_key, idents_set)
    if user is not None:
        return user

    user = try_user_pass(password, username, idents_set)
    if user is not None:
        return user

    return None


def try_reqparser(idents_set):
    """
    Use ``try_all_auth`` to attempt authorization from the ``LOGIN_FORM``
    ``RequestParser``. Will take JWT keys from ``x_dockci_api_key``, and
    ``x_dockci_username``/``x_dockci_password`` combinations
    """
    args = LOGIN_FORM.parse_args()
    return try_all_auth(
        args['x_dockci_api_key'] or args['hx_dockci_api_key'],
        args['x_dockci_password'] or args['hx_dockci_password'],
        args['x_dockci_username'] or args['hx_dockci_username'],
        idents_set,
    )


def try_basic_auth(idents_set):
    """
    Use ``try_all_auth`` to attempt authorization from HTTP basic auth. Only
    the password is used for API key
    """
    auth = request.authorization
    if not auth:
        return None

    return try_all_auth(
        auth.password,
        auth.password,
        auth.username,
        idents_set,
    )


@got_request_exception.connect
@request_finished.connect
def db_rollback(*args, **kwargs):  # pylint:disable=unused-argument
    """ Rollback the DB transaction when the request completes """
    dirty = DB.session.dirty
    if dirty:
        message = (
            "Dirty session had to be rolled back. Objects were: %s" % dirty
        )
        rollbar.report_message(message, 'warning')
        logging.error(message)

        DB.session.rollback()
