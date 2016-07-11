"""
Generic DockCI utils
"""
import hashlib
import hmac
import logging
import pickle
import re
import shlex
import socket
import ssl
import struct
import sys
import datetime

from base64 import b64encode
from functools import wraps
from ipaddress import ip_address
from urllib.parse import urlencode, urlparse, urlunparse

import docker.errors
import jwt
import py.error  # pylint:disable=import-error
import redis
import yaml_model

from flask import current_app, flash, request
from flask_principal import Permission, RoleNeed
from flask_restful import abort as rest_abort
from flask_security import current_user, login_required
from py.path import local  # pylint:disable=import-error
from yaml_model import ValidationError


AUTH_TOKEN_EXPIRY = 36000  # 10 hours


def request_fill(model_obj, fill_atts, accept_blank=(), data=None, save=True):
    """
    Fill given model attrs from a POST request (and ignore other requests).
    Will save only if the save flag is True
    """
    if data is None:
        data = request.form

    if request.method == 'POST':
        for att in fill_atts:
            if att in data and (data[att] != '' or att in accept_blank):
                setattr(model_obj, att, data[att])
            elif att not in data:  # For check boxes
                setattr(model_obj, att, None)

    if save:
        return model_flash(model_obj)

    return True


def model_flash(model_obj, save=True):
    """
    Save a model object, displaying appropriate flash messages
    """
    # TODO move the flash to views
    try:
        if save:
            if isinstance(model_obj, yaml_model.Model):
                model_obj.save()

            else:
                model_obj.validate()
                from dockci.server import DB
                DB.session.add(model_obj)
                DB.session.commit()

            flash(u"%s saved" % model_obj.__class__.__name__.title(),
                  'success')

        else:
            model_obj.validate()

        return True

    except ValidationError as ex:
        flash(ex.messages, 'danger')
        return False


def default_gateway():
    """
    Gets the IP address of the default gateway
    """
    with open('/proc/net/route') as handle:
        for line in handle:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue

            return ip_address(socket.inet_ntoa(
                struct.pack("<L", int(fields[2], 16))
            ))


def bytes_human_readable(num, suffix='B'):
    """
    Gets byte size in human readable format
    """
    for unit in ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'):
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1000.0

    return "%.1f%s%s" % (num, 'Y', suffix)


def is_valid_github(secret):
    """
    Validates a GitHub hook payload
    """
    if 'X-Hub-Signature' not in request.headers:
        return False

    hash_type, signature = request.headers['X-Hub-Signature'].split('=')
    if hash_type.lower() != 'sha1':
        logging.warn("Unknown GitHub hash type: '%s'", hash_type)
        return False

    computed_signature = hmac.new(secret.encode(),
                                  request.data,
                                  hashlib.sha1).hexdigest()

    return signature == computed_signature


def login_or_github_required(func):
    """
    Decorator to either check for GitHub headers, or require a login
    """
    login_required_func = login_required(func)

    @wraps(func)
    def inner(*args, **kwargs):
        """
        Check headers, pass to func or login_required decorator on outcome
        """
        if request.method == 'POST' and 'X-Github-Event' in request.headers:
            return func(*args, **kwargs)

        else:
            return login_required_func(*args, **kwargs)

    return inner


def is_hex_string(value, max_len=None):
    """
    Is the value a hex string (only characters 0-f)
    """
    if max_len:
        regex = r'^[a-fA-F0-9]{1,%d}$' % max_len
    else:
        regex = r'^[a-fA-F0-9]+$'

    return re.match(regex, value) is not None


def is_git_hash(value):
    """
    Validate a git commit hash for validity
    """
    return is_hex_string(value, 40)


def setup_templates(app):
    """
    Add util filters/tests/etc to the app's Jinja context
    """
    # pylint:disable=unused-variable
    @app.template_test('an_array')
    def an_array(val):
        """
        Jinja test to see if the value is array-like (tuple, list)
        """
        return isinstance(val, (tuple, list))


def tokengetter_for(oauth_app):
    """
    Flask security tokengetter for an endpoint
    """
    def inner():
        """
        Create a tokengetter for the current_user model
        """
        return get_token_for(oauth_app)

    return inner


def get_token_for(oauth_app):
    """
    Get a token for the currently logged in user
    """
    if current_user.is_authenticated():
        token = current_user.oauth_tokens.filter_by(
            service=oauth_app.name,
        ).first()

        if token:
            from dockci.server import OAUTH_APPS_SCOPES
            if token.scope == OAUTH_APPS_SCOPES[oauth_app.name]:
                return (token.key, token.secret)

    return None


