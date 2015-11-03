"""
Application configuration models
"""

import os
import socket

from urllib.parse import urlparse
from uuid import uuid4

import py.path  # pylint:disable=import-error
import requests.exceptions

from flask import has_request_context, request
from yaml_model import LoadOnAccess, SingletonModel, ValidationError

from dockci.exceptions import DockerUnreachableError
from dockci.util import (client_kwargs_from_config,
                         default_gateway,
                         guess_multi_value,
                         )


def default_docker_host():
    """
    Get a default value for the docker_host variable. This will work out
    if DockCI is running in Docker, and try and guess the Docker IP address
    to use for a TCP connection. Otherwise, defaults to the default
    unix socket.
    """
    try:
        return os.environ['DOCKER_HOST']
    except KeyError:
        pass

    if py.path.local('/var/run/docker.sock').check():
        return 'unix:///var/run/docker.sock'

    return default_host(
        "tcp://{ip}:2375",
        "unix:///var/run/docker.sock",
    )


def default_registry_host():
    """
    Get a default value for the registry_host variable. This will try Docker
    link env vars, and fall back to localhost:5000
    """
    try:
        return "http://{host}:{port}".format(
            host=os.environ['REGISTRY_PORT_5000_TCP_ADDR'],
            port=os.environ['REGISTRY_PORT_5000_TCP_PORT'],
        )

    except KeyError:
        pass

    return ""


def default_host(format_string, local_default=None):
    """
    Get a default host. If running in Docker, we get the default gateway, and
    use format string with the IP. Otherwise, returns the ``local_default``
    """
    docker_files = [py.path.local(path)
                    for path in ('/.dockerenv', '/.dockerinit')]
    if any(path.check() for path in docker_files):
        return format_string.format(ip=default_gateway())

    return local_default


def default_use_registry():
    """
    Get a value for the ``use_registry`` variable. True if Docker link env vars
    are set
    """
    return ('REGISTRY_PORT_5000_TCP_ADDR' in os.environ and
            'REGISTRY_PORT_5000_TCP_PORT' in os.environ)


def default_external_url():
    """ Try to get a server name from the request """
    if has_request_context():
        return request.host_url

    return None


class Config(SingletonModel):  # pylint:disable=too-few-public-methods
    """
    Global application configuration
    """
    restart_needed = False

    # TODO docker_hosts
    secret = LoadOnAccess(generate=lambda _: uuid4().hex)

    docker_use_env_vars = LoadOnAccess(default=lambda _: False,
                                       input_transform=bool)
    docker_hosts = LoadOnAccess(
        input_transform=guess_multi_value,
        default=lambda _: [default_docker_host()]
    )
    docker_use_registry = LoadOnAccess(
        default=lambda _: default_use_registry(),
        input_transform=bool,
    )
    docker_registry = LoadOnAccess(default=lambda _: default_registry_host())

    mail_server = LoadOnAccess(default=lambda _: "localhost")
    mail_port = LoadOnAccess(default=lambda _: 25, input_transform=int)
    mail_use_tls = LoadOnAccess(default=lambda _: False, input_transform=bool)
    mail_use_ssl = LoadOnAccess(default=lambda _: False, input_transform=bool)
    mail_username = LoadOnAccess(default=lambda _: None)
    mail_password = LoadOnAccess(default=lambda _: None)
    mail_default_sender = LoadOnAccess(default=lambda _:
                                       "dockci@%s" % socket.gethostname())

    external_url = LoadOnAccess(generate=lambda _: default_external_url())

    github_key = LoadOnAccess(default=lambda _: None)
    github_secret = LoadOnAccess(default=lambda _: None)

    security_password_salt = LoadOnAccess(generate=lambda _: uuid4().hex)
    security_registerable = LoadOnAccess(default=True)
    security_recoverable = LoadOnAccess(default=True)

    @property
    def docker_registry_host(self):
        """
        Get the hostname portion of the Docker registry
        """
        url = urlparse(self.docker_registry)
        return url.netloc

    @property
    def docker_registry_insecure(self):
        """
        Tell if the Docker registry URL is secure, or insecure
        """
        url = urlparse(self.docker_registry)
        return url.scheme.lower() == 'http'

    @property
    def mail_host_string(self):
        """
        Get the host/port as a h:p string
        """
        return "{host}:{port}".format(host=self.mail_server,
                                      port=self.mail_port)

    @mail_host_string.setter
    def mail_host_string(self, value):
        """
        Parse a URL string into host/port/user/pass and set the relevant attrs
        """
        url = urlparse('smtp://%s' % value)
        if url.hostname:
            self.mail_server = url.hostname
        if url.port:
            self.mail_port = url.port
        if url.username:
            self.mail_username = url.username
        if url.password:
            self.mail_password = url.password

    def validate(self):
        with self.parent_validation(Config):
            errors = []

            import docker
            for docker_host in self.docker_hosts:
                docker_client_args = client_kwargs_from_config(docker_host)

                try:
                    # pylint:disable=unused-variable
                    client = docker.Client(**docker_client_args)
                    client.ping()

                except docker.errors.DockerException as ex:
                    # pylint:disable=unpacking-non-sequence
                    message, *_ = ex.args
                    errors.append(message)

                except requests.exceptions.SSLError as ex:
                    errors.append(str(DockerUnreachableError(
                        docker_client_args['base_url'], ex,
                    )))

            if self.docker_registry != '':
                registry_url = urlparse(self.docker_registry)
                if registry_url.scheme.lower() not in ('http', 'https'):
                    errors.append("Registry URL must be HTTP, or HTTPS")

                invalid_url_parts = (
                    bool(getattr(registry_url, url_part))
                    for url_part
                    in ('path', 'params', 'query', 'fragment')
                )
                if any(invalid_url_parts):
                    errors.append("Registry URL can only include scheme, "
                                  "host, and port")

            if self.external_url is not None and self.external_url != '':
                external_url = urlparse(self.external_url)
                if external_url.scheme.lower() not in ('http', 'https'):
                    errors.append("External URL must be HTTP, or HTTPS")
                if not external_url.netloc:
                    errors.append("External URL must contain a host name")

                invalid_url_parts = (
                    bool(getattr(external_url, url_part))
                    for url_part
                    in ('params', 'query', 'fragment')
                )
                if any(invalid_url_parts):
                    errors.append("External URL can only include scheme, "
                                  "host, port, and path")

            if errors:
                raise ValidationError(errors)

        return True
