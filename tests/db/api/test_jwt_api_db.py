""" Test ``dockci.api.jwt`` against the DB """
import json

import pytest


class TestJwtServiceNew(object):
    """ Test the ``JwtServiceNew`` resource """
    @pytest.mark.usefixtures('db')
    def test_agent_role(self, client, admin_user):
        """ Test creating a service token with the agent internal role """
        response = client.post('/api/v1/jwt/service', headers={
            'x_dockci_username': admin_user.email,
            'x_dockci_password': 'testpass',
        }, data={
            'name': 'test',
            'roles': ['agent'],
        })

        assert response.status_code == 201

        response_data = json.loads(response.data.decode())
        token = response_data.pop('token')
        assert response_data == {}

        response = client.get('/api/v1/me/jwt', headers={
            'x_dockci_api_key': token
        })
        response_data = json.loads(response.data.decode())
        response_data.pop('iat')

        assert response_data == dict(
            name='test',
            roles=['agent'],
            sub='service',
            sub_detail='/api/v1/users/service',
        )

    @pytest.mark.usefixtures('db')
    def test_non_admin(self, client, user):
        """ Test creating a service token without admin """
        response = client.post('/api/v1/jwt/service', headers={
            'x_dockci_username': user.email,
            'x_dockci_password': 'testpass',
        }, data={
            'name': 'test',
            'roles': ['agent'],
        })

        assert response.status_code == 401

    @pytest.mark.usefixtures('db')
    def test_unknown_role(self, client, admin_user):
        """ Test creating a service token with the agent internal role """
        response = client.post('/api/v1/jwt/service', headers={
            'x_dockci_username': admin_user.email,
            'x_dockci_password': 'testpass',
        }, data={
            'name': 'test',
            'roles': ['faketest'],
        })

        assert response.status_code == 400

        response_data = json.loads(response.data.decode())
        assert response_data == {
            'message': {'roles': 'Roles not found: faketest'}
        }
