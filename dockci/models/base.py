""" Base model classes, mixins """


class RepoFsMixin(object):
    """ Mixin to add ``display_repo`` and ``command_repo`` properties """

    @property
    def display_repo(self):
        """ Repo, redacted for display """
        return self.repo_fs.format(
            token_key='****',
        )

    @property
    def command_repo(self):
        """ Repo, with credentials substituted in """
        try:
            token_key = self.external_auth_token.key
        except AttributeError:
            token_key = ''

        return self.repo_fs.format(
            token_key=token_key,
        )

    @property
    def repo_fs(self):
        """
        Format string for the repo. The ``token_key`` attribute may be
        substituted with the OAuth token
        """
        raise NotImplementedError("Must override repo_fs property")

    @property
    def external_auth_token(self):
        """ OAuthToken for the object to use in ``command_repo`` """
        raise NotImplementedError("Must override external_auth_token property")