def guess_multi_value(value):
    """
    Make the best kind of list from `value`. If it's already a list, or tuple,
    do nothing. If it's a value with new lines, split. If it's a single value
    without new lines, wrap in a list
    """
    if isinstance(value, (tuple, list)):
        return value

    if isinstance(value, str) and '\n' in value:
        return [line.strip() for line in value.split('\n')]

    return [value]


def fq_object_class_name(obj):
    """ Fully qualified name for an object's class """
    return '%s.%s' % (obj.__class__.__module__,
                      obj.__class__.__name__)


def auth_token_data_from_form(form_data, user, model):
    """
    Give the data dict necessary for an auth token, filling values from the
    form where possible
    """
    return {
        'user_id': user.id,
        'model_class': fq_object_class_name(model),
        'model_id': model.id,
        'operation': form_data.get('operation', None),
        'expiry': int(form_data['expiry']),  # Should be checked previously
    }


def auth_token_data(user, model, operation, expiry):
    """ Give the data dict necessary for an auth token """
    return {
        'user_id': user.id,
        'model_class': fq_object_class_name(model),
        'model_id': model.id,
        'operation': operation,
        'expiry': expiry,
    }


def auth_token_expiry():
    """ Expiry date for a new auth token """
    return int(datetime.datetime.now().timestamp()) + AUTH_TOKEN_EXPIRY


def create_auth_token(secret, token_data):
    """
    Create an auth token for a user to do a destructive operation on a model
    """
    # TODO HMAC default here is MD5. This needs to NOT be MD5
    return b64encode(hmac.new(
        secret.encode(),
        pickle.dumps(token_data),
        'sha256',
    ).digest()).decode()


def validate_auth_token(secret, form_data, user, model):
    """ Validate that auth token data in the form is valid """
    try:
        expiry = int(form_data.get('expiry', ''))
    except ValueError:
        return False  # TODO better logging

    now = int(datetime.datetime.now().timestamp())
    if expiry < now:
        return False

    req_auth_token = create_auth_token(
        secret, auth_token_data_from_form(form_data, user, model),
    )

    return hmac.compare_digest(req_auth_token,
                               form_data.get('auth_token', None))


def str2bool(value):
    """ Convert a string to a boolean, accounting for english-like terms """
    value = value.lower()

    try:
        return bool(int(value))
    except ValueError:
        pass

    return value in ('yes', 'true', 'y', 't')


def path_contained(outer_path, inner_path):
    """ Ensure that ``inner_path`` is contained within ``outer_path`` """
    common = inner_path.common(outer_path)
    try:
        # Account for symlinks
        return common.samefile(outer_path)

    except py.error.ENOENT:
        return common == outer_path


def client_kwargs_from_config(host_str):
    """ Generate Docker Client kwargs from the host string """
    docker_host, *arg_strings = shlex.split(host_str)
    docker_client_args = {
        'base_url': docker_host,
    }

    tls_args = {}
    for arg_string in arg_strings:
        arg_name, arg_val = arg_string.split('=', 1)
        if arg_name == 'cert_path':
            cert_path = py.path.local(arg_val)
            tls_args['client_cert'] = (
                cert_path.join('cert.pem').strpath,
                cert_path.join('key.pem').strpath,
            )

            # Assign the CA if it exists, and verify isn't overridden
            ca_path = cert_path.join('ca.pem')
            if ca_path.check() and tls_args.get('verify', None) != False:
                tls_args['verify'] = ca_path.strpath

        elif arg_name == 'assert_hostname':
            tls_args[arg_name] = str2bool(arg_val)

        elif arg_name == 'verify':
            tls_args[arg_name] = str2bool(arg_val)

        elif arg_name == 'ssl_version':
            tls_args['ssl_version'] = getattr(ssl, 'PROTOCOL_%s' % arg_val)

    if tls_args:
        docker_client_args['tls'] = docker.tls.TLSConfig(**tls_args)

    return docker_client_args


GIT_NAME_REV_BRANCH = re.compile(r'^(remotes/origin/|refs/heads/)([^~]+)')
GIT_NAME_REV_TAG = re.compile(r'^(refs/tags/)([^~]+)')


def parse_ref(ref):
    """
    Discover what type of ref is passed in, and convert to a short ref name. It
    is assumed that a ref with no full name is a branch.

    Returns:
      tuple(str, str): Ref type, and ref short name
      tuple(None, str): Ref type was unknown. Ref name is the full ref
    """
    for ref_type, func in (
        ('branch', parse_branch_from_ref),
        ('tag', parse_tag_from_ref),
        ('branch', lambda ref: parse_branch_from_ref(ref, relax=True))
    ):
        parsed = func(ref)
        if parsed is not None:
            return ref_type, parsed

    return None, ref


