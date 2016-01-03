import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.base import ServiceBase


class TestServiceBase(object):
    """ Test the ``ServiceBase`` class """
    @pytest.mark.parametrize(
        'base_registry,exp_filter,query_count,query_first,exp', [
            ('quay.io', 'quay.io', 0, None, None),
            ('quay.io', 'quay.io', 1, 'testval', 'testval'),
            ('quay.io', 'quay.io', 2, 'testval', 'testval'),
            ('docker.io', 'docker.io', 0, None, None),
            ('docker.io', 'docker.io', 1, 'testval', 'testval'),

            (None, 'docker.io', 1, 'testval', 'testval'),
        ]
    )
    def test_auth_registry_gen(self,
                               mocker,
                               base_registry,
                               exp_filter,
                               query_count,
                               query_first,
                               exp):
        """ Test that auth registry is looked up correctly when not given """
        class MockResult(object):
            filter_by_called = False

            def filter_by(self, **kwargs):
                self.filter_by_called = True
                assert kwargs == {'base_name': exp_filter}
                return self

            def count(self):
                return query_count

            def first(self):
                return query_first

        mock_result = MockResult()
        filter_mock = mocker.patch.object(
            AuthenticatedRegistry, 'query', new=mock_result, create=True,
        )

        assert ServiceBase(base_registry=base_registry).auth_registry == exp
        assert mock_result.filter_by_called

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
