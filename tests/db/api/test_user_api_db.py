""" Test ``dockci.api.user`` against the DB """
import json

import pytest
import werkzeug.exceptions

from dockci.api.user import rest_add_roles, SECURITY_STATE
from dockci.models.auth import User, Role
from dockci.server import DB


class TestRestAddRoles(object):
    """ Test the ``rest_add_roles`` function """
    @pytest.mark.usefixtures('db')
    def test_add_to_empty(self):
        """ Add a role to a user with no roles """
        user = User()
        rest_add_roles(user, ['admin'])

        assert [role.name for role in user.roles] == ['admin']

    @pytest.mark.usefixtures('db')
    def test_add_multiple(self):
        """ Add multiple roles to a user with no roles """
        role = Role(name='test')
        DB.session.add(role)
        DB.session.commit()

        user = User()
        rest_add_roles(user, ['admin', 'test'])
        assert [role.name for role in user.roles] == ['admin', 'test']

    @pytest.mark.usefixtures('db')
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

    @pytest.mark.usefixtures('db')
    def test_add_fake(self):
        """ Add a fake role to a user causes 400 and error message """
        user = User()
        with pytest.raises(werkzeug.exceptions.BadRequest) as excinfo:
            rest_add_roles(user, ['testfake', 'testmore'])

        assert 'testfake' in excinfo.value.data['message']['roles']
        assert 'testmore' in excinfo.value.data['message']['roles']


class TestUserAPI(object):
    """ Test the actual user API using Flask test client """
    @pytest.mark.usefixtures('db')
    def test_me(self, client, admin_user):
        """ User accessing me API sees correct data """
        response = client.get('/api/v1/me', headers={
            'x_dockci_username': 'admin@example.com',
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 200
        assert json.loads(response.data.decode()) == dict(
            id=admin_user.id,
            confirmed_at=None,
            active=True,
            email='admin@example.com',
            emails=['admin@example.com'],
            roles=[{'name': 'admin', 'description': 'Administrators'}],
            avatar='https://s.gravatar.com/avatar/e64c7d89f26bd1972efa854d13d7dd61',
        )

    @pytest.mark.usefixtures('db')
    def test_me_unauth(self, client):
        """ Guest access to the me API """
        assert client.get('/api/v1/me').status_code == 401

    @pytest.mark.usefixtures('db')
    def test_admin_update_roles(self, client, admin_user):
        """ Admin user updates roles """
        role = Role(name='test')
        DB.session.add(role)
        DB.session.commit()

        response = client.post('/api/v1/me', headers={
            'x_dockci_username': 'admin@example.com',
            'x_dockci_password': 'testpass',
        }, data={
            'roles': ['test'],
        })

        assert response.status_code == 200

        DB.session.refresh(admin_user)
        assert set(
            role.name for role in admin_user.roles
        ) == set(('admin', 'test'))

    @pytest.mark.usefixtures('db')
    def test_no_admin_update_roles(self, client, user):
        """ Admin user updates roles """
        role = Role(name='test2')
        DB.session.add(role)
        DB.session.commit()

        response = client.post('/api/v1/me', headers={
            'x_dockci_username': 'user@example.com',
            'x_dockci_password': 'testpass',
        }, data={
            'roles': ['test2'],
        })

        print(response.data)
        assert response.status_code == 401

        DB.session.refresh(user)
        assert list(user.roles) == []
