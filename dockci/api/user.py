from flask import request
from flask_restful import fields, marshal_with, Resource
from flask_security import current_user, login_required

from .base import BaseDetailResource, BaseRequestParser
from .util import new_edit_parsers
from dockci.models.auth import User
from dockci.server import API, DB


BASIC_FIELDS = {
    'id': fields.Integer(),
    'email': fields.String(),
    'active': fields.Boolean(),
}

LIST_FIELDS = {
    'detail': fields.Url('user_detail'),
}
LIST_FIELDS.update(BASIC_FIELDS)


DETAIL_FIELDS = {
    'confirmed_at': fields.DateTime(),
    #'roles': fields.Nested(),
}
DETAIL_FIELDS.update(BASIC_FIELDS)


SHARED_PARSER_ARGS = {
    'email': dict(
        help="Contact email address",
        required=None,
    ),
    'password': dict(
        help="Password for user to authenticate",
        required=None,
    ),
    'active': dict(
        help="Whether or not the user can login",
        required=False,
    ),
}

USER_NEW_PARSER = BaseRequestParser(bundle_errors=True)
USER_EDIT_PARSER = BaseRequestParser(bundle_errors=True)
new_edit_parsers(USER_NEW_PARSER, USER_EDIT_PARSER, SHARED_PARSER_ARGS)


class UserList(Resource):
    @login_required
    @marshal_with(LIST_FIELDS)
    def get(self):
        return User.query.all()


class UserDetail(BaseDetailResource):
    @login_required
    @marshal_with(DETAIL_FIELDS)
    def get(self, id):
        return User.query.get_or_404(id)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def put(self, id):
        user = User()
        return self.handle_write(user, USER_NEW_PARSER)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, id):
        user = User.query.get_or_404(id)
        return self.handle_write(user, USER_EDIT_PARSER)


class MeDetail(Resource):
    @login_required
    @marshal_with(DETAIL_FIELDS)
    def get(self):
        return current_user

    def post(self):
        return self.get()


API.add_resource(UserList,
                 '/users',
                 endpoint='user_list')
API.add_resource(UserDetail,
                 '/users/<int:id>',
                 endpoint='user_detail')
API.add_resource(MeDetail,
                 '/me',
                 endpoint='me_detail')
