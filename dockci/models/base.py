""" Base model classes, mixins """
from dockci.models.auth import AuthenticatedRegistry


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


class ServiceBase(object):
    """ Service object for storing utility/provision information """

    def __init__(self,
                 name=None,
                 repo=None,
                 tag=None,
                 base_registry=None,
                 auth_registry=None,
                 ):

        if base_registry is not None and auth_registry is not None:
            assert auth_registry.base_name == base_registry, (
                "AuthenticatedRegistry.base_name doesn't match base_registry")

        self._name = name
        self._repo = repo
        self._tag = tag
        self._base_registry = base_registry
        self._auth_registry = auth_registry

    @classmethod
    def from_image(cls, image, name=None):
        """
        Given an image name such as ``quay.io/thatpanda/dockci:latest``,
        creates a ``ServiceBase`` object.

        For a registry host to be identified, it must have both a repo
        namespace, and a repo name (otherwise Docker hub with a namespace is
        assumed).

        Examples:

        >>> svc = ServiceBase.from_image('registry/dockci')
        >>> svc.base_registry
        'docker.io'

        >>> svc.repo
        'registry/dockci'


        >>> svc = ServiceBase.from_image('registry/spruce/dockci')
        >>> svc.base_registry
        'registry'

        >>> svc.repo
        'spruce/dockci'

        >>> svc.tag
        'latest'

        >>> svc = ServiceBase.from_image('registry/spruce/dockci:other')
        >>> svc.tag
        'other'

        >>> svc = ServiceBase.from_image('dockci', 'DockCI App')
        >>> svc.base_registry
        'docker.io'

        >>> svc.repo
        'dockci'

        >>> svc.tag
        'latest'

        >>> svc.name
        'DockCI App'

        >>> svc = ServiceBase.from_image('registry:5000/spruce/dockci:other')
        >>> svc.base_registry
        'registry:5000'

        >>> svc.tag
        'other'
        """
        path_parts = image.split('/', 2)
        if len(path_parts) != 3:
            base_registry = None
            repo_etc = image
        else:
            base_registry = path_parts[0]
            repo_etc = '/'.join(path_parts[1:])

        tag_parts = repo_etc.rsplit(':', 1)
        tag = None if len(tag_parts) != 2 else tag_parts[1]

        repo = tag_parts[0]

        return cls(base_registry=base_registry, repo=repo, tag=tag, name=name)

    @property
    def name_raw(self):
        """ Raw name given to this service """
        return self._name

    @property
    def name(self):
        """ Human readable name for this service. Falls back to the repo """
        if self.has_name:
            return self.name_raw
        else:
            return self.repo

    @property
    def has_name(self):
        """ Whether or not a name was explicitly given """
        return self.name_raw is not None

    @property
    def repo_raw(self):
        """ Raw repository given to this service """
        return self._repo

    @property
    def repo(self):
        """ Repository for this service """
        return self.repo_raw

    @property
    def has_repo(self):
        """ Whether or not a repository was explicitly given """
        return self.repo_raw is not None

    @property
    def tag_raw(self):
        """ Raw tag given to this service """
        return self._tag

    @property
    def tag(self):
        """ Tag for this service. Defaults to ``latest`` """
        if self.has_tag:
            return self.tag_raw
        else:
            return 'latest'

    @property
    def has_tag(self):
        """ Whether or not a tag was explicitly given """
        return self.tag_raw is not None

    @property
    def base_registry_raw(self):
        """ Raw registry base name given to this service """
        return self._base_registry

    @property
    def base_registry(self):
        """
        A registry base name. This is the host name of the registry. Falls back
        to the authenticated registry ``base_name``, or defaults to
        ``docker.io`` if that's not given either
        """
        if self.has_base_registry:
            return self.base_registry_raw
        elif self.has_auth_registry:
            return self.auth_registry.base_name
        else:
            return 'docker.io'

    @property
    def has_base_registry(self):
        """ Whether or not a registry base name was explicitly given """
        return self.base_registry_raw is not None

    @property
    def auth_registry_raw(self):
        """ Raw authenticated registry given to this service """
        return self._auth_registry

    @property
    def auth_registry(self):
        """
        ``AuthenticatedRegistry`` required for this service. If not given,
        tries to lookup using the registry base name
        """
        if self.has_auth_registry:
            return self.auth_registry_raw
        else:
            query = AuthenticatedRegistry.query.filter_by(
                base_name=self.base_registry,
            )
            if query.count() > 0:
                return query.first()

    @property
    def has_auth_registry(self):
        """ Whether or not an authenticated registry was explicitly given """
        return self.auth_registry_raw is not None

    @property
    def display(self):
        """ Human readable display, hiding default elements """
        return self._display(full=False)

    @property
    def display_full(self):
        """ Human readable display, including defaults """
        return self._display(full=True)

    def _display(self, full):
        """ Used for the display properties """
        string = ""

        if full or self.has_name:
            string = "%s - " % self.name
        if full or self.has_base_registry:
            string += '%s/' % self.base_registry
        if full or self.has_repo:
            string += self.repo
        if full or self.has_tag:
            string += ":%s" % self.tag

        if string == '':
            return "No details"

        return string

    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.display)
