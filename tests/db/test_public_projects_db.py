""" Test public project protections """
import json

import pytest

from dockci.models.project import Project
from dockci.models.job import Job, JobStageTmp
from dockci.server import DB


def model_helper(request, models):
    """ Add models, and remove after """
    for model in models:
        DB.session.add(model)
    DB.session.commit()

    def fin():
        for model in models:
            DB.session.delete(model)
        DB.session.commit()
    request.addfinalizer(fin)

    return models


def clean():
    """ Delete all projects, jobs, stages """
    JobStageTmp.query.delete()
    Job.query.delete()
    Project.query.delete()
    DB.session.commit()


@pytest.fixture
def projects(request, db):
    """ Add pub x2 and pri x2 """
    clean()
    vals = [
        Project(slug='pp-pub1', repo='', name='', utility=False, public=True),
        Project(slug='pp-pri1', repo='', name='', utility=False, public=False),
        Project(slug='pp-pub2', repo='', name='', utility=False, public=True),
        Project(slug='pp-pri2', repo='', name='', utility=False, public=False),
    ]
    return model_helper(request, vals)


@pytest.fixture
def jobs(request, projects, db):
    """ Add a job for each project """
    vals = [
        Job(project=project, commit='test', repo_fs='')
        for project in projects
    ]
    return model_helper(request, vals)


@pytest.fixture
def stages(request, jobs, db):
    """ Add a stage for each job """
    vals = [
        JobStageTmp(job=job, slug='test')
        for job in jobs
    ]
    return model_helper(request, vals)


class TestPublicProjects(object):
    @pytest.mark.usefixtures('stages')
    @pytest.mark.parametrize('url_prefix', ['', '/api/v1'])
    @pytest.mark.parametrize('url_fs', [
        '/projects/{project_slug}',
        '/projects/{project_slug}/jobs/{job_slug}',
        '/projects/{project_slug}/jobs/{job_slug}/stages/{stage_slug}',
    ])
    @pytest.mark.parametrize('project_slug,exp_status', [
        ('pp-pub1', 200),
        ('pp-pri1', 404),
        ('pp-pub2', 200),
        ('pp-pri2', 404),
    ])
    def test_guest(self,
                   client,
                   jobs,
                   url_prefix,
                   url_fs,
                   project_slug,
                   exp_status,
                   ):
        """ Ensure only public projects accessible as guest """
        project = Project.query.filter_by(slug=project_slug)[0]
        job = project.jobs[0]
        stage = job.job_stages[0]

        full_url = ('%s%s' % (url_prefix, url_fs)).format(
            project_slug=project.slug,
            job_slug=job.slug,
            stage_slug=stage.slug,
        )
        response = client.get(full_url)

        assert response.status_code == exp_status

    @pytest.mark.usefixtures('stages')
    @pytest.mark.parametrize('url_prefix', ['', '/api/v1'])
    @pytest.mark.parametrize('url_fs', [
        '/projects/{project_slug}',
        '/projects/{project_slug}/jobs/{job_slug}',
        '/projects/{project_slug}/jobs/{job_slug}/stages/{stage_slug}',
    ])
    @pytest.mark.parametrize('project_slug', [
        'pp-pub1', 'pp-pri1', 'pp-pub2', 'pp-pri2',
    ])
    def test_user(self,
                  client,
                  jobs,
                  user,
                  url_prefix,
                  url_fs,
                  project_slug,
                  ):
        """ Ensure all projects accessible as user """
        project = Project.query.filter_by(slug=project_slug)[0]
        job = project.jobs[0]
        stage = job.job_stages[0]

        full_url = ('%s%s' % (url_prefix, url_fs)).format(
            project_slug=project.slug,
            job_slug=job.slug,
            stage_slug=stage.slug,
        )
        response = client.get(full_url, headers={
            'x_dockci_username': user.email,
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 200
