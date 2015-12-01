class RepoFsMixin(object):
    @property
    def display_repo(self):
        return self.repo_fs.format(
            token_key='****',
        )

    @property
    def command_repo(self):
        return self.repo_fs.format(
            token_key=self.project.external_auth_token.key,
        )

    @property
    def repo_fs(self):
        raise NotImplementedError("Must override repo_fs property")

