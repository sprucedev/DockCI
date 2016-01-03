import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.base import ServiceBase
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import DB


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
        """ Ensure project is not associated if service has no target """
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
        assert svc.project == None

    def test_registries_match(self):
        """ Ensure project is associated if registry base names match """
        svc = ServiceBase(repo='postgres', base_registry='registry:5000')
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
