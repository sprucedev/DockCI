"""
Functions for setting up and starting the DockCI application server
"""

import logging
import mimetypes
import multiprocessing
import os

from flask import Flask
from flask_oauthlib.client import OAuth
from flask_security import Security, SQLAlchemyUserDatastore
from flask_mail import Mail
from flask_migrate import Migrate
from flask_restful import Api
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import NullPool

from dockci.models.config import Config
from dockci.util import setup_templates, tokengetter_for


class WrappedSQLAlchemy(SQLAlchemy):
    """ ``SQLAlchemy`` object that makes the ``poolclass`` a ``NullPool`` """
    def apply_pool_defaults(self, app, options):
        options['poolclass'] = NullPool


APP = Flask(__name__)
MAIL = Mail()
CONFIG = Config()
SECURITY = Security()
DB = WrappedSQLAlchemy()
OAUTH = OAuth(APP)
API = Api(APP, prefix='/api/v1')
MANAGER = Manager(APP)
MIGRATE = Migrate(APP, DB, directory='alembic')

APP.config.model = CONFIG  # For templates


OAUTH_APPS = {}
OAUTH_APPS_SCOPES = {}
OAUTH_APPS_SCOPE_SERIALIZERS = {
    'github': lambda scope: ','.join(sorted(scope.split(','))),
}


def get_db_uri():
    """ Try to get the DB URI from multiple sources """
    if 'DOCKCI_DB_URI' in os.environ:
        return os.environ['DOCKCI_DB_URI']
    elif (
        'POSTGRES_PORT_5432_TCP_ADDR' in os.environ and
        'POSTGRES_PORT_5432_TCP_PORT' in os.environ and
        'POSTGRES_ENV_POSTGRES_PASSWORD' in os.environ
    ):
        return "postgresql://{user}:{password}@{addr}:{port}/{name}".format(
            addr=os.environ['POSTGRES_PORT_5432_TCP_ADDR'],
            port=os.environ['POSTGRES_PORT_5432_TCP_PORT'],
            password=os.environ['POSTGRES_ENV_POSTGRES_PASSWORD'],
            user=os.environ.get('POSTGRES_ENV_POSTGRES_USER', 'postgres'),
            name=os.environ.get(
                'POSTGRES_ENV_POSTGRES_DB',
                os.environ.get('POSTGRES_ENV_POSTGRES_USER', 'dockci'),
            ),
        )


def app_init():
    """
    Pre-run app setup
    """
    logger = logging.getLogger('dockci.init')

    logger.info("Loading app config")

    APP.secret_key = CONFIG.secret

    APP.config['BUNDLE_ERRORS'] = True

    APP.config['MAIL_SERVER'] = CONFIG.mail_server
    APP.config['MAIL_PORT'] = CONFIG.mail_port
    APP.config['MAIL_USE_TLS'] = CONFIG.mail_use_tls
    APP.config['MAIL_USE_SSL'] = CONFIG.mail_use_ssl
    APP.config['MAIL_USERNAME'] = CONFIG.mail_username
    APP.config['MAIL_PASSWORD'] = CONFIG.mail_password
    APP.config['MAIL_DEFAULT_SENDER'] = CONFIG.mail_default_sender

    APP.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
    APP.config['SECURITY_PASSWORD_SALT'] = CONFIG.security_password_salt
    APP.config['SECURITY_REGISTERABLE'] = CONFIG.security_registerable
    APP.config['SECURITY_RECOVERABLE'] = CONFIG.security_recoverable
    APP.config['SECURITY_CHANGEABLE'] = True
    APP.config['SECURITY_EMAIL_SENDER'] = CONFIG.mail_default_sender

    APP.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()

    if CONFIG.server_name:
        APP.config['SERVER_NAME'] = CONFIG.server_name

    mimetypes.add_type('application/x-yaml', 'yaml')

    from dockci.models.auth import User, Role
    from dockci.models.job import Job  # pylint:disable=unused-variable
    from dockci.models.project import Project  # pylint:disable=unused-variable

    if 'security' not in APP.blueprints:
        SECURITY.init_app(APP, SQLAlchemyUserDatastore(DB, User, Role))

    MAIL.init_app(APP)
    DB.init_app(APP)

    app_init_oauth()
    app_init_handlers()
    app_init_api()
    app_init_views()
    app_init_workers()


def app_init_workers():
    """
    Initialize the worker job queue
    """
    from .workers import start_workers
    APP.worker_queue = multiprocessing.Queue()
    start_workers()


def app_init_oauth():
    """
    Initialize the OAuth integrations
    """
    if CONFIG.github_key and CONFIG.github_secret:
        if 'github' not in OAUTH_APPS:
            scope = 'user:email,admin:repo_hook,repo'
            OAUTH_APPS_SCOPES['github'] = \
                OAUTH_APPS_SCOPE_SERIALIZERS['github'](scope)
            OAUTH_APPS['github'] = OAUTH.remote_app(
                'github',
                consumer_key=CONFIG.github_key,
                consumer_secret=CONFIG.github_secret,
                request_token_params={'scope': scope},
                base_url='https://api.github.com/',
                request_token_url=None,
                access_token_method='POST',
                access_token_url='https://github.com/login/oauth/access_token',
                authorize_url='https://github.com/login/oauth/authorize'
            )

    for oauth_app in OAUTH_APPS.values():
        oauth_app.tokengetter(tokengetter_for(oauth_app))


def app_init_handlers():
    """ Initialize event handlers """
    # pylint:disable=unused-variable
    import dockci.handlers


def app_init_api():
    """ Activate the DockCI API """
    # pylint:disable=unused-variable
    import dockci.api


def app_init_views():
    """
    Activate all DockCI views
    """
    # pylint:disable=unused-variable
    import dockci.views
    setup_templates(APP)
