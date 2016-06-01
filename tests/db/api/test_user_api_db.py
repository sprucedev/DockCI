""" Test ``dockci.api.user`` against the DB """
import pytest
import werkzeug.exceptions

from dockci.api.user import rest_add_roles, SECURITY_STATE
from dockci.models.auth import User, Role
from dockci.server import DB


@pytest.mark.usefixtures('db')
class TestRestAddRoles(object):
    """ Test the ``rest_add_roles`` function """
    def test_add_to_empty(self):
        """ Add a role to a user with no roles """
        user = User()
        rest_add_roles(user, ['admin'])

        assert [role.name for role in user.roles] == ['admin']

    def test_add_multiple(self):
        """ Add multiple roles to a user with no roles """
        role = Role(name='test')
        DB.session.add(role)
        DB.session.commit()

        user = User()
        rest_add_roles(user, ['admin', 'test'])
        assert [role.name for role in user.roles] == ['admin', 'test']

    def test_add_to_existing(self):
        """ Add a role to a user with an existing role """
        role = Role(name='test')
        user = SECURITY_STATE.datastore.create_user(
            email='test@example.com',
        )
        user.roles.append(Role.query.get(1))
        DB.session.add(role)
        DB.session.add(user)
        DB.session.commit()

        rest_add_roles(user, ['test'])
        assert [role.name for role in user.roles] == ['admin', 'test']

    def test_add_fake(self):
        """ Add a fake role to a user causes 400 and error message """
        user = User()
        with pytest.raises(werkzeug.exceptions.BadRequest) as excinfo:
            rest_add_roles(user, ['fake', 'more'])

        assert 'fake, more' in excinfo.value.data['message']['roles']