def parse_branch_from_ref(ref, strict=True, relax=False):
    """ Get a branch name from a git symbolic name """
    parsed = _parse_from_ref(ref, GIT_NAME_REV_BRANCH, strict)
    if parsed is not None:
        return parsed
    elif relax and '/' not in ref:
        return ref

    return None


def parse_tag_from_ref(ref, strict=True):
    """ Get a tag name from a git symbolic name """
    return _parse_from_ref(ref, GIT_NAME_REV_TAG, strict)


def _parse_from_ref(ref, regex, strict):
    """ Logic for the tag/branch ref parsers """
    ref_match = regex.search(ref)

    if ref_match:
        return ref_match.groups()[1]
    elif not strict:
        return ref

    return None


def project_root():
    """ Get the DockCI project root """
    return local(__file__).dirpath().join('..')


def bin_root():
    """ Get the bin directory of the execution env """
    return local(sys.prefix).join('bin')


def ext_url_for(endpoint, **values):
    """ Use ``external_url`` from config to build a full URL """
    from dockci.server import CONFIG

    if not CONFIG.external_url:
        return None

    ext_url = urlparse(CONFIG.external_url)
    method = values.pop('_method', None)
    return current_app.url_map.bind(
        ext_url.netloc,
        script_name=ext_url.path,
        url_scheme=values.pop('_scheme', ext_url.scheme),
    ).build(
        endpoint,
        values,
        method=method,
        force_external=True,
    )


def add_to_url_path(url, more_path):
    """ Appends ``more_path`` to ``url`` path, and normalizes the output """
    url = list(urlparse(url))
    url[2] = re.sub('//+', '/', ('%s/%s' % (url[2], more_path)))
    return urlunparse(url)


def unique_model_conflicts(klass, ignored_id=None, **fields):
    """ Find any models that have values in fields """
    queries = {
        field_name: klass.query.filter_by(**{field_name: field_value})
        for field_name, field_value in fields.items()
    }

    if ignored_id is not None:
        queries = {
            field_name: query.filter(klass.id != ignored_id)
            for field_name, query in queries.items()
        }

    return {
        field_name: query
        for field_name, query in queries.items()
        if query.count() > 0
    }


def gravatar_url(email, size=None):
    """
    Get a Gravatar URL from an email address

    >>> gravatar_url('ricky@spruce.sh')
    'https://s.gravatar.com/avatar/35866d5d838f7aeb9b51a29eda9878e7'

    >>> gravatar_url('hello@spruce.sh')
    'https://s.gravatar.com/avatar/6f54fe761ebc48100522fc2bdf958848'

    >>> gravatar_url('ricky@spruce.sh', size=100)
    'https://s.gravatar.com/avatar/35866d5d838f7aeb9b51a29eda9878e7?s=100'

    >>> gravatar_url('hello@spruce.sh', size=120)
    'https://s.gravatar.com/avatar/6f54fe761ebc48100522fc2bdf958848?s=120'
    """
    email_digest = hashlib.md5(email.lower().encode()).hexdigest()
    url = "https://s.gravatar.com/avatar/" + email_digest
    if size is not None:
        url += '?' + urlencode({'s': str(size)})

    return url


API_RE = re.compile(r'/api/.*')


def is_api_request(check_request=None):
    """
    Checks if the request is for the API

    Examples:

    >>> from dockci.server import APP

    >>> with APP.test_request_context('/api/v1/projects'):
    ...     is_api_request(request)
    True

    >>> with APP.test_request_context('/projects/dockci'):
    ...     is_api_request(request)
    False
    """
    if check_request is None:
        check_request = request

    try:
        check_path = check_request.url_rule.rule
    except AttributeError:
        check_path = check_request.path

    return API_RE.match(check_path) is not None


def jwt_token(**kwargs):
    """
    Create a new JWT token with the given args

    Examples:

    >>> from .server import CONFIG

    >>> token = jwt_token()
    >>> jwt.decode(token, CONFIG.secret)
    {'iat': ...}

    >>> token = jwt_token(name='test')
    >>> data = jwt.decode(token, CONFIG.secret)
    >>> sorted(list(data.items()))
    [('iat', ...), ('name', 'test')]

    >>> token = jwt_token(iat=1111)
    >>> jwt.decode(token, CONFIG.secret)
    {'iat': 1111}
    """
    from .server import CONFIG

    jwt_kwargs = kwargs.copy()
    if 'sub' not in jwt_kwargs and current_user.is_authenticated():
        jwt_kwargs['sub'] = current_user.id
    if 'iat' not in jwt_kwargs:
        jwt_kwargs['iat'] = datetime.datetime.utcnow()

    jwt_kwargs = {
        key: value
        for key, value in jwt_kwargs.items()
        if value is not None
    }

    return jwt.encode(jwt_kwargs, CONFIG.secret).decode()


