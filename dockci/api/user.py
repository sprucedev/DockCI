""" API relating to User model objects """
from flask import abort
from flask_principal import Permission, RoleNeed
from flask_restful import abort as rest_abort
from flask_restful import fields, inputs, marshal_with, Resource
from flask_security import current_user, login_required
from flask_security.changeable import change_user_password

from .base import BaseDetailResource, BaseRequestParser
from .fields import GravatarUrl, NonBlankInput, RewriteUrl
from .util import clean_attrs, DT_FORMATTER, new_edit_parsers
from dockci.models.auth import Role, User, UserEmail
from dockci.server import API, APP, CONFIG, DB


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
    'avatar': GravatarUrl(attr_name='email'),
    'confirmed_at': DT_FORMATTER,
    'emails': fields.List(fields.String(attribute='email')),
    'roles': fields.List(fields.Nested({
        'name': fields.String(),
        'description': fields.String(),
    })),
}
DETAIL_FIELDS.update(BASIC_FIELDS)


SHARED_PARSER_ARGS = {
    'email': dict(
        help="Contact email address",
        required=None, type=NonBlankInput(),
    ),
    'password': dict(
        help="Password for user to authenticate",
        required=None, type=NonBlankInput(),
    ),
    'roles': dict(
        help="List of roles for the user",
        required=False, action='append'
    ),
}

USER_NEW_PARSER = BaseRequestParser()
USER_EDIT_PARSER = BaseRequestParser()
new_edit_parsers(USER_NEW_PARSER, USER_EDIT_PARSER, SHARED_PARSER_ARGS)

USER_EDIT_PARSER.add_argument('active',
                              help="Whether or not the user can login",
                              type=inputs.boolean)


SECURITY_STATE = APP.extensions['security']

ADMIN_PERMISSION = Permission(RoleNeed('admin'))


# pylint:disable=no-self-use


def rest_add_roles(user, role_names):
    """
    Add given roles to the user, aborting with error if some roles don't exist
    """
    role_names = set(role_names)
    roles = Role.query.filter(Role.name.in_(role_names)).all()
    if len(roles) != len(role_names):
        found_role_names = set(role.name for role in roles)
        rest_abort(400, message={
            "roles": "Roles not found: %s" % ", ".join(
                role_names.difference(found_role_names)
            )
        })

    existing_role_names = set(role.name for role in user.roles)
    role_names_to_add = role_names.difference(existing_role_names)
    roles_to_add = (role for role in roles if role.name in role_names_to_add)
    user.roles.extend(roles_to_add)


def rest_add_roles_perms(user, role_names):
    """ Check user permissions before adding roles """
    if not role_names:
        return
    if not ADMIN_PERMISSION.can():
        rest_abort(401, message={
            "roles": "Only administators can assign roles",
        })
    rest_add_roles(user, role_names)


class UserList(BaseDetailResource):
    """ API resource that handles listing users, and creating new users """
    @login_required
    @marshal_with(LIST_FIELDS)
    def get(self):
        """ List all users """
        return User.query.all()

    @marshal_with(DETAIL_FIELDS)
    def post(self):
        """ Create a new user """
        if not CONFIG.security_registerable_form:
            rest_abort(403, message="API user registration disabled")

        args = USER_NEW_PARSER.parse_args(strict=True)
        args = clean_attrs(args)

        # TODO throttle before error
        user = SECURITY_STATE.datastore.get_user(args['email'])
        if user is not None:
            rest_abort(400, message={
                "email": "Duplicate value '%s'" % args['email'],
            })

        user = SECURITY_STATE.datastore.create_user(**args)
        rest_add_roles_perms(user, args['roles'])
        DB.session.add(user)
        DB.session.commit()
        return user


class UserDetail(BaseDetailResource):
    """ API resource that handles getting user details, and updating users """
    @classmethod
    def user_or_404(cls, user_id):
        """ Return a user from the security store, or 404 """
        user = SECURITY_STATE.datastore.get_user(user_id)
        if user is None:
            return abort(404)

        return user

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def get(self, user_id):
        """ Get a user's details """
        return self.user_or_404(user_id)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, user_id, user=None):
        """ Update a user """
        if user is None:
            user = self.user_or_404(user_id)

        args = USER_EDIT_PARSER.parse_args(strict=True)
        args = clean_attrs(args)

        try:
            new_password = args.pop('password')
        except KeyError:
            pass
        else:
            change_user_password(user, new_password)

        rest_add_roles_perms(user, args.pop('roles'))
        return self.handle_write(user, data=args)


class MeDetail(Resource):
    """ Wrapper around ``UserDetail`` to user the current user """
    @login_required
    @marshal_with(DETAIL_FIELDS)
    def get(self):
        """ Get details of the current user """
        return current_user

    @login_required
    def post(self):
        """ Update the current user """
        return UserDetail().post(None, current_user)


class MeEmailDetail(Resource):
    """ Deletion of user email addresses """
    @login_required
    def delete(self, email):
        """ Delete an email from the current user """
        email = current_user.emails.filter(
            UserEmail.email.ilike(email),
        ).first_or_404()
        DB.session.delete(email)
        DB.session.commit()
        return {'message': '%s deleted' % email.email}


API.add_resource(UserList,
                 '/users',
                 endpoint='user_list')
API.add_resource(UserDetail,
                 '/users/<int:user_id>',
                 endpoint='user_detail')
API.add_resource(MeDetail,
                 '/me',
                 endpoint='me_detail')
API.add_resource(MeEmailDetail,
                 '/me/<string:email>',
                 endpoint='me_email_detail')
