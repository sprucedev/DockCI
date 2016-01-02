import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.base import ServiceBase
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
