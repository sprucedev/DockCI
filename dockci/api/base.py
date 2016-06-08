""" Base classes and data for building the API """
from flask_restful import abort, reqparse, Resource

from .util import clean_attrs, set_attrs
from dockci.server import DB
from dockci.util import unique_model_conflicts


AUTH_FORM_LOCATIONS = ('form', 'json')


class BaseDetailResource(Resource):
    """ Base resource for details API endpoints """
    # pylint:disable=no-self-use
    def handle_write(self, model, parser=None, data=None):
        """ Parse request args, set attrs on the model, and commit """
        assert parser is not None or data is not None, (
            "Must give either parser, or data")

        if data is None:
            args = parser.parse_args(strict=True)
            args = clean_attrs(args)
        else:
            args = data

        unique_columns = {name
                          for name, column in model.__mapper__.c.items()
                          if column.unique}
        conflict_checks = {
            name: value
            for name, value in args.items()
            if name in unique_columns
        }

        conflicts = {
            field_name: "Duplicate value '%s'" % getattr(
                query.first(), field_name,
            )
            for field_name, query in unique_model_conflicts(
                model.__class__,
                ignored_id=model.id,
                **conflict_checks
            ).items()
        }
        if conflicts:
            abort(400, message=conflicts)

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
        self.add_argument('x_dockci_username', location=AUTH_FORM_LOCATIONS)
        self.add_argument('x_dockci_password', location=AUTH_FORM_LOCATIONS)
        self.add_argument('x_dockci_api_key',
                          location=('args',) + AUTH_FORM_LOCATIONS)
        self.add_argument('X-Dockci-Username',
                          location='headers',
                          dest='hx_dockci_username')
        self.add_argument('X-Dockci-Password',
                          location='headers',
                          dest='hx_dockci_password')
        self.add_argument('X-Dockci-Api-Key',
                          location='headers',
                          dest='hx_dockci_api_key')
