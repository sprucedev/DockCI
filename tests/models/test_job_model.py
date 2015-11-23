import re

from unittest.mock import PropertyMock

import pytest

from dockci.models.auth import AuthenticatedRegistry
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


class TestStateBools(object):
    """ Test ``Job.is_good_state`` and ``Job.is_bad_state`` """
    @pytest.mark.parametrize('result,exp', [
        (JobResult.success, True),
        (JobResult.fail, False),
    ])
    def test_good_state_result(self, result, exp):
        """ Test ``Job.is_good_state`` from job result """
        job = Job(result=result)
        assert job.is_good_state == exp

    @pytest.mark.parametrize('result,code,exp', [
        (JobResult.fail, 0, False),
        (None, 1, False),
        (None, 0, True),
    ])
    def test_good_state_exit_code(self, result, code, exp):
        """ Test ``Job.is_good_state`` from exit code """
        job = Job(result=result, exit_code=code)
        assert job.is_good_state == exp

    @pytest.mark.parametrize('result,exp', [
        (JobResult.success, False),
        (JobResult.fail, True),
        (JobResult.broken, True),
    ])
    def test_bad_state(self, result, exp):
        """ Test ``Job.is_bad_state`` """
        job = Job(result=result)
        assert job.is_bad_state == exp


class TestPushable(object):
    """ Test the various job push properties """
    @pytest.mark.parametrize('tag,reg,exp', [
        (None, None, False),
        ('abc', None, False),
        (None, AuthenticatedRegistry(), False),
        ('abc', AuthenticatedRegistry(), True),
    ])
    def test_tag_push_candidate(self, tag, reg, exp):
        """ Test ``Job.tag_push_candidate`` """
        project = Project(target_registry=reg)
        job = Job(project=project, tag=tag)

        assert job.tag_push_candidate == exp

    @pytest.mark.parametrize('branch,pattern,reg,exp', [
        (None, None, None, False),
        ('abc', None, None, False),
        (None, None, AuthenticatedRegistry(), False),
        ('abc', None, AuthenticatedRegistry(), False),
        (None, re.compile('abc'), None, False),
        ('abc', re.compile('abc'), None, False),
        (None, re.compile('abc'), AuthenticatedRegistry(), False),
        ('abc', re.compile('abc'), AuthenticatedRegistry(), True),
        ('abc', re.compile('nomatch'), AuthenticatedRegistry(), False),
        ('abc', re.compile('(a|b)bc'), AuthenticatedRegistry(), True),
        ('acd', re.compile('(a|b)cd'), AuthenticatedRegistry(), True),
        ('bcd', re.compile('(a|b)cd'), AuthenticatedRegistry(), True),
        ('abcd', re.compile('bcd'), AuthenticatedRegistry(), False),
    ])
    def test_branch_push_candidate(self, branch, pattern, reg, exp):
        """ Test ``Job.branch_push_candidate`` """
        project = Project(branch_pattern=pattern, target_registry=reg)
        job = Job(project=project, git_branch=branch)

        assert job.branch_push_candidate == exp

    @pytest.mark.parametrize('tag_pc,branch_pc,good_state,exp', [
        (False, False, False, False),
        (True, False, True, True),
        (False, True, True, True),
        (True, False, False, False),
        (False, True, False, False),
        (True, True, True, True),
    ])
    def test_pushable(self, mocker, tag_pc, branch_pc, good_state, exp):
        """ Test ``Job.pushable`` """
        mocker.patch('dockci.models.job.Job.is_good_state',
                     new_callable=PropertyMock(return_value=good_state))
        mocker.patch('dockci.models.job.Job.tag_push_candidate',
                     new_callable=PropertyMock(return_value=tag_pc))
        mocker.patch('dockci.models.job.Job.branch_push_candidate',
                     new_callable=PropertyMock(return_value=branch_pc))
        job = Job()

        assert job.pushable == exp


class TestJobBase(object):
    """ Base for name, semver tests """
    def setup_method(self, method):
        self.registry = AuthenticatedRegistry()
        self.project = Project(
            target_registry=self.registry,
            branch_pattern=re.compile('master'),
        )
        self.job = Job(project=self.project)


class TestNames(TestJobBase):
    """ Test some of the job naming methods """
    def test_docker_tag_branch(self):
        """ Test ``Job.docker_tag`` when ``git_branch`` is set """
        self.job.git_branch = 'master'
        assert self.job.docker_tag == 'latest-master'

    def test_docker_tag_tag(self):
        """ Test ``Job.docker_tag`` when ``tag`` is set """
        self.job.tag = 'test'
        assert self.job.docker_tag == 'test'

    def test_docker_tag_none(self):
        """ Test ``Job.docker_tag`` when nothing is set """
        assert self.job.docker_tag == None

    def test_docker_tag_branch_tag(self):
        """ Test ``Job.docker_tag`` when ``git_branch``, and ``tag`` is set """
        self.job.tag = 'test'
        self.job.git_branch = 'master'
        assert self.job.docker_tag == 'test'


class TestSemver(TestJobBase):
    """ Test semver related functionality for the ``Job`` model """
    @pytest.mark.parametrize('tag,exp', [
        ('0.0.0', dict(major=0, minor=0, patch=0)),
        ('1.2.3', dict(major=1, minor=2, patch=3)),
        ('7.11.2', dict(major=7, minor=11, patch=2)),
        ('v7.11.2', dict(major=7, minor=11, patch=2)),
        ('7.11.2-abc', dict(major=7, minor=11, patch=2, prerelease='abc')),
        ('7.11.2-abc+d', dict(
            major=7, minor=11, patch=2, prerelease='abc', build='d',
        )),
        ('v7.11.2-abc+d', dict(
            major=7, minor=11, patch=2, prerelease='abc', build='d',
        )),
    ])
    def test_tag_semver(self, tag, exp):
        """ Test semver-like parsings for ``Job.tag_semver`` """
        self.job.tag = tag

        actual = self.job.tag_semver
        for key, value in exp.items():
            assert actual.pop(key) == value

        for key, value in actual.items():
            assert value is None

    @pytest.mark.parametrize('tag', [
        'av1.1.1', 'a1.1.1', '1.1', '1', 'a.1.1', '1.a.1', '1.1.a', '1.1.1-½',
        '1.1.1-1+½', None,
    ])
    def test_tag_semver_invalid(self, tag):
        """ Test non-semver-like parsings for ``Job.tag_semver`` """
        self.job.tag = tag
        assert self.job.tag_semver == None

    @pytest.mark.parametrize('tag,exp_no_v', [
        ('0.0.0-ab+cd', '0.0.0-ab+cd'),
        ('v0.0.0-ab+cd', '0.0.0-ab+cd'),
    ])
    def test_str(self, tag, exp_no_v):
        """
        Test ``tag_semver_str`` and ``tag_semver_str_v`` with semver-like tags
        """
        self.job.tag = tag
        assert self.job.tag_semver_str == exp_no_v
        assert self.job.tag_semver_str_v == 'v%s' % exp_no_v

    @pytest.mark.parametrize('tag', [
        'a.0.0-ab+cd', 'a0.0.0-ab+cd',
    ])
    def test_str_invalid(self, tag):
        """
        Test ``tag_semver_str`` and ``tag_semver_str_v`` with non-semver-like
        tags
        """
        self.job.tag = tag
        assert self.job.tag_semver_str is None
        assert self.job.tag_semver_str_v is None
