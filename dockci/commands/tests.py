""" Flask-Script commands for running unit/style/static tests """
import os

import docker

from dockci.server import MANAGER
from dockci.util import bin_root, project_root


def call_seq(*commands):
    """ Call commands in sequence, returning on first failure """
    for cmd in commands:
        result = cmd()
        if result is not None and result != 0:
            return result

    return 0


@MANAGER.command
def unittest():
    """ Run unit tests """
    import pytest

    tests_dir = project_root().join('tests')
    return pytest.main(['--doctest-modules',
                        '--subunit',
                        '-vvrxs',
                        tests_dir.strpath,
                        ])


@MANAGER.command
def dbtest():
    """ Only run unit tests that require the database """
    import pytest

    from dockci.server import get_db_uri

    tests_dir = project_root().join('tests', 'db')

    for pyc_file in tests_dir.visit(fil='*.pyc'):
        pyc_file.remove()

    if get_db_uri() is None:
        client = docker.Client(**docker.utils.kwargs_from_env(
            assert_hostname=False,
        ))

        try:
            client.inspect_container('dockci_web_1')
        except docker.errors.NotFound:
            pass
        else:
            print("Running in dockci_web_1 container")
            os.execvp('docker', [
                'docker', 'exec', '-it', 'dockci_web_1',
                '/code/entrypoint.sh', 'dbtest',
            ])

    return pytest.main(['--doctest-modules',
                        '--subunit',
                        '-vvrxs',
                        tests_dir.strpath,
                        ])


@MANAGER.command
def doctest():
    """ Run doc tests """
    import pytest

    tests_dir = project_root().join('dockci')
    return pytest.main(['--doctest-modules',
                        # '--subunit',
                        '-vvrxs',
                        tests_dir.strpath,
                        ])


@MANAGER.command
def pep8():
    """ Style tests with PEP8 """
    from pep8 import StyleGuide

    code_dir = project_root().join('dockci')
    pep8style = StyleGuide(parse_argv=False)

    report = pep8style.check_files((code_dir.strpath,))

    if report.total_errors:
        return 1


@MANAGER.command
def pylint():
    """ Style tests with pylint """
    root_path = project_root()
    code_dir = root_path.join('dockci')
    rc_file = root_path.join('pylint.conf')

    pylint_path = bin_root().join('pylint').strpath
    os.execvp(pylint_path, [
        pylint_path,
        '--rcfile', rc_file.strpath,
        code_dir.strpath,
    ])


def pylint_forked():
    """ Fork, and execute the pylint command """
    pid = os.fork()
    if not pid:
        pylint()
    else:
        _, returncode = os.waitpid(pid, 0)

        # Flask-Script doesn't handle exiting 1024 properly
        return 0 if returncode == 0 else 1


@MANAGER.command
def styletest():
    """ Run style tests """
    return call_seq(pep8, pylint_forked)


@MANAGER.command
def ci():  # pylint:disable=invalid-name
    """ Run all tests """
    return call_seq(styletest, unittest, doctest)
