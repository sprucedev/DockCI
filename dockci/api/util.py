""" Utilities used when building APIs """
from copy import copy

from flask import request
from flask_restful import fields


DT_FORMATTER = fields.DateTime('iso8601')


def set_attrs(obj, values):
    """ Set attrs in values, on obj """
    for attr_name, attr_value in values.items():
        setattr(obj, attr_name, attr_value)


def clean_attrs(values):
    """
    Return only dict items from ``values`` whose keys exist in the request
    values, or json
    """
    return {
        attr_name: attr_value
        for attr_name, attr_value in values.items()
        if (
            attr_name in request.values or
            attr_name in request.json
        )
    }


def new_edit_parsers(new_parser, edit_parser, field_data):
    """
    Create parsers for new, and edit where 'required' args that have the value
    ``None`` are replaced with ``True`` for new, and ``False`` for edit (ie
    fields are required on creation, but not on edit/patch)
    """
    for parser, required_val in (
        (new_parser, True), (edit_parser, False),
    ):
        for arg_name, arg_kwargs in field_data.items():
            if 'required' in arg_kwargs and arg_kwargs['required'] is None:
                arg_kwargs = copy(arg_kwargs)
                arg_kwargs['required'] = required_val

            parser.add_argument(arg_name, **arg_kwargs)


def filter_query_args(parser, query):
    """ Use arguments parsed by ``parser`` to filter the SQLAlchemy query """
    args = parser.parse_args()
    args = clean_attrs(args)
    return query.filter_by(**args)
