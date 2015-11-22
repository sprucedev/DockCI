"""
Flask RESTful fields, and WTForms input validators for validation and
marshaling
"""

import re

from functools import wraps

from flask_restful import fields


class RewriteUrl(fields.Url):
    """
    Extension of the Flask RESTful Url field that allows you to remap object
    fields to different names
    """
    def __init__(self,
                 endpoint=None,
                 absolute=False,
                 scheme=None,
                 rewrites=None):
        super(RewriteUrl, self).__init__(endpoint, absolute, scheme)
        self.rewrites = rewrites or {}

    def output(self, key, obj):
        data = obj.__dict__
        for field_set, field_from in self.rewrites.items():
            attr_path_data = obj
            for attr_path in field_from.split('.'):
                if attr_path_data is None:
                    return None
                attr_path_data = getattr(attr_path_data, attr_path)

            data[field_set] = attr_path_data

        return super(RewriteUrl, self).output(key, data)


class RegexField(fields.String):
    """ Output a Python compiled regex as string """
    def output(self, key, obj):
        regex = getattr(obj, key, None)
        if regex is None:
            return None

        return regex.pattern


class NonBlankInput(object):
    """ Don't allow a field to be blank, or None """
    def _raise_error(self, name):  # pylint:disable=no-self-use
        """ Central place to handle invalid input """
        raise ValueError("The '%s' parameter can not be blank" % name)

    def __call__(self, value, name):
        if value is None:
            self._raise_error(name)
        try:
            if value.strip() == '':
                self._raise_error(name)
        except AttributeError:
            pass

        return value


class RegexInput(object):
    """ Validate a RegEx """
    def __call__(self, value, name):  # pylint:disable=no-self-use
        try:
            return re.compile(value)
        except re.error as ex:
            raise ValueError(str(ex))


def strip(field_type):
    """ Decorator to strip whitespace on input values before parsing """
    @wraps(field_type)
    def inner(value, name):
        """ Strip whitespace, pass to input field type """
        try:
            value = value.strip()
        except AttributeError:
            pass

        return field_type(value, name)

    return inner
