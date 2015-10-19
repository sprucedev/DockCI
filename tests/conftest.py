import subprocess

import pytest


@pytest.yield_fixture
def tmpgitdir(tmpdir):
    """ Get a new ``tmpdir``, make it the cwd, and set git config """
    with tmpdir.as_cwd():
        subprocess.check_call(['git', 'init'])
        for name, val in (
            ('user.name', 'DockCI Test'),
            ('user.email', 'test@example.com'),
        ):
            subprocess.check_call(['git', 'config', name, val])

        yield tmpdir
