import subprocess

from urllib.parse import urlparse, urlunparse

import alembic
import pytest

from flask_migrate import migrate

from dockci.server import APP, app_init, DB, MIGRATE


@pytest.yield_fixture
def tmpgitdir(tmpdir):
    """ Get a new ``tmpdir``, make it the cwd, and set git config """
    with tmpdir.as_cwd():
        subprocess.check_call(['git', 'init'])
        for name, val in (
            ('user.name', 'DockCI Test'),
            ('user.email', 'test@example.com'),
        ):
            subprocess.check_call(['git', 'config', name, val])

        yield tmpdir


@pytest.yield_fixture(scope='session')
def base_db_conn():
    """ App setup with DockCI database """
    app_init()
    try:
        DB.engine

    except Exception as ex:
        pytest.skip(str(ex))

    else:
        db_name = '%s_test' % DB.engine.url.database

        with DB.engine.contextual_connect() as conn:
            conn.execution_options(isolation_level='AUTOCOMMIT')
            conn.execute('DROP DATABASE IF EXISTS %s' % db_name)
            conn.execute('CREATE DATABASE %s' % db_name)

            DB.engine.url.database = db_name
            APP.config['SQLALCHEMY_DATABASE_URI'] = DB.engine.url
            app_init()

            yield conn

            conn.execute('DROP DATABASE %s' % db_name)


@pytest.yield_fixture
def db(base_db_conn):
    """ App setup with blank DockCI database """
    config = MIGRATE.get_config(None)
    alembic.command.upgrade(config, 'head')

    session = DB.session
    session.begin_nested()
    try:
        yield
    finally:
        session.rollback()
