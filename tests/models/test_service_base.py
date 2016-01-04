import re

import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.base import ServiceBase
from dockci.models.job import Job
from dockci.models.project import Project


VALUE_ERROR_MESSAGE_RE = re.compile(
    r"Existing .+ value '[^']+' doesn't match new ([^ ]+)(.*)? value"
)


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

    def _test_value_error_in_attr(self, name, value, **kwargs):
        """ Tests that ValueError is raised in both init, and setter """
        # Raises in setter
        svc = ServiceBase(use_db=False, **kwargs)
        with pytest.raises(ValueError) as exc_info:
            setattr(svc, name, value)

        exc_message, = exc_info.value.args
        message_match = VALUE_ERROR_MESSAGE_RE.match(exc_message)
        assert message_match
        assert message_match.groups()[0] == name

        # Raises in init
        kwargs[name] = value
        with pytest.raises(ValueError) as exc_info:
            ServiceBase(use_db=False, **kwargs)

    def test_value_error_base_reg_auth_reg(self):
        """
        Test the ``ValueError`` raised setting ``base_registry`` with
        non-matching ``auth_registry``
        """
        self._test_value_error_in_attr(
            'base_registry', 'quay.io',
            auth_registry=AuthenticatedRegistry(base_name='docker.io'),
        )

    def test_value_error_base_reg_project(self):
        """
        Test the ``ValueError`` raised setting ``base_registry`` with
        non-matching ``project.target_registry``
        """
        project = Project(
            target_registry=AuthenticatedRegistry(base_name='docker.io'),
        )

        self._test_value_error_in_attr(
            'base_registry', 'quay.io',
            project=project,
        )

    def test_value_error_auth_reg_base_reg(self):
        """
        Test the ``ValueError`` raised setting ``auth_registry`` with
        non-matching ``base_registry_registry``
        """
        self._test_value_error_in_attr(
            'auth_registry', AuthenticatedRegistry(base_name='quay.io'),
            base_registry='docker.io',
        )

    def test_value_error_project_base_reg(self):
        """
        Test the ``ValueError`` raised setting ``project.target_registry`` with
        non-matching ``base_registry``
        """
        project = Project(
            target_registry=AuthenticatedRegistry(base_name='quay.io'),
        )

        self._test_value_error_in_attr(
            'project', project,
            base_registry='docker.io',
        )

    def test_value_error_project_auth_reg(self):
        """
        Test the ``ValueError`` raised setting ``project.target_registry`` with
        non-matching ``auth_registry``
        """
        project = Project(
            target_registry=AuthenticatedRegistry(base_name='quay.io'),
        )

        self._test_value_error_in_attr(
            'project', project,
            auth_registry=AuthenticatedRegistry(base_name='docker.io'),
        )

    def test_value_error_auth_reg_project(self):
        """
        Test the ``ValueError`` raised setting ``auth_registry`` with
        non-matching ``project.target_registry``
        """
        project = Project(
            target_registry=AuthenticatedRegistry(base_name='docker.io'),
        )

        self._test_value_error_in_attr(
            'auth_registry', AuthenticatedRegistry(base_name='quay.io'),
            project=project,
        )

    def test_value_error_job_project(self):
        """
        Test the ``ValueError`` raised setting ``job`` with non-matching
        ``project``
        """
        self._test_value_error_in_attr(
            'job', Job(project=Project()),
            project=Project(),
        )

    def test_value_error_project_job(self):
        """
        Test the ``ValueError`` raised setting ``project`` with non-matching
        ``job``
        """
        self._test_value_error_in_attr(
            'project', Project(),
            job=Job(project=Project()),
        )
