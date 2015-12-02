class RepoFsMixin(object):
    @property
    def display_repo(self):
        return self.repo_fs.format(
            token_key='****',
        )

    @property
    def command_repo(self):
        try:
            token_key = self.external_auth_token.key
        except AttributeError:
            token_key = ''

        return self.repo_fs.format(
            token_key=token_key,
        )

    @property
    def repo_fs(self):
        raise NotImplementedError("Must override repo_fs property")

