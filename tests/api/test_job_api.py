from unittest.mock import patch, PropertyMock

import pytest

from dockci.api.job import filter_jobs_by_request

from contextlib import contextmanager
import flask

@contextmanager
def request_values(values):
    """
    Mock request values. Python mocks isn't used because it attempts to delete
    things, and we get an exception
    """
    old_values = flask.request.values
    flask.request.values = values

    try:
        yield

    finally:
        flask.request.values = old_values


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
    def test_filter_kwargs(self, mock_values, expected_kwargs):
        """ Ensure that the correct kwargs are passed to ``filtered_jobs`` """

        class MockProject(object):
            filtered_jobs_called = False
            def filtered_jobs(self, **kwargs):
                self.filtered_jobs_called = True
                assert kwargs == expected_kwargs
                return 'test val'

        with request_values(mock_values):
            mock_project = MockProject()

            assert filter_jobs_by_request(mock_project) == 'test val'
            assert mock_project.filtered_jobs_called