def check_auth_fail_window(window):
    """
    Check an auth fail window for throttling

    Examples:

    >>> from .server import CONFIG
    >>> class MockWindow(object):
    ...     def __init__(self, count):
    ...         self.count_raw = count
    ...     def count(self):
    ...         return self.count_raw

    >>> CONFIG.auth_fail_max = 10
    >>> check_auth_fail_window(MockWindow(10))
    False

    >>> check_auth_fail_window(MockWindow(11))
    False

    >>> check_auth_fail_window(MockWindow(9))
    True

    >>> CONFIG.auth_fail_max = 5
    >>> check_auth_fail_window(MockWindow(5))
    False

    >>> check_auth_fail_window(MockWindow(6))
    False

    >>> check_auth_fail_window(MockWindow(4))
    True
    """
    from .server import CONFIG
    if window.count() >= CONFIG.auth_fail_max:
        return False
    return True


def check_auth_fail(suffixes, redis_pool_):
    """ Check the auth fail windows for a set of window suffixes """
    from .server import CONFIG

    windows = [
        RedisWindow(
            'auth_fail_%s' % suffix,
            CONFIG.auth_fail_ttl_sec,
            redis_pool_,
        )
        for suffix in suffixes
    ]

    return windows, all(check_auth_fail_window(window) for window in windows)


class RedisWindow(object):
    """ Sliding window, using Redis to store data """

    def __init__(self, key, ttl, redis_pool=None):
        self.key = key
        self.ttl = ttl
        self.redis_pool = redis_pool

    _redis = None

    @property
    def redis(self):
        """ Get a Redis object """
        if self._redis is None:
            self._redis = redis.Redis(connection_pool=self.redis_pool)

        return self._redis

    @property
    def tail_score(self):
        """ Score for the tail of the window """
        return self.head_score - self.ttl

    @property
    def head_score(self):  # pylint:disable=no-self-use
        """ Score for the head of the window """
        return int(datetime.datetime.utcnow().timestamp())

    def remove_old(self, pipe):
        """ Remove old values from the window """
        pipe.zremrangebyscore(self.key, '-inf', self.tail_score)

    def add(self, value):
        """ Add a value to the window """
        with self.redis.pipeline() as pipe:
            self.remove_old(pipe)
            pipe.zadd(self.key, **{value: self.head_score})
            pipe.expire(self.key, self.ttl)

            return all(pipe.execute())

    def count(self):
        """ Count the number of values currently in the window """
        with self.redis.pipeline() as pipe:
            self.remove_old(pipe)
            pipe.zcard(self.key)

            return pipe.execute()[1]


ADMIN_PERMISSION = Permission(RoleNeed('admin'))
AGENT_PERMISSION = Permission(RoleNeed('agent'))


def show_error(status, message):
    """
    If API request, do a REST abort with JSON message. Otherwise, flash the
    error
    """
    if is_api_request():
        rest_abort(status, message=message)

    flash(message)


def require_admin(func):
    """ Decorator to require ``ADMIN_PERMISSION`` """
    @wraps(func)
    def inner(*args, **kwargs):
        """ Check for admin """
        if not ADMIN_PERMISSION.can():
            show_error(401, 'Only an administrator can do this')
        return func(*args, **kwargs)
    return inner


def require_agent(func):
    """ Decorator to require ``AGENT_PERMISSION`` """
    @wraps(func)
    def inner(*args, **kwargs):
        """ Check for agent """
        if not AGENT_PERMISSION.can():
            show_error(401, 'Only an agent can do this')
        return func(*args, **kwargs)
    return inner


def require_me_or_admin(func):
    """
    Decorator to require ``ADMIN_PERMISSION``, or the current user to be the
    same as either the ``user_id`` or ``user`` kwargs. If API request, aborts
    with errors. Otherwise, flashes an error and unsets the user kwargs.
    """
    @wraps(func)
    def inner(*args, **kwargs):
        """ Check for admin, or user matches """
        if ADMIN_PERMISSION.can():
            return func(*args, **kwargs)

        user_id = kwargs.get('user_id', None)
        user = kwargs.get('user', None)

        okay = True

        if user is not None and user_id is not None:
            if user.id != user_id:
                show_error(500, "Somehow user, and user ID don't match")

            okay = False

        if user is None and user_id is None:
            show_error(400, "No user requested")
            okay = False

        if user is not None:
            user_id = user.id

        if current_user.id != user_id:
            show_error(401, "Only the requested user, or an admin can do this")
            okay = False

        if not okay:
            kwargs['user'] = None
            kwargs['user_id'] = None

        return func(*args, **kwargs)

    return inner
