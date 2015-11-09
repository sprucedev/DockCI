from collections import namedtuple

import pytest

import dockci.server

from dockci.server import CONFIG
from dockci.models.job_meta.stages import CommandJobStage
from dockci.models.job_meta.stages_prepare import WorkdirStage


class MockProc(object):
    """ Mocked return object for Popen """
    returncode = 0
    def wait(self):
        """ Don't wait ;) """
        pass

class MockDbSession(object):
    """ Mocked add/commit functions """
    def add(self, obj):
        """ Don't add """
        pass
    def commit(self):
        """ Don't commit """
        pass

class MockJob(object):
    """ Mock Job object with a MockDbSession """
    db_session = MockDbSession()

class MockProject(object):
    """ Mock Project object with ``is_type`` matcher """
    def __init__(self, service_type):
        self.service_type = service_type

    def is_type(self, service):
        return self.service_type == service


class TestCommandJobStage(object):
    """ Test some of ``CommandJobStage`` """
    def test_display_output(self, mocker, tmpdir):
        """
        Ensure that commands are not displayed when display option is present
        """
        workdir = tmpdir.join('work')
        workdir.ensure_dir()

        stage = CommandJobStage(None, workdir=workdir, cmd_args=[
            dict(display=('git', 'clone', 'ab@****:ef.com'),
                 command=('git', 'clone', 'ab@secret:ef.com')),
        ])

        popen_mock = mocker.patch('subprocess.Popen', return_value=MockProc())

        with tmpdir.join('output.log').open('wb') as handle:
            stage.runnable(handle)
            popen_mock.assert_called()
            args, _ = popen_mock.call_args
            assert args == (('git', 'clone', 'ab@secret:ef.com'),)

        with tmpdir.join('output.log').open('rb') as handle:
            assert b'ab@****:ef.com' in handle.read()


class TestWorkdirStage(object):
    """ Test some of ``WorkdirStage`` """
    @pytest.mark.parametrize(
        'repo,service,repo_id_attr,exp_display,exp_command',
        [
            (
                'http://example.com/should/be/replaced.git',
                'gitlab', 'gitlab_repo_id',
                'http://oauth2:****@localhost:8000/sprucedev/DockCI.git',
                'http://oauth2:authkey@localhost:8000/sprucedev/DockCI.git',
            ),
            (
                'http://example.com/should/be/replaced.git',
                'github', 'github_repo_id',
                'https://oauth2:****@github.com/sprucedev/DockCI.git',
                'https://oauth2:authkey@github.com/sprucedev/DockCI.git',
            ),
            (
                'http://example.com/should/clone/this.git',
                'manual', None,
                'http://example.com/should/clone/this.git',
                'http://example.com/should/clone/this.git',
            ),
        ]
    )
    def test_external_override_clone(self,
                                     mocker,
                                     tmpdir,
                                     repo,
                                     service,
                                     repo_id_attr,
                                     exp_display,
                                     exp_command,
                                     ):
        """
        Ensure that github, gitlab, manual project types override command args
        as expected
        """
        workdir = tmpdir.join('work')
        workdir.ensure_dir()

        mocker.patch(
            'dockci.models.job_meta.stages_prepare.CONFIG',
            namedtuple('Config', ['gitlab_base_url'])(
                'http://localhost:8000'
            ),
        )

        job = MockJob()
        job.repo = repo
        job.commit = 'abcdef'
        job.project = MockProject(service)
        if repo_id_attr is not None:
            setattr(job.project, repo_id_attr, 'sprucedev/DockCI')
            job.project.external_auth_token = namedtuple(
                'AuthToken', ['key', 'secret', 'service']
            )(
                'authkey', 'authsecret', service
            )

        stage = WorkdirStage(job, workdir)

        assert stage.cmd_args[0] == {
            'display': ['git', 'clone', exp_display, workdir.strpath],
            'command': ['git', 'clone', exp_command, workdir.strpath],
        }
