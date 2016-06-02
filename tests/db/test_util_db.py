import pytest

from dockci.server import APP
from dockci.util import require_me_or_admin


@APP.route('/_test/require_me_or_admin/<int:user_id>')
@APP.route('/api/v1/_test/require_me_or_admin/<int:user_id>')
@require_me_or_admin
def mock_view(user_id=None):
    """ A mock view that returns HTTP 999 """
    return "Test val", 999


class TestRequireMeOrAdmin(object):
    @pytest.mark.usefixtures('db')
    def test_api_as_admin(self, client, user, admin_user):
        response = client.get(
            '/api/v1/_test/require_me_or_admin/%s' % user.id,
            headers={
                'x_dockci_username': admin_user.email,
                'x_dockci_password': 'testpass',
            },
        )

        assert response.status_code == 999

    @pytest.mark.usefixtures('db')
    def test_api_as_me(self, client, user, admin_user):
        response = client.get(
            '/api/v1/_test/require_me_or_admin/%s' % user.id,
            headers={
                'x_dockci_username': user.email,
                'x_dockci_password': 'testpass',
            },
        )

        assert response.status_code == 999

    @pytest.mark.usefixtures('db')
    def test_api_as_other(self, client, user, admin_user):
        response = client.get(
            '/api/v1/_test/require_me_or_admin/%s' % admin_user.id,
            headers={
                'x_dockci_username': user.email,
                'x_dockci_password': 'testpass',
            },
        )

        assert response.status_code == 401
