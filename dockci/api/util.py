from copy import copy

from flask import request
from flask_restful.reqparse import RequestParser


AUTH_LOCATIONS = ('form', 'headers')


class DefaultRequestParser(RequestParser):
    def __init__(self, *args, **kwargs):
        super(DefaultRequestParser, self).__init__(*args, **kwargs)
        self.add_argument('username', location=AUTH_LOCATIONS)
        self.add_argument('password', location=AUTH_LOCATIONS)
        self.add_argument('api_key', location=('args',) + AUTH_LOCATIONS)


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
