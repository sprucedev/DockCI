from contextlib import contextmanager
from unittest.mock import ANY, patch, PropertyMock

import flask
import pytest

from dockci.api.job import filter_jobs_by_request
from dockci.models.job import Job
from dockci.models.project import Project


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
    def test_filter_kwargs(self, mocker, mock_values, expected_kwargs):
        """
        Ensure that the correct kwargs are passed to ``Job.filtered_query``
        """

        filtered_query_mock = mocker.patch.object(
            Job, 'filtered_query', return_value='test val',
        )
        project_mock = mocker.patch('dockci.models.project.Project')
        query_mock = mocker.patch('sqlalchemy.orm.dynamic.Query')
        query_mock_obj = query_mock()
        project_mock.jobs.return_value = query_mock_obj

        with request_values(mock_values):
            filter_jobs_by_request(project_mock())
            filtered_query_mock.assert_called_with(
                query=ANY,
                **expected_kwargs
            )
