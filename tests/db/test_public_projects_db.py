""" Test public project protections """
import json

import pytest

from dockci.models.project import Project
from dockci.server import DB


@pytest.fixture(scope='module')
def projects(request):
    vals = [
        Project(slug='pp-pub1', repo='', name='', utility=False, public=True),
        Project(slug='pp-pri1', repo='', name='', utility=False, public=False),
        Project(slug='pp-pub2', repo='', name='', utility=False, public=True),
        Project(slug='pp-pri2', repo='', name='', utility=False, public=False),
    ]

    for proj in vals:
        proj_ex = Project.query.filter_by(slug=proj.slug).first()
        if proj_ex:
            DB.session.delete(proj_ex)
    DB.session.commit()

    for proj in vals:
        DB.session.add(proj)
    DB.session.commit()

    def fin():
        for proj in vals:
            DB.session.delete(proj)
        DB.session.commit()
    request.addfinalizer(fin)

    return vals


@pytest.mark.usefixtures('db')
@pytest.mark.usefixtures('projects')
class TestPublicProjects(object):
    @pytest.mark.parametrize('url_prefix', ['', '/api/v1'])
    @pytest.mark.parametrize('url,exp_status', [
        ('/projects/pp-pub1', 200),
        ('/projects/pp-pri1', 404),
        ('/projects/pp-pub2', 200),
        ('/projects/pp-pri2', 404),
    ])
    def test_project_guest(self,
                           client,
                           url_prefix,
                           url,
                           exp_status,
                           ):
        """ Ensure only public projects accessible as guest """
        full_url = '%s%s' % (url_prefix, url)
        response = client.get(full_url)

        assert response.status_code == exp_status

    @pytest.mark.parametrize('url_prefix', ['', '/api/v1'])
    @pytest.mark.parametrize('url', [
        '/projects/pp-pub1',
        '/projects/pp-pri1',
        '/projects/pp-pub2',
        '/projects/pp-pri2',
    ])
    def test_project_user(self,
                          client,
                          user,
                          url_prefix,
                          url,
                          ):
        """ Ensure all projects accessible as user """
        full_url = '%s%s' % (url_prefix, url)
        response = client.get(full_url, headers={
            'x_dockci_username': user.email,
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 200
