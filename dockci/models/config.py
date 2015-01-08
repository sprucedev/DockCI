"""
Application configuration models
"""

import os.path
import socket

from urllib.parse import urlparse
from uuid import uuid4

from dockci.util import default_gateway
from dockci.yaml_model import LoadOnAccess, SingletonModel


def default_docker_host():
    """
    Get a default value for the docker_host variable. This will work out
    if DockCI is running in Docker, and try and guess the Docker IP address
    to use for a TCP connection. Otherwise, defaults to the default
    unix socket.
    """
    docker_files = ('/.dockerenv', '/.dockerinit')
    if any(os.path.isfile(filename) for filename in docker_files):
        return "tcp://{ip}:2375".format(ip=default_gateway())

    return "unix:///var/run/docker.sock"


class Config(SingletonModel):  # pylint:disable=too-few-public-methods
    """
    Global application configuration
    """
    restart_needed = False

    # TODO docker_hosts
    secret = LoadOnAccess(generate=lambda _: uuid4().hex)

    docker_use_env_vars = LoadOnAccess(default=lambda _: False,
                                       input_transform=bool)
    docker_host = LoadOnAccess(default=lambda _: default_docker_host())
    docker_workers = LoadOnAccess(default=lambda _: 5)

    mail_server = LoadOnAccess(default=lambda _: "localhost")
    mail_port = LoadOnAccess(default=lambda _: 25, input_transform=int)
    mail_use_tls = LoadOnAccess(default=lambda _: False, input_transform=bool)
    mail_use_ssl = LoadOnAccess(default=lambda _: False, input_transform=bool)
    mail_username = LoadOnAccess(default=lambda _: None)
    mail_password = LoadOnAccess(default=lambda _: None)
    mail_default_sender = LoadOnAccess(default=lambda _:
                                       "dockci@%s" % socket.gethostname())

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
