from unittest.mock import PropertyMock

import pytest

from dockci.models.job import Job, JobResult
from dockci.models.project import Project


CHANGED_RESULT_PARAMS = [
    (JobResult.success, JobResult.success, False),
    (JobResult.success, JobResult.fail, True),
    (JobResult.success, JobResult.broken, True),
    (JobResult.fail, JobResult.broken, True),
]


class TestChangedResult(object):
    """ Test ``Job.changed_result`` """
    @pytest.mark.parametrize(
        'prev_result,new_result,changed',
        CHANGED_RESULT_PARAMS + [(JobResult.success, None, None)]
    )
    def test_ancestor_complete(self,
                               mocker,
                               prev_result,
                               new_result,
                               changed):
        """ Test when ancestor job has a result """
        job_current = Job()
        job_ancestor = Job()

        mocker.patch.object(job_current, 'ancestor_job', new=job_ancestor)
        mocker.patch.object(job_current, 'result', new=new_result)
        mocker.patch.object(job_ancestor, 'result', new=prev_result)

        assert job_current.changed_result() == changed


    @pytest.mark.parametrize(
        'prev_result,new_result,changed',
        CHANGED_RESULT_PARAMS
    )
    def test_ancestor_incomplete(self,
                                 mocker,
                                 prev_result,
                                 new_result,
                                 changed):
        job_current = Job()
        job_ancestor_incomplete = Job()
        job_ancestor = Job()
        project = Project()

        mocker.patch.object(job_ancestor_incomplete, 'result', new=None)
        mocker.patch.object(
            job_current, 'ancestor_job', new=job_ancestor_incomplete,
        )

        mocker.patch.object(job_current, 'project', new=project)
        mocker.patch.object(job_current, 'commit', new='fake commit')
        mocker.patch.object(job_current, 'result', new=new_result)
        mocker.patch.object(job_ancestor, 'result', new=prev_result)

        ancestor_mock = mocker.patch.object(
            project, 'latest_job_ancestor', return_value=job_ancestor,
        )

        assert job_current.changed_result(workdir='fake workdir') == changed

        ancestor_mock.assert_called_once_with(
            'fake workdir', 'fake commit', complete=True,
        )


    def test_ancestor_incomplete_no_workdir(self, mocker):
        job_current = Job()
        job_ancestor_incomplete = Job()

        mocker.patch.object(job_ancestor_incomplete, 'result', new=None)
        mocker.patch.object(
            job_current, 'ancestor_job', new=job_ancestor_incomplete,
        )

        mocker.patch.object(job_current, 'result', new=JobResult.success)

        assert job_current.changed_result() == True


    @pytest.mark.parametrize('new_result,changed', [
        (JobResult.success, True),
        (JobResult.fail, True),
        (JobResult.broken, True),
        (None, None),
    ])
    def test_no_ancestors(self,
                          mocker,
                          new_result,
                          changed):
        """ Test when ancestor job has a result """
        job_current = Job()

        mocker.patch.object(job_current, 'ancestor_job', new=None)
        mocker.patch.object(job_current, 'result', new=new_result)

        assert job_current.changed_result() == changed


class TestStateDataFor(object):
    """ Test ``Job.state_data_for`` """
    @pytest.mark.parametrize(
        'model_state,in_service,in_state,in_msg,exp_state,exp_msg', [
        (
            None, 'github', 'running', None, 'pending',
            'The DockCI job is in progress',
        ),
        (
            None, 'github', 'broken', None, 'error',
            'The DockCI job failed to complete due to an error',
        ),
        (
            'running', 'github', None, None, 'pending',
            'The DockCI job is in progress',
        ),
        (
            None, 'github', 'running', 'is testing things', 'pending',
            'The DockCI job is testing things',
        ),
        (
            'running', 'github', None, 'is testing things', 'pending',
            'The DockCI job is testing things',
        ),
        (
            None, 'gitlab', 'fail', None, 'failed',
            'The DockCI job completed with failing tests',
        ),
        (
            'fail', 'gitlab', None, None, 'failed',
            'The DockCI job completed with failing tests',
        ),
    ])
    def test_basic_sets(self,
                        mocker,
                        model_state,
                        in_service,
                        in_state,
                        in_msg,
                        exp_state,
                        exp_msg,
                        ):
        """ Test some basic input/output combinations """
        job = Job()
        mocker.patch('dockci.models.job.Job.state', new_callable=PropertyMock(return_value=model_state))
        out_state, out_msg = job.state_data_for(in_service, in_state, in_msg)

        assert out_state == exp_state
        assert out_msg == exp_msg
