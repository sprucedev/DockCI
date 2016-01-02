import pytest

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
