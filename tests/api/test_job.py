from unittest.mock import patch, PropertyMock

import pytest

from dockci.api.job import filter_jobs_by_request

class TestFilterJobsByRequest(object):
    """ Test the ``filter_jobs_by_request`` function """
    @pytest.mark.parametrize('mock_values,expected_kwargs', [
        ({'versioned': ''}, {'versioned': True}),
        ({'versioned': 'y'}, {'versioned': True}),
        ({'versioned': 'no'}, {'versioned': False}),
        ({'completed': ''}, {'completed': True}),
        ({'passed': ''}, {'passed': True}),
        ({'branch': 'abc'}, {'branch': 'abc'}),
        (
            {'branch': 'abc', 'versioned': 'y'},
            {'branch': 'abc', 'versioned': True},
        ),
    ])
    def test_filter_kwargs(self, mocker, mock_values, expected_kwargs):
        """ Ensure that the correct kwargs are passed to ``filtered_jobs`` """

        class MockProject(object):
            filtered_jobs_called = False
            def filtered_jobs(self, **kwargs):
                self.filtered_jobs_called = True
                assert kwargs == expected_kwargs
                return 'test val'

        import flask
        mocker.patch.object(flask.request, 'values', new=mock_values)
        mock_project = MockProject()

        assert filter_jobs_by_request(mock_project) == 'test val'
        assert mock_project.filtered_jobs_called
