from flask import request
from flask_restful import fields, marshal_with, Resource
from flask_security import current_user, login_required

from . import DT_FORMATTER
from .base import BaseDetailResource, BaseRequestParser
from .util import new_edit_parsers, RewriteUrl
from dockci.models.auth import User
from dockci.server import API, DB


BASIC_FIELDS = {
    'id': fields.Integer(),
    'email': fields.String(),
    'active': fields.Boolean(),
}

LIST_FIELDS = {
    'detail': RewriteUrl('user_detail', rewrites=dict(user_id='id')),
}
LIST_FIELDS.update(BASIC_FIELDS)


DETAIL_FIELDS = {
    'confirmed_at': DT_FORMATTER,
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
    )
}

USER_NEW_PARSER = BaseRequestParser(bundle_errors=True)
USER_EDIT_PARSER = BaseRequestParser(bundle_errors=True)
new_edit_parsers(USER_NEW_PARSER, USER_EDIT_PARSER, SHARED_PARSER_ARGS)

USER_EDIT_PARSER.add_argument('active',
                              help="Whether or not the user can login")


class UserList(BaseDetailResource):
    @login_required
    @marshal_with(LIST_FIELDS)
    def get(self):
        return User.query.all()

    @marshal_with(DETAIL_FIELDS)
    def post(self):
        user = User()
        return self.handle_write(user, USER_NEW_PARSER)

class UserDetail(BaseDetailResource):
    @login_required
    @marshal_with(DETAIL_FIELDS)
    def get(self, user_id):
        return User.query.get_or_404(user_id)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, user_id, user=None):
        if user is None:
            user = User.query.get_or_404(user_id)
        return self.handle_write(user, USER_EDIT_PARSER)


class MeDetail(Resource):
    @login_required
    @marshal_with(DETAIL_FIELDS)
    def get(self):
        return current_user

    @login_required
    def post(self):
        return UserDetail().post(none, current_user)


API.add_resource(UserList,
                 '/users',
                 endpoint='user_list')
API.add_resource(UserDetail,
                 '/users/<int:user_id>',
                 endpoint='user_detail')
API.add_resource(MeDetail,
                 '/me',
                 endpoint='me_detail')
