import pytest

from dockci.models.auth import AuthenticatedRegistry


BASE_AUTHENTICATED_REGISTRY = dict(
    id=1,
    display_name='Display name',
    base_name='Base name',
    username='Username',
    password='Password',
    email='Email',
    insecure=False,
)


class TestHash(object):
    """ Test ``AuthenticatedRegistry.__hash__`` """
    def test_hash_eq(self):
        """ Test when hash should be equal """
        left = AuthenticatedRegistry(**BASE_AUTHENTICATED_REGISTRY)
        right = AuthenticatedRegistry(**BASE_AUTHENTICATED_REGISTRY)

        assert hash(left) == hash(right)

    @pytest.mark.parametrize('attr_name,attr_value', [
        ('id', 7),
        ('display_name', 'different'),
        ('base_name', 'different'),
        ('username', 'different'),
        ('password', 'different'),
        ('email', 'different'),
        ('insecure', True),
    ])
    def test_hash_ne(self, attr_name, attr_value):
        """ Test when hash should be not equal """
        left = AuthenticatedRegistry(**BASE_AUTHENTICATED_REGISTRY)
        right = AuthenticatedRegistry(**BASE_AUTHENTICATED_REGISTRY)

        setattr(right, attr_name, attr_value)

        assert hash(left) != hash(right)
