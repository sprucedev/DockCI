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
