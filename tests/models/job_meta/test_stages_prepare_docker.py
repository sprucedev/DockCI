import re
import sys

import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.project import Project
from dockci.models.job import Job
from dockci.models.job_meta.stages_prepare_docker import PushPrepStage


class TestPushPrepStage(object):
    """ Test the PushPrepStage """
    def setup_method(self, method):
        self.registry = AuthenticatedRegistry(base_name='localhost:5000')
        self.project = Project(
            slug='testproject',
            target_registry=self.registry,
            branch_pattern=re.compile('master'),
        )

    @pytest.mark.parametrize('job,images,expected_ids', [
        (
            Job(tag="v0.0.1"),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:v0.0.1',
                    'localhost:5000/testproject:latest-master',
                )},
            ),
            (),
        ),
        (
            Job(git_branch='master'),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:v0.0.1',
                    'localhost:5000/testproject:latest-master',
                )},
            ),
            (),
        ),
        (
            Job(tag="v0.0.1", git_branch='master'),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:v0.0.1',
                    'localhost:5000/testproject:latest-master',
                )},
            ),
            ('abc',),
        ),
        (
            Job(tag="v0.0.1", git_branch='master'),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:v0.0.1',
                    'localhost:5000/testproject:latest-master',
                    'localhost:5000/testproject:othertag',
                )},
            ),
            (),
        ),
        (
            Job(tag="v0.0.1", git_branch='master'),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:0.0.1',
                    'localhost:5000/testproject:latest-master',
                    'localhost:5000/testproject:othertag',
                )},
            ),
            ('localhost:5000/testproject:0.0.1',),
        ),
        (
            Job(tag="v0.0.1", git_branch='master'),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:0.0.1',
                    'localhost:5000/testproject:latest-master',
                )},
            ),
            ('localhost:5000/testproject:0.0.1', 'abc'),
        ),
        (
            Job(tag="v0.0.1", git_branch='master'),
            (
                {'Id': 'abc', 'RepoTags': (
                    'localhost:5000/testproject:0.0.1',
                    'localhost:5000/testproject:othertag',
                )},
                {'Id': 'def', 'RepoTags': (
                    'localhost:5000/testproject:latest-master',
                )},
            ),
            ('localhost:5000/testproject:0.0.1', 'def'),
        ),
    ])
    def test_set_old_image_ids(self, job, images, expected_ids):
        """ Test that PushPrepStage.set_old_image_ids works as expected """
        class MockDocker(object):
            def images(self):
                return images

        job.project = self.project
        job._docker_client = MockDocker()
        stage = PushPrepStage(job)

        stage.set_old_image_ids(sys.stdout)
        assert set(job._old_image_ids) == set(expected_ids)
