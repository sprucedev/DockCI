from copy import copy

from flask import request
from flask_restful import fields


def set_attrs(obj, values):
    for attr_name, attr_value in values.items():
        setattr(obj, attr_name, attr_value)


def clean_attrs(values):
    return {
        attr_name: attr_value
        for attr_name, attr_value in values.items()
        if attr_name in request.form
    }


def new_edit_parsers(new_parser, edit_parser, fields):
    for parser, required_val in (
        (new_parser, True), (edit_parser, False),
    ):
        for arg_name, arg_kwargs in fields.items():
            if 'required' in arg_kwargs and arg_kwargs['required'] is None:
                arg_kwargs = copy(arg_kwargs)
                arg_kwargs['required'] = required_val

            parser.add_argument(arg_name, **arg_kwargs)


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
            data[field_set] = data[field_from]

        return super(RewriteUrl, self).output(key, data)
