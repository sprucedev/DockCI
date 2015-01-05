"""
Functions for setting up and starting the DockCI application server
"""

import mimetypes
import multiprocessing
import multiprocessing.pool

from flask import Flask
from flask_mail import Mail

from dockci.models.config import Config


APP = Flask(__name__)
MAIL = Mail()
MAIL_QUEUE = multiprocessing.Queue()  # pylint:disable=no-member
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
    from dockci.main import init_mail_queue
    MAIL.init_app(APP)
    init_mail_queue()

    # Pool must be started after mail is initialized
    APP.workers = multiprocessing.pool.Pool(int(CONFIG.workers))

    mimetypes.add_type('application/x-yaml', 'yaml')


def run(app_args):
    """
    Setup, and run the DockCI application server, using the args given to
    configure it
    """
    app_setup_extra()

    server_args = {
        key: val
        for key, val in app_args.items()
        if key in ('host', 'port', 'debug')
    }
    APP.run(**server_args)
