from dockci.models.job_meta.stages import CommandJobStage


class MockProc(object):
    """ Mocked return object for Popen """
    returncode = 0
    def wait(self):
        """ Don't wait ;) """
        pass


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
