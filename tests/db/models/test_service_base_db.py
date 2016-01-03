import itertools

import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.base import ServiceBase
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import DB


BASIC_ATTR_TESTS = [
    dict(
        kwargs=dict(
            name='DockCI',
            base_registry='quay.io',
            repo='spruce/dockci',
            tag='special',
        ),
        exp=dict(
            display='DockCI - quay.io/spruce/dockci:special',
            display_full='DockCI - quay.io/spruce/dockci:special',
            slug='quay_io_spruce_dockci_special',
            name='DockCI',
            base_registry='quay.io',
            repo='spruce/dockci',
            tag='special',
        ),
    ),
    dict(
        kwargs=dict(
            name='DockCI',
            repo='spruce/dockci',
            tag='special',
        ),
        exp=dict(
            display='DockCI - spruce/dockci:special',
            display_full='DockCI - docker.io/spruce/dockci:special',
            slug='spruce_dockci_special',
            name='DockCI',
            base_registry='docker.io',
            repo='spruce/dockci',
            tag='special',
        ),
    ),
    dict(
        kwargs=dict(
            repo='spruce/dockci',
            tag='special',
        ),
        exp=dict(
            display='spruce/dockci:special',
            display_full='spruce/dockci - docker.io/spruce/dockci:special',
            slug='spruce_dockci_special',
            name='spruce/dockci',
            base_registry='docker.io',
            repo='spruce/dockci',
            tag='special',
        ),
    ),
    dict(
        kwargs=dict(
            base_registry='quay.io',
            repo='spruce/dockci',
            tag='special',
        ),
        exp=dict(
            display='quay.io/spruce/dockci:special',
            display_full='spruce/dockci - quay.io/spruce/dockci:special',
            slug='quay_io_spruce_dockci_special',
            name='spruce/dockci',
            base_registry='quay.io',
            repo='spruce/dockci',
            tag='special',
        ),
    ),
    dict(
        kwargs=dict(
            repo='spruce/dockci',
        ),
        exp=dict(
            display='spruce/dockci',
            display_full='spruce/dockci - docker.io/spruce/dockci:latest',
            slug='spruce_dockci',
            name='spruce/dockci',
            base_registry='docker.io',
            repo='spruce/dockci',
            tag='latest',
        ),
    ),
    dict(
        kwargs=dict(
            base_registry='quay.io',
            repo='spruce/dockci',
        ),
        exp=dict(
            display='quay.io/spruce/dockci',
            display_full='spruce/dockci - quay.io/spruce/dockci:latest',
            slug='quay_io_spruce_dockci',
            name='spruce/dockci',
            base_registry='quay.io',
            repo='spruce/dockci',
            tag='latest',
        ),
    ),
    dict(
        kwargs=dict(
            name='DockCI',
            repo='spruce/dockci',
        ),
        exp=dict(
            display='DockCI - spruce/dockci',
            display_full='DockCI - docker.io/spruce/dockci:latest',
            slug='spruce_dockci',
            name='DockCI',
            base_registry='docker.io',
            repo='spruce/dockci',
            tag='latest',
        ),
    ),
    dict(
        kwargs=dict(
            name='DockCI',
            base_registry='docker.io',
            repo='spruce/dockci',
            tag='latest'
        ),
        exp=dict(
            display='DockCI - docker.io/spruce/dockci:latest',
            display_full='DockCI - docker.io/spruce/dockci:latest',
            slug='docker_io_spruce_dockci_latest',
            name='DockCI',
            base_registry='docker.io',
            repo='spruce/dockci',
            tag='latest',
        ),
    )
]
BASIC_ATTR_TESTS = list(itertools.chain.from_iterable(
    [
        (kwargs_vals['kwargs'], attr_name, exp_value)
        for attr_name, exp_value in kwargs_vals['exp'].items()
    ]
    for kwargs_vals in BASIC_ATTR_TESTS
))

@pytest.mark.usefixtures('db')
class TestServiceBaseAttrs(object):
    @pytest.mark.parametrize('kwargs,attr_name,exp', BASIC_ATTR_TESTS)
    def test_basic(self, kwargs, attr_name, exp):
        """ Test defaults and generation for many basic attributes """
        assert getattr(ServiceBase(**kwargs), attr_name) == exp

