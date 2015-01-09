"""
Functions for setting up and starting the DockCI application server
"""

import mimetypes
import multiprocessing
import multiprocessing.pool

from flask import Flask
from flask_mail import Mail
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from dockci.models.config import Config


APP = Flask(__name__)
MAIL = Mail()
CONFIG = Config()

APP.config.model = CONFIG  # For templates


def app_setup_extra():
    """
    Pre-run app setup
    """
    APP.secret_key = CONFIG.secret

    APP.config['MAIL_SERVER'] = CONFIG.mail_server
    APP.config['MAIL_PORT'] = CONFIG.mail_port
    APP.config['MAIL_USE_TLS'] = CONFIG.mail_use_tls
    APP.config['MAIL_USE_SSL'] = CONFIG.mail_use_ssl
    APP.config['MAIL_USERNAME'] = CONFIG.mail_username
    APP.config['MAIL_PASSWORD'] = CONFIG.mail_password
    APP.config['MAIL_DEFAULT_SENDER'] = CONFIG.mail_default_sender

    # Import loop if this is imported at head
    from dockci.workers import init_mail_queue
    MAIL.init_app(APP)
    init_mail_queue()

    # Pool must be started after mail is initialized
    APP.workers = multiprocessing.pool.Pool(int(CONFIG.docker_workers))

    mimetypes.add_type('application/x-yaml', 'yaml')


def app_setup_views():
    """
    Activate all DockCI views
    """
    # pylint:disable=unused-variable
    import dockci.views.core

    import dockci.views.build
    import dockci.views.job


def run(app_args):
    """
    Setup, and run the DockCI application server, using the args given to
    configure it
    """
    app_setup_extra()
    app_setup_views()

    server_args = {
        key: val
        for key, val in app_args.items()
        if key in ('host', 'port', 'debug')
    }
    if server_args.get('debug', False):
        APP.run(**server_args)
    else:
        http_server = HTTPServer(WSGIContainer(APP))
        http_server.listen(port=server_args['port'],
                           address=server_args['host'])
        IOLoop.instance().start()
