"""
Users and permissions models
"""

from flask_security import UserMixin, RoleMixin

from yaml_model import LoadOnAccess, Model, ValidationError

from dockci.server import DB

roles_users = DB.Table(
    'roles_users',
    DB.Column('user_id', DB.Integer(), DB.ForeignKey('user.id'), index=True),
    DB.Column('role_id', DB.Integer(), DB.ForeignKey('role.id')),
)


class Role(DB.Model, RoleMixin):
    """ Role model for granting permissions """
    id = DB.Column(DB.Integer(), primary_key=True)
    name = DB.Column(DB.String(80), unique=True)
    description = DB.Column(DB.String(255))

    def __str__(self):
        return '<{klass}: {name}>'.format(
            klass=self.__class__.__name__,
            name=self.name,
        )


class OAuthToken(DB.Model):
    id = DB.Column(DB.Integer(), primary_key=True)
    service = DB.Column(DB.String(31))
    key = DB.Column(DB.String(80))
    secret = DB.Column(DB.String(80))
    scope = DB.Column(DB.String(255))
    user_id = DB.Column(DB.Integer, DB.ForeignKey('user.id'), index=True)
    user = DB.relationship('User',
                           foreign_keys="OAuthToken.user_id",
                           backref=DB.backref('oauth_tokens', lazy='dynamic'))

    def __str__(self):
        return '<{klass}: {service} for {email}>'.format(
            klass=self.__class__.__name__,
            service=self.service,
            email=self.user.email,
        )


class User(DB.Model, UserMixin):
    """ User model for authentication """
    id = DB.Column(DB.Integer, primary_key=True)
    email = DB.Column(DB.String(255), unique=True, index=True)
    password = DB.Column(DB.String(255))
    active = DB.Column(DB.Boolean())
    confirmed_at = DB.Column(DB.DateTime())
    roles = DB.relationship('Role',
                            secondary=roles_users,
                            backref=DB.backref('users', lazy='dynamic'))

    def __str__(self):
        return '<{klass}: {email} ({active})>'.format(
            klass=self.__class__.__name__,
            email=self.email,
            active='active' if self.active else 'inactive'
        )


# class User(Model, UserMixin):
#     """
#     User model for authentication
#     """
#     slug = None

#     email = LoadOnAccess(index=True)
#     password = LoadOnAccess(default=lambda _: None)
#     active = LoadOnAccess(input_transform=bool, default=False)
#     confirmed_at = LoadOnAccess()

#     oauth_tokens = LoadOnAccess(generate=lambda _: {})

#     roles = []

#     @property
#     def id(self):  # pylint:disable=invalid-name
#         """
#         Synonym for slug
#         """
#         return self.slug

#     def __init__(self, slug=None, **kwargs):
#         if kwargs.get('roles', None):
#             raise ValueError("Can's assign roles just yet")

#         try:
#             del kwargs['roles']

#         except KeyError:
#             pass

#         if slug is None and 'email' in kwargs:
#             slug = kwargs['email']

#         if not slug:
#             raise ValueError("Must give either a slug, or an email")

#         self.slug = slug

#         super(User, self).__init__()

#         for var_name, value in kwargs.items():
#             if var_name in self._load_on_access:  # pylint:disable=no-member
#                 setattr(self, var_name, value)
#             else:
#                 raise AttributeError("Unknown attribute: '%s'" % var_name)

#     def validate(self):
#         errors = []

#         if self.email is None:
#             errors.append("Email address is required")

#         if errors:
#             raise ValidationError(errors)

#         return True


# class Role(Model, RoleMixin):
#     """
#     Role model for permissions granting
#     """
#     slug = None
#     description = LoadOnAccess()

#     @property
#     def id(self):  # pylint:disable=invalid-name
#         """
#         Synonym for slug
#         """
#         return self.slug

#     @property
#     def name(self):
#         """
#         Synonym for slug
#         """
#         return self.slug

#     def __init__(self, slug):
#         self.slug = slug
#         super(Role, self).__init__()
