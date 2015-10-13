""" Base classes and data for building the API """
from flask_restful import reqparse, Resource

from .util import clean_attrs, set_attrs
from dockci.server import DB


AUTH_FORM_LOCATIONS = ('form', 'headers', 'json')


class BaseDetailResource(Resource):
    """ Base resource for details API endpoints """
    def handle_write(self, model, parser):  # pylint:disable=no-self-use
        """ Parse request args, set attrs on the model, and commit """
        args = parser.parse_args(strict=True)
        args = clean_attrs(args)
        set_attrs(model, args)
        DB.session.add(model)
        DB.session.commit()
        return model


class BaseRequestParser(reqparse.RequestParser):
    """
    Request parser that should be used for all DockCI API endpoints. Adds
    ``username``, ``password``, and ``api_key`` fields for login
    """
    def __init__(self, *args, **kwargs):
        super(BaseRequestParser, self).__init__(*args, **kwargs)
        self.add_argument('username', location=AUTH_FORM_LOCATIONS)
        self.add_argument('password', location=AUTH_FORM_LOCATIONS)
        self.add_argument('api_key', location=('args',) + AUTH_FORM_LOCATIONS)
