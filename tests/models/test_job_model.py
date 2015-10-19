import pytest

from dockci.models.job import Job, JobResult
from dockci.models.project import Project

class TestChangedResult(object):
    """ Test ``Job.changed_result`` """
    @pytest.mark.parametrize('prev_result,new_result,changed', [
        (JobResult.success, JobResult.success, False),
        (JobResult.success, JobResult.fail, True),
        (JobResult.success, JobResult.broken, True),
        (JobResult.fail, JobResult.broken, True),
        (JobResult.success, None, None),
    ])
    def test_ancestor_complete(self, mocker, prev_result, new_result, changed):
        """ Test when ancestor job has a result """
        job_current = Job()
        job_ancestor = Job()

        mocker.patch.object(job_current, 'ancestor_job', new=job_ancestor)
        mocker.patch.object(job_current, 'result', new=new_result)
        mocker.patch.object(job_ancestor, 'result', new=prev_result)

        assert job_current.changed_result == changed
