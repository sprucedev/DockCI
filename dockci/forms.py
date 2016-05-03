""" WTForms for DockCI (including Flask-Security overrides) """
import logging

from functools import wraps

import flask_security.forms as sec_forms

from flask import request
from redis.exceptions import RedisError

from .server import redis_pool
from .util import check_auth_fail


THROTTLE_ERROR = ('Too many incorrect attempts have been made. Temporarily '
                  'throttled.')


def field_for_throttle_error(form):
    """
    Given a form, returns the field that throttle errors should be added to
    """
    for name in ('email', 'password'):
        try:
            return getattr(form, name)
        except AttributeError:
            pass


def sec_form_throttle(func):
    """ Wrap a security form in throttling logic """
    @wraps(func)
    def inner(self):
        """
        Check request throttling, then ident throtting on the email field if
        it exists. If either fail, add an error and return ``False``.
        Validates as normal if not throttled. If validation fails, throttle
        counter is incremented
        """
        try:
            field = field_for_throttle_error(self)
            with redis_pool() as redis_pool_:
                suffixes = [request.remote_addr]
                if hasattr(self, 'email'):
                    suffixes.append(self.email.data)

                windows, unthrottled = check_auth_fail(
                    suffixes, redis_pool_,
                )
                if not unthrottled:
                    field.errors = (THROTTLE_ERROR,)
                    return False

            valid = func(self)

            if not valid:
                value = str(hash(request))
                for window in windows:
                    window.add(value)

            return valid

        except RedisError:
            logging.exception("Authentication throttling disabled")
            return func(self)

    return inner


# pylint:disable=too-many-ancestors


class ForgotPasswordForm(sec_forms.ForgotPasswordForm):
    """
    See ``flask_security.forms.ForgotPasswordForm``

    Wraps validation throttling around the default form
    """
    @sec_form_throttle
    def validate(self):
        return super(ForgotPasswordForm, self).validate()


class LoginForm(sec_forms.LoginForm):
    """
    See ``flask_security.forms.LoginForm``

    Wraps validation throttling around the default faorm
    """
    @sec_form_throttle
    def validate(self):
        return super(LoginForm, self).validate()


class RegisterForm(sec_forms.RegisterForm):
    """
    See ``flask_security.forms.RegisterForm``

    Wraps validation throttling around the default form
    """
    @sec_form_throttle
    def validate(self):
        return super(RegisterForm, self).validate()


class ResetPasswordForm(sec_forms.ResetPasswordForm):
    """
    See ``flask_security.forms.ResetPasswordForm``

    Wraps validation throttling around the default form
    """
    @sec_form_throttle
    def validate(self):
        return super(ResetPasswordForm, self).validate()


class ChangePasswordForm(sec_forms.ChangePasswordForm):
    """
    See ``flask_security.forms.ChangePasswordForm``

    Wraps validation throttling around the default form
    """
    @sec_form_throttle
    def validate(self):
        return super(ChangePasswordForm, self).validate()
