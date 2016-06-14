""" Test ``dockci.api.jwt`` against the DB """
import json

import pytest


def job_url_for(job):
    """ Job API URL for the given job """
    return '/api/v1/projects/{project}/jobs/{job}'.format(
        project=job.project.slug,
        job=job.slug,
    )

def stage_url_for(stage):
    """ Stage API URL for the given stage """
    return '{base}/stages/{stage}'.format(
        base=job_url_for(stage.job),
        stage=stage.slug,
    )

@pytest.mark.usefixtures('db')
class TestJobEdit(object):
    """ Test the ``JobDetail.patch`` resource """
    def test_as_admin(self, client, job, admin_user):
        """ Ensure even admins are denied """
        original_commit = job.commit
        job_url = job_url_for(job)
        response = client.patch(
            job_url,
            headers={
                'x_dockci_username': admin_user.email,
                'x_dockci_password': 'testpass',
            },
            data={'commit': 'updated'},
        )

        assert response.status_code == 401

        response_data = json.loads(response.data.decode())
        assert response_data == {'message': 'Only an agent can do this'}

        response = client.get(job_url)
        response_data = json.loads(response.data.decode())
        assert response_data.pop('commit') == original_commit

    def test_as_agent(self, client, job, agent_token):
        """ Ensure agents can update """
        job_url = job_url_for(job)
        response = client.patch(
            job_url,
            headers={'x_dockci_api_key': agent_token},
            data={'commit': 'updated'},
        )

        assert response.status_code == 200

        response_data = json.loads(response.data.decode())
        assert response_data.pop('commit') == 'updated'

        response = client.get(job_url)
        response_data = json.loads(response.data.decode())
        assert response_data.pop('commit') == 'updated'

    @pytest.mark.parametrize('field_name', ['start_ts', 'complete_ts'])
    def test_update_date(self, client, job, agent_token, field_name):
        """ Ensure dates are updated correctly """
        job_url = job_url_for(job)
        response = client.patch(
            job_url,
            headers={'x_dockci_api_key': agent_token},
            data={field_name: '2016-02-03T04:05:06'},
        )

        assert response.status_code == 200

        response_data = json.loads(response.data.decode())
        assert response_data.pop(field_name) == '2016-02-03T04:05:06'

        response = client.get(job_url)
        response_data = json.loads(response.data.decode())
        assert response_data.pop(field_name) == '2016-02-03T04:05:06'



@pytest.mark.usefixtures('db')
class TestStageDetail(object):
    """ Test the ``StageDetail`` resource """
    def test_as_admin(self, client, job, admin_user):
        """ Ensure even admins are denied """
        stage_url = '{base}/stages/teststage'.format(base=job_url_for(job))
        response = client.put(
            stage_url,
            headers={
                'x_dockci_username': admin_user.email,
                'x_dockci_password': 'testpass',
            },
            data={'success': True},
        )

        assert response.status_code == 401

        response_data = json.loads(response.data.decode())
        assert response_data == {'message': 'Only an agent can do this'}

        response = client.get(stage_url)
        assert response.status_code == 404

    def test_create(self, client, job, agent_token):
        """ Ensure agents can update """
        stage_url = '{base}/stages/teststage'.format(base=job_url_for(job))
        response = client.put(
            stage_url,
            headers={'x_dockci_api_key': agent_token},
            data={'success': 'true'},
        )

        assert response.status_code == 200  # TODO 201

        response_data = json.loads(response.data.decode())
        assert response_data.pop('success') == True

        response = client.get(stage_url)
        response_data = json.loads(response.data.decode())
        assert response_data.pop('success') == True


    def test_update(self, client, stage, agent_token):
        """ Ensure agents can update """
        stage_url = stage_url_for(stage)
        response = client.put(
            stage_url,
            headers={'x_dockci_api_key': agent_token},
            data={'success': 'false'},
        )

        assert response.status_code == 200

        response_data = json.loads(response.data.decode())
        assert response_data.pop('success') == False

        response = client.get(stage_url)
        response_data = json.loads(response.data.decode())
        assert response_data.pop('success') == False
