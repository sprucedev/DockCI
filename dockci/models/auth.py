"""
Users and permissions models
"""

from flask_security import UserMixin, RoleMixin

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
    """ An OAuth token from a service, for a user """
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
