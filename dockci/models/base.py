""" Base model classes, mixins """
import re

from collections import defaultdict

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


SLUG_REPLACE_RE = re.compile(r'[^a-zA-Z0-9_]')


# TODO all these disabled pylint things should be reviewed later on. How would
#      we better split this up?
# pylint:disable=too-many-public-methods,too-many-instance-attributes
class ServiceBase(object):
    """
    Service object for storing utility/provision information

    Examples:

    Most examples can be seen in their relevant property docs.

    >>> svc = ServiceBase(meta={'config': 'fake'})
    >>> svc.meta
    {'config': 'fake'}
    """

    # pylint:disable=too-many-arguments
    def __init__(self,
                 name=None,
                 repo=None,
                 tag=None,
                 project=None,
                 job=None,
                 base_registry=None,
                 auth_registry=None,
                 meta=None,
                 use_db=True,
                 ):

        if meta is None:
            meta = {}

        self.meta = meta

        self.use_db = use_db

        self._auth_registry_dynamic = None
        self._project_dynamic = None
        self._job_dynamic = None

        self._name = None
        self._repo = None
        self._tag = None
        self._base_registry = None
        self._auth_registry = None
        self._project = None
        self._job = None

        self.name = name
        self.repo = repo
        self.tag = tag
        self.base_registry = base_registry
        self.auth_registry = auth_registry
        self.project = project
        self.job = job

    @classmethod
    def from_image(cls, image, name=None, meta=None, use_db=True):
        """
        Given an image name such as ``quay.io/thatpanda/dockci:latest``,
        creates a ``ServiceBase`` object.

        For a registry host to be identified, it must have both a repo
        namespace, and a repo name (otherwise Docker hub with a namespace is
        assumed).

        Examples:

        >>> svc = ServiceBase.from_image('registry/dockci', use_db=False)

        >>> svc.repo
        'registry/dockci'


        >>> svc = ServiceBase.from_image('registry/spruce/dockci', \
                                         use_db=False)
        >>> svc.base_registry
        'registry'

        >>> svc.repo
        'spruce/dockci'

        >>> svc.tag
        'latest'

        >>> svc = ServiceBase.from_image('registry/spruce/dockci:other', \
                                         use_db=False)
        >>> svc.tag
        'other'

        >>> svc = ServiceBase.from_image('dockci', 'DockCI App', use_db=False)

        >>> svc.repo
        'dockci'

        >>> svc.tag
        'latest'

        >>> svc.name
        'DockCI App'

        >>> svc = ServiceBase.from_image('registry:5000/spruce/dockci:other', \
                                         use_db=False)

        >>> svc.base_registry
        'registry:5000'

        >>> svc.tag
        'other'

        >>> svc = ServiceBase.from_image('dockci', \
                                         meta={'config': 'fake'}, \
                                         use_db=False)
        >>> svc.meta
        {'config': 'fake'}
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

        return cls(base_registry=base_registry,
                   repo=repo,
                   tag=tag,
                   name=name,
                   meta=meta,
                   use_db=use_db,
                   )

    @property
    def name_raw(self):
        """ Raw name given to this service """
        return self._name

    @property
    def name(self):
        """
        Human readable name for this service. Falls back to the repo

        Examples:

        >>> svc = ServiceBase.from_image('quay.io/spruce/dockci', use_db=False)
        >>> svc.name
        'spruce/dockci'

        >>> svc.has_name
        False

        >>> svc.name = 'Test Name'
        >>> svc.name
        'Test Name'

        >>> svc.has_name
        True

        >>> svc.display
        'Test Name - quay.io/spruce/dockci'
        """
        if self.has_name:
            return self.name_raw
        else:
            return self.repo

    @name.setter
    def name(self, value):
        """ Set the name """
        self._name = value

    @property
    def has_name(self):
        """ Whether or not a name was reliably given """
        return self.name_raw is not None

    @property
    def repo_raw(self):
        """ Raw repository given to this service """
        return self._repo

    @property
    def repo(self):
        """
        Repository for this service

        Examples:

        >>> svc = ServiceBase(base_registry='quay.io', \
                              tag='special', \
                              use_db=False)
        >>> svc.has_repo
        False

        >>> svc.repo = 'spruce/dockci'
        >>> svc.repo
        'spruce/dockci'

        >>> svc.has_repo
        True

        >>> svc.display
        'quay.io/spruce/dockci:special'
        """
        return self.repo_raw

    @repo.setter
    def repo(self, value):
        """ Set the repo """
        self._repo = value

    @property
    def has_repo(self):
        """ Whether or not a repository was reliably given """
        return self.repo_raw is not None

    @property
    def app_name(self):
        """
        Application name of the service. This is the last part of the repo,
        without the namespace path

        Examples:

        >>> svc = ServiceBase.from_image('quay.io/spruce/dockci', use_db=False)

        >>> svc.app_name
        'dockci'

        >>> svc = ServiceBase.from_image('quay.io/my/app:test', use_db=False)

        >>> svc.app_name
        'app'
        """
        if self.has_repo:
            return self.repo.rsplit('/', 1)[-1]

    @property
    def tag_raw(self):
        """ Raw tag given to this service """
        return self._tag

    @property
    def tag(self):
        """
        Tag for this service. Defaults to ``latest``

        Examples:

        >>> svc = ServiceBase.from_image('quay.io/spruce/dockci', use_db=False)

        >>> svc.tag
        'latest'

        >>> svc.has_tag
        False

        >>> svc.tag = 'special'
        >>> svc.tag
        'special'

        >>> svc.has_tag
        True

        >>> svc.display
        'quay.io/spruce/dockci:special'
        """
        if self.has_tag:
            return self.tag_raw
        else:
            return 'latest'

    @tag.setter
    def tag(self, value):
        """ Set the tag """
        self._tag = value

    @property
    def has_tag(self):
        """ Whether or not a tag was reliably given """
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

        Examples:

        >>> svc = ServiceBase.from_image('spruce/dockci', use_db=False)

        >>> svc.base_registry = 'docker.io'

        >>> svc.base_registry = 'quay.io'
        >>> svc.base_registry
        'quay.io'

        >>> svc.has_base_registry
        True

        >>> svc.display
        'quay.io/spruce/dockci'
        """
        return self._get_base_registry()

    @base_registry.setter
    def base_registry(self, value):
        """ Set the base_registry """
        if (
            value is not None and
            self.has_auth_registry and
            self.auth_registry.base_name != value
        ):
            raise ValueError(
                ("Existing auth_registry value '%s' doesn't match new "
                 "base_registry value") % self.auth_registry.base_name
            )

        self._base_registry = value

    def _get_base_registry(self, lookup_allow=None):
        """ Dynamically get the base_registry from other values """
        if lookup_allow is None:
            lookup_allow = defaultdict(lambda: True)

        if self.has_base_registry:
            return self.base_registry_raw

        elif lookup_allow['auth_registry']:
            lookup_allow['base_registry'] = False
            auth_registry = self._get_auth_registry(lookup_allow)
            if auth_registry is not None:
                return auth_registry.base_name

        return 'docker.io'

    @property
    def has_base_registry(self):
        """ Whether or not a registry base name was reliably given """
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
        return self._get_auth_registry()

    @auth_registry.setter
    def auth_registry(self, value):
        """ Set the auth_registry """
        if (
            value is not None and
            self.has_base_registry and
            self.base_registry != value
        ):
            raise ValueError(
                ("Existing base_registry value '%s' doesn't match new "
                 "auth_registry value") % self.base_registry
            )
        if value is not None and self.has_project:
            project = self.project
            if (
                self.project.target_registry is not None and
                self.project.target_registry != value
            ):
                raise ValueError(
                    ("Existing project target_registry value '%s' doesn't "
                     "match new auth_registry value") % project.target_registry
                )

        self._auth_registry = value

    def _get_auth_registry(self, lookup_allow=None):
        """ Dynamically get the auth_registry from other values """
        if lookup_allow is None:
            lookup_allow = defaultdict(lambda: True)

        if False:  # help pylint understand our return value
            return AuthenticatedRegistry()

        if self.auth_registry_raw is not None:
            return self.auth_registry_raw

        lookup_allow['auth_registry'] = False

        if (
            self.use_db and
            lookup_allow['base_registry'] and
            self.has_base_registry and
            self._auth_registry_dynamic is None
        ):
            self._auth_registry_dynamic = \
                AuthenticatedRegistry.query.filter_by(
                    base_name=self._get_base_registry(lookup_allow),
                ).first()

        if (
            lookup_allow['project'] and
            self._auth_registry_dynamic is None
        ):
            project = self._get_project()
            if project is not None:
                self._auth_registry_dynamic = project.target_registry

        if self._auth_registry_dynamic is None and self.use_db:
            self._auth_registry_dynamic = \
                AuthenticatedRegistry.query.filter_by(
                    base_name='docker.io',
                ).first()

        return self._auth_registry_dynamic

    @property
    def has_auth_registry(self):
        """ Whether or not an authenticated registry was reliably given """
        return self._has_auth_registry()

    def _has_auth_registry(self, lookup_allow=None):
        """
        Figure out if we have a reliable ``auth_registry``source from other
        values
        """
        if self.auth_registry_raw is not None:
            return True

        if lookup_allow is None:
            lookup_allow = defaultdict(lambda: True)

        lookup_allow['has_auth_registry'] = False

        if lookup_allow['project']:
            project = self.project
            return project is not None and project.target_registry is not None

        return False

    @property
    def project_raw(self):
        """ Raw project given to this service """
        return self._project

    @property
    def project(self):
        """
        ``Project`` associated with this service. If not given, tries to lookup
        by matching the repository with the project slug. When a lookup occurs,
        and a registry is given to the service, the ``Project`` must have the
        same authenticated registry set
        """
        return self._get_project()

    @project.setter
    def project(self, value):
        """ Set the project """
        lookup_allow = defaultdict(lambda: True)
        lookup_allow['project'] = False

        if value is not None and value.target_registry is not None:
            if (
                self.has_base_registry and
                self.base_registry != value.target_registry.base_name
            ):
                raise ValueError(
                    ("Existing base_registry value '%s' doesn't match new "
                     "project target_registry value") % self.base_registry
                )

            if (
                self._has_auth_registry(lookup_allow) and
                self.auth_registry != value.target_registry
            ):
                raise ValueError(
                    ("Existing auth_registry value '%s' doesn't match new "
                     "project target_registry value") % self.auth_registry
                )


        if (
            value is not None and
            self.has_job and
            value != self.job.project
        ):
            raise ValueError(
                ("Existing job project value '%s' doesn't match new "
                 "project value") % self.job.project
            )

        self._project = value

    def _get_project(self, lookup_allow=None):
        """ Dynamically get the project from other values """
        from dockci.models.project import Project

        if False:  # help pylint understand our return value
            return Project()

        if lookup_allow is None:
            lookup_allow = defaultdict(lambda: True)

        if self.has_project:
            return self.project_raw

        lookup_allow['project'] = False

        if self._project_dynamic is None and self.use_db:
            if self.has_base_registry or self.auth_registry_raw is not None:
                return None

            self._project_dynamic = Project.query.filter_by(
                slug=self.repo,
            ).first()

        return self._project_dynamic

    @property
    def has_project(self):
        """ Whether or not a project was reliably given """
        return self.project_raw is not None

    @property
    def job_raw(self):
        """ Raw job given to this service """
        return self._job

    @property
    def job(self):
        """
        ``Job`` associated with this service. If not given, tries to lookup
        by using the service project, and matching the tag

        >>> svc = ServiceBase(repo='postgres')
        >>> job = 'Fake Job'
        >>> svc.job = job
        >>> svc.job
        'Fake Job'
        """
        return self._get_job()

    @job.setter
    def job(self, value):
        """ Set the job """
        if (
            value is not None and
            self.has_project and
            value.project != self.project
        ):
            raise ValueError(
                ("Existing project value '%s' doesn't match new "
                 "job project value") % self.project
            )
        self._job = value

    def _get_job(self, lookup_allow=None):
        """ Dynamically get the job from other values """
        if lookup_allow is None:
            lookup_allow = defaultdict(lambda: True)

        if self.has_job:
            return self.job_raw

        lookup_allow['job'] = False

        if lookup_allow['project'] and self._job_dynamic is None:
            project = self._get_project(lookup_allow)
            if project is not None:
                self._job_dynamic = project.latest_job(
                    passed=True, versioned=True, tag=self.tag_raw,
                )

        return self._job_dynamic

    @property
    def has_job(self):
        """ Whether or not a job was reliably given """
        return self.job_raw is not None

    @property
    def display(self):
        """ Human readable display, hiding default elements """
        return self._display(full=False)

    @property
    def display_full(self):
        """ Human readable display, including defaults """
        return self._display(full=True)

    @property
    def image(self):
        """
        Pullable image for Docker

        Examples:

        >>> svc = ServiceBase.from_image('quay.io/spruce/dockci', use_db=False)

        >>> svc.image
        'quay.io/spruce/dockci'

        >>> svc.tag = 'latest'
        >>> svc.image
        'quay.io/spruce/dockci:latest'

        >>> svc.name = 'Test Name'
        >>> svc.image
        'quay.io/spruce/dockci:latest'
        """
        return self._display(full=False, name=False)

    @property
    def repo_full(self):
        """
        Similar to the ``repo`` property, but includes the registry

        Examples:

        >>> svc = ServiceBase.from_image('quay.io/spruce/dockci', use_db=False)

        >>> svc.repo_full
        'quay.io/spruce/dockci'

        >>> svc.tag = 'latest'
        >>> svc.repo_full
        'quay.io/spruce/dockci'

        >>> svc.name = 'Test Name'
        >>> svc.repo_full
        'quay.io/spruce/dockci'
        """
        return self._display(full=False, name=False, tag=False)

    @property
    def slug(self):
        """
        Get a slug for the service

        Examples:

        >>> svc = ServiceBase.from_image('spruce/dockci', use_db=False)

        >>> svc.slug
        'spruce_dockci'

        >>> svc.tag = 'latest'
        >>> svc.slug
        'spruce_dockci_latest'

        >>> svc.base_registry = 'registry:5000'
        >>> svc.slug
        'registry_5000_spruce_dockci_latest'
        """
        return SLUG_REPLACE_RE.sub("_", self.image)

    def _display(self, full, name=True, tag=True):
        """ Used for the display properties """
        string = ""

        if name and (full or self.has_name):
            string = "%s - " % self.name
        if full or self.has_base_registry or self.has_auth_registry:
            if self.has_auth_registry:
                string += '%s/' % self.auth_registry.base_name
            else:
                string += '%s/' % self.base_registry
        if full or self.has_repo:
            string += self.repo
        if tag and (full or self.has_tag):
            string += ":%s" % self.tag

        if string == '':
            return "No details"

        return string

    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.display)