@pytest.mark.usefixtures('db')
class TestServiceBaseRegistry(object):
    def test_no_project_exists(self):
        svc = ServiceBase(repo='postgres')
        assert svc.base_registry == 'docker.io'
        assert svc.auth_registry == None

    def test_docker_io_exists(self):
        svc = ServiceBase(repo='postgres')
        registry = AuthenticatedRegistry(
            base_name='docker.io',
            display_name='Docker Hub',
        )
        DB.session.add(registry)
        DB.session.commit()

        assert svc.auth_registry == registry

    def test_project_target(self):
        svc = ServiceBase(repo='postgres')
        registry = AuthenticatedRegistry(
            base_name='registry:5000',
            display_name='Local',
        )
        project = Project(
            slug='postgres',
            name='Postgres Test',
            repo='',
            utility=False,
            target_registry=registry
        )
        DB.session.add(registry)
        DB.session.add(project)
        DB.session.commit()

        assert svc.auth_registry == registry
        assert svc.image == 'registry:5000/postgres'

    def test_registry_docker_io_exists(self):
        svc = ServiceBase(repo='postgres')
        proj_registry = AuthenticatedRegistry(
            base_name='registry:5000',
            display_name='Local',
        )
        hub_registry = AuthenticatedRegistry(
            base_name='docker.io',
            display_name='Docker Hub',
        )
        project = Project(
            slug='postgres',
            name='Postgres Test',
            repo='',
            utility=False,
            target_registry=proj_registry
        )
        DB.session.add(proj_registry)
        DB.session.add(hub_registry)
        DB.session.add(project)
        DB.session.commit()

        assert svc.auth_registry == proj_registry
        assert svc.image == 'registry:5000/postgres'


@pytest.mark.usefixtures('db')
class TestServiceBaseProject(object):
    def setup_method(self, _):
        pass

    def test_no_project_exists(self):
        """ Ensure when no project exists, None is returned """
        svc = ServiceBase(repo='postgres')
        assert svc.project == None

    def test_project_no_target(self):
        """ Ensure project is found where it has no target """
        svc = ServiceBase(repo='postgres')
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        DB.session.add(project)
        DB.session.commit()
        assert svc.project == project

    def test_project_target_svc_no_registry(self):
        """ Ensure project is associated if service has no target """
        svc = ServiceBase(repo='postgres')
        registry = AuthenticatedRegistry(
            base_name='registry:5000',
            display_name='Test Reg',
        )
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
            target_registry=registry,
        )
        DB.session.add(registry)
        DB.session.add(project)
        DB.session.commit()
        assert svc.project == project

    def test_service_registry_project_none(self):
        """ Ensure project is not associated if service has auth registry """
        registry = AuthenticatedRegistry(
            base_name='registry:5000',
            display_name='Test Reg',
            username='project'
        )
        svc = ServiceBase(repo='postgres', auth_registry=registry)
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        DB.session.add(registry)
        DB.session.add(project)
        DB.session.commit()
        assert svc.project == None


@pytest.mark.usefixtures('db')
class TestServiceBaseJob(object):
    def setup_method(self, _):
        pass

    def test_no_project_exists(self):
        """ Ensure when no project exists, None is returned """
        svc = ServiceBase(repo='postgres')
        assert svc.job == None

    def test_job_exists(self):
        """ Ensure when a passing, versioned job exists, it is found """
        svc = ServiceBase(repo='postgres')
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        job = Job(
            project=project,
            result='success',
            tag='v0.0.0',
            repo_fs='',
            commit='',
        )
        DB.session.add(project)
        DB.session.add(job)
        DB.session.commit()
        assert svc.job == job

    def test_job_failed(self):
        """ Ensure when no passing job exists, None is returned """
        svc = ServiceBase(repo='postgres')
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        job = Job(
            project=project,
            result='fail',
            tag='v0.0.0',
            repo_fs='',
            commit='',
        )
        DB.session.add(project)
        DB.session.add(job)
        DB.session.commit()
        assert svc.job == None

    def test_job_not_versioned(self):
        """ Ensure when no tagged job exists, None is returned """
        svc = ServiceBase(repo='postgres')
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        job = Job(
            project=project,
            result='success',
            repo_fs='',
            commit='',
        )
        DB.session.add(project)
        DB.session.add(job)
        DB.session.commit()
        assert svc.job == None

    def test_job_multiple(self):
        """ Ensure when multiple jobs match, last one is returned """
        svc = ServiceBase(repo='postgres')
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        results = ['fail', 'success', 'success', 'fail']
        jobs = [
            Job(
                project=project,
                result=results[idx],
                tag='v0.0.1',
                repo_fs='',
                commit='',
            )
            for idx in range(4)
        ]

        DB.session.add(project)

        for job in jobs:
            DB.session.add(job)

        DB.session.commit()
        assert svc.job == jobs[2]

    def test_job_image_tag(self):
        """ Ensure when image tag is used to lookup jobs """
        svc = ServiceBase(repo='postgres', tag='9.4')
        project = Project(
            slug='postgres',
            name='Test PG',
            repo='/test/PG',
            utility=False,
        )
        tags = ['9.4', '9.5']
        jobs = [
            Job(
                project=project,
                result='success',
                tag=tags[idx],
                repo_fs='',
                commit='',
            )
            for idx in range(2)
        ]

        DB.session.add(project)

        for job in jobs:
            DB.session.add(job)

        DB.session.commit()
        assert svc.job == jobs[0]
