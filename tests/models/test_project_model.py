from collections import namedtuple

import pytest

from dockci.models.auth import OAuthToken
from dockci.models.project import Project


class TestRepoFs(object):
    """ Test utilization of the ``Project.repo_fs`` field """
    @pytest.mark.parametrize(
        'repo,github_repo_id,gitlab_repo_id,exp_display,exp_command',
        [
            (
                'http://example.com/should/be/replaced.git',
                None, 'sprucedev/DockCI',
                'http://oauth2:****@localhost:8000/sprucedev/DockCI.git',
                'http://oauth2:authkey@localhost:8000/sprucedev/DockCI.git',
            ),
            (
                'http://example.com/should/be/replaced.git',
                'sprucedev/DockCI', None,
                'https://oauth2:****@github.com/sprucedev/DockCI.git',
                'https://oauth2:authkey@github.com/sprucedev/DockCI.git',
            ),
            (
                'http://example.com/should/clone/this.git',
                None, None,
                'http://example.com/should/clone/this.git',
                'http://example.com/should/clone/this.git',
            ),
        ]
    )
    def test_fs_outputs(self,
                        mocker,
                        repo,
                        github_repo_id,
                        gitlab_repo_id,
                        exp_display,
                        exp_command,
                        ):
        """
        Ensure that github, gitlab, manual project types are represented
        correctly with ``display_repo`` and ``command_repo``
        """
        mocker.patch(
            'dockci.models.project.CONFIG',
            namedtuple('Config', ['gitlab_base_url'])(
                'http://localhost:8000'
            ),
        )

        project = Project(
            repo=repo,
            github_repo_id=github_repo_id,
            gitlab_repo_id=gitlab_repo_id,
        )

        service = None
        if github_repo_id is not None:
            service = 'github'
        elif gitlab_repo_id is not None:
            service = 'gitlab'

        if service is not None:
            project.external_auth_token = OAuthToken(
                key='authkey',
                secret='authsecret',
                service=service,
            )

        assert project.display_repo == exp_display
        assert project.command_repo == exp_command
