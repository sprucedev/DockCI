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
        Project(slug='pp-pub', repo='', name='', utility=False, public=True),
        Project(slug='pp-pri', repo='', name='', utility=False, public=False),
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


API_URL_FS_LIST = [
    '/api/v1/projects/{project_slug}',
    '/api/v1/projects/{project_slug}/jobs',
    '/api/v1/projects/{project_slug}/jobs/commits',
    '/api/v1/projects/{project_slug}/jobs/{job_slug}',
    '/api/v1/projects/{project_slug}/jobs/{job_slug}/stages',
    '/api/v1/projects/{project_slug}/jobs/{job_slug}/stages/{stage_slug}',
]
URL_FS_LIST = [
    '/projects/{project_slug}',
    '/projects/{project_slug}/jobs/{job_slug}',
] + API_URL_FS_LIST


class TestPublicProjects(object):
    @pytest.mark.usefixtures('stages')
    @pytest.mark.parametrize('url_fs', URL_FS_LIST)
    @pytest.mark.parametrize('project_slug,exp_status', [
        ('pp-pub', 200),
        ('pp-pri', 404),
    ])
    def test_guest(self,
                   client,
                   jobs,
                   url_fs,
                   project_slug,
                   exp_status,
                   ):
        """ Ensure only public projects accessible as guest """
        project = Project.query.filter_by(slug=project_slug)[0]
        job = project.jobs[0]
        stage = job.job_stages[0]

        full_url = url_fs.format(
            project_slug=project.slug,
            job_slug=job.slug,
            stage_slug=stage.slug,
        )
        response = client.get(full_url)

        assert response.status_code == exp_status

    @pytest.mark.usefixtures('stages')
    @pytest.mark.parametrize('url_fs', URL_FS_LIST)
    @pytest.mark.parametrize('project_slug', [
        'pp-pub', 'pp-pri',
    ])
    def test_user(self,
                  client,
                  jobs,
                  user,
                  url_fs,
                  project_slug,
                  ):
        """ Ensure all projects accessible as user """
        project = Project.query.filter_by(slug=project_slug)[0]
        job = project.jobs[0]
        stage = job.job_stages[0]

        full_url = url_fs.format(
            project_slug=project.slug,
            job_slug=job.slug,
            stage_slug=stage.slug,
        )
        response = client.get(full_url, headers={
            'x_dockci_username': user.email,
            'x_dockci_password': 'testpass',
        })

        assert response.status_code == 200

    @pytest.mark.usefixtures('stages')
    @pytest.mark.parametrize('url_fs', API_URL_FS_LIST)
    @pytest.mark.parametrize('project_slug', [
        'pp-pub', 'pp-pri',
    ])
    def test_agent(self,
                   client,
                   jobs,
                   agent_token,
                   url_fs,
                   project_slug,
                   ):
        """ Ensure all projects accessible as user """
        project = Project.query.filter_by(slug=project_slug)[0]
        job = project.jobs[0]
        stage = job.job_stages[0]

        full_url = url_fs.format(
            project_slug=project.slug,
            job_slug=job.slug,
            stage_slug=stage.slug,
        )
        response = client.get(full_url, headers={
            'x_dockci_api_key': agent_token,
        })

        assert response.status_code == 200
