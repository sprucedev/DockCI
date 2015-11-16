""" API relating to configuration """
from flask_restful import fields, inputs, marshal_with, Resource
from flask_security import login_required

from .base import BaseDetailResource, BaseRequestParser
from .fields import NonBlankInput
from .util import new_edit_parsers
from dockci.models.auth import AuthenticatedRegistry
from dockci.server import API, DB


REGISTRY_BASIC_FIELDS = {
    'display_name': fields.String(),
    'base_name': fields.String(),
    'username': fields.String(),
    'email': fields.String(),
    'insecure': fields.Boolean(),
    'detail': fields.Url('registry_detail'),
}

REGISTRY_SHARED_PARSER_ARGS = {
    'display_name': dict(
        help="Registry display name",
        required=None, type=NonBlankInput(),
    ),
    'username': dict(help="Username for logging into the registry"),
    'password': dict(help="Password for logging into the registry"),
    'email': dict(help="Email for logging into the registry"),
    'insecure': dict(
        help="Whether connection is over HTTP (default HTTPS)",
        required=None, type=inputs.boolean,
    )
}

REGISTRY_NEW_PARSER = BaseRequestParser()
REGISTRY_EDIT_PARSER = BaseRequestParser()
new_edit_parsers(REGISTRY_NEW_PARSER,
                 REGISTRY_EDIT_PARSER,
                 REGISTRY_SHARED_PARSER_ARGS)


# pylint:disable=no-self-use


class RegistryList(Resource):
    """ API resource that handles listing registries """
    @marshal_with(REGISTRY_BASIC_FIELDS)
    def get(self):
        """ List of all projects """
        return AuthenticatedRegistry.query.all()


class RegistryDetail(BaseDetailResource):
    """
    API resource to handle getting registry details, creating new registries,
    updating existing registries, and deleting registries
    """
    @login_required
    @marshal_with(REGISTRY_BASIC_FIELDS)
    def get(self, base_name):
        """ Get registry details """
        return AuthenticatedRegistry.query.filter_by(
            base_name=base_name
        ).first_or_404()

    @login_required
    @marshal_with(REGISTRY_BASIC_FIELDS)
    def put(self, base_name):
        """ Create a new registry """
        registry = AuthenticatedRegistry(base_name=base_name)
        return self.handle_write(registry, REGISTRY_NEW_PARSER)

    @login_required
    @marshal_with(REGISTRY_BASIC_FIELDS)
    def post(self, base_name):
        """ Update an existing registry """
        registry = AuthenticatedRegistry.query.filter_by(
            base_name=base_name,
        ).first_or_404()
        return self.handle_write(registry, REGISTRY_EDIT_PARSER)

    @login_required
    def delete(self, base_name):
        """ Delete a registry """
        registry = AuthenticatedRegistry.query.filter_by(
            base_name=base_name,
        ).first_or_404()
        display_name = registry.display_name
        DB.session.delete(registry)
        DB.session.commit()
        return {'message': '%s deleted' % display_name}


API.add_resource(RegistryList,
                 '/registries',
                 endpoint='registry_list')
API.add_resource(RegistryDetail,
                 '/registries/<string:base_name>',
                 endpoint='registry_detail')
