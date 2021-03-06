""" Test ``dockci.api.user`` against the DB """
import json

import pytest
import werkzeug.exceptions

from dockci.api.user import rest_set_roles, SECURITY_STATE
from dockci.models.auth import User, Role
from dockci.server import DB


class TestRestSetRoles(object):
    """ Test the ``rest_set_roles`` function """
    @pytest.mark.usefixtures('db')
    def test_add_to_empty(self):
        """ Add a role to a user with no roles """
        user = User()
        rest_set_roles(user, ['admin'])

        assert [role.name for role in user.roles] == ['admin']

    @pytest.mark.usefixtures('db')
    def test_add_multiple(self, role):
        """ Add multiple roles to a user with no roles """
        user = User()
        rest_set_roles(user, ['admin', role.name])
        assert [role.name for role in user.roles] == ['admin', role.name]

    @pytest.mark.usefixtures('db')
    def test_set_with_existing(self, role, user):
        """ Set roles on a user with an existing role """
        user.roles.append(role)
        DB.session.add(role)
        DB.session.add(user)
        DB.session.commit()

        rest_set_roles(user, [role.name])
        assert [role.name for role in user.roles] == [role.name]

    @pytest.mark.usefixtures('db')
    def test_add_fake(self):
        """ Add a fake role to a user causes 400 and error message """
        user = User()
        with pytest.raises(werkzeug.exceptions.BadRequest) as excinfo:
            rest_set_roles(user, ['testfake', 'testmore'])

        assert 'testfake' in excinfo.value.data['message']['roles']
        assert 'testmore' in excinfo.value.data['message']['roles']


class TestUserAPI(object):
    """ Test the actual user API using Flask test client """
    @pytest.mark.usefixtures('db')
    def test_me(self, client, admin_user):
        """ User accessing me API sees correct data """
        response = client.get('/api/v1/me', headers={
            'x_dockci_username': admin_user.email,
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 200
        response_data = json.loads(response.data.decode())
        response_data.pop('avatar')  # gravatar is too hard
        assert response_data == dict(
            id=admin_user.id,
            confirmed_at=None,
            active=True,
            email=admin_user.email,
            emails=[admin_user.email],
            roles=[{'name': 'admin', 'description': 'Administrators'}],
        )

    @pytest.mark.usefixtures('db')
    def test_me_unauth(self, client):
        """ Guest access to the me API """
        assert client.get('/api/v1/me').status_code == 401

    @pytest.mark.usefixtures('db')
    def test_admin_update_roles(self, client, admin_user, role):
        """ Admin user updates roles """
        response = client.post('/api/v1/me', headers={
            'x_dockci_username': admin_user.email,
            'x_dockci_password': 'testpass',
        }, data={
            'roles': ['admin', role.name],
        })

        assert response.status_code == 200

        DB.session.refresh(admin_user)
        assert set(
            irole.name for irole in admin_user.roles
        ) == set(('admin', role.name))

    @pytest.mark.usefixtures('db')
    def test_no_admin_update_roles(self, client, user, role):
        """ Non-admin user updates roles """
        response = client.post('/api/v1/me', headers={
            'x_dockci_username': user.email,
            'x_dockci_password': 'testpass',
        }, data={
            'roles': [role.name],
        })

        assert response.status_code == 401

        DB.session.refresh(user)
        assert list(user.roles) == []

        DB.session.delete(role)
        DB.session.commit()

    @pytest.mark.usefixtures('db')
    def test_admin_delete_role(self, client, admin_user):
        """ Admin user deletes roles """
        response = client.delete('/api/v1/me/roles/admin', headers={
            'x_dockci_username': admin_user.email,
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 200

        DB.session.refresh(admin_user)
        assert len(admin_user.roles) == 0

    @pytest.mark.usefixtures('db')
    def test_no_admin_delete_role(self, client, user, role):
        """ Non-admin user deletes roles """
        user.roles.append(role)
        DB.session.add(user)
        DB.session.commit()

        response = client.delete('/api/v1/me/roles/%s' % role.name, headers={
            'x_dockci_username': user.email,
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 401

        DB.session.refresh(user)
        assert set(
            role.name for role in user.roles
        ) == set((role.name,))
