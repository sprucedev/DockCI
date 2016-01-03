import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.base import ServiceBase


class TestServiceBase(object):
    """ Test the ``ServiceBase`` class """

    def test_auth_registry_given(self):
        """ Test that auth registry is passed right through when given """
        assert ServiceBase(auth_registry='testval').auth_registry == 'testval'

    def test_base_registry_gen(self):
        """ Test that base registry uses auth registry if not given """
        class MockAuthRegistry(object):
            base_name = 'testval'

        assert ServiceBase(
            auth_registry=MockAuthRegistry(),
        ).base_registry == 'testval'
