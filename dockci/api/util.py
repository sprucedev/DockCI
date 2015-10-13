from copy import copy

from flask import request
from flask_restful import fields


DT_FORMATTER = fields.DateTime('iso8601')


def set_attrs(obj, values):
    for attr_name, attr_value in values.items():
        setattr(obj, attr_name, attr_value)


def clean_attrs(values):
    return {
        attr_name: attr_value
        for attr_name, attr_value in values.items()
        if attr_name in request.values
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


def filter_query_args(parser, query):
    args = parser.parse_args()
    args = clean_attrs(args)
    return query.filter_by(**args)
