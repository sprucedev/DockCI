import random
import subprocess

from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse

import alembic
import pytest

from flask_migrate import migrate

from dockci.models.auth import Role
from dockci.models.job import Job, JobStageTmp
from dockci.models.project import Project
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

            try:
                yield conn
            finally:
                conn.execute('DROP DATABASE %s' % db_name)


@pytest.yield_fixture
def db(base_db_conn):
    """ App setup with blank DockCI database """
    config = MIGRATE.get_config(None)
    alembic.command.upgrade(config, 'head')

    DB.session.begin(nested=True)
    try:
        yield
    finally:
        DB.session.rollback()


@contextmanager
def db_fixture_helper(model, delete=False):
    """ Common DB fixture logic """
    DB.session.add(model)
    DB.session.commit()
    try:
        yield model
    finally:
        if delete:
            DB.session.delete(model)
            DB.session.commit()


@pytest.fixture
def randid():
    """ Random ID """
    return random.randint(0, 1000000)


@pytest.yield_fixture
def admin_user(db, randid):
    """ Admin user in the DB """
    from dockci.models.auth import Role
    with db_fixture_helper(
        APP.extensions['security'].datastore.create_user(
            email='admin%s@example.com' % randid,
            password='testpass',
            roles=[Role.query.filter_by(name='admin').first()]
        )
    ) as model:
        yield model


@pytest.yield_fixture
def user(db, randid):
    """ Normal user in the DB """
    with db_fixture_helper(
        APP.extensions['security'].datastore.create_user(
            email='user%s@example.com' % randid,
            password='testpass',
        )
    ) as model:
        yield model


@pytest.fixture
def agent_token(db):
    """ A service token with agent role """
    from dockci.util import jwt_token
    return jwt_token(sub='service', name='test', roles=['agent'])


@pytest.yield_fixture
def role(db, randid):
    """ Role in the DB """
    with db_fixture_helper(Role(
        name="testrole%s" % randid,
        description='Test role %s' % randid,
    )) as model:
        yield model


@pytest.yield_fixture
def project(db, randid):
    """ Project in the DB """
    with db_fixture_helper(Project(
        slug=randid,
        name=randid,
        repo='test',
        utility=False,
        public=True
    ), delete=True) as model:
        yield model

@pytest.yield_fixture
def job(db, project):
    """ Job in the DB """
    with db_fixture_helper(Job(
        project=project,
        repo_fs=project.repo_fs,
        commit='test',
    ), delete=True) as model:
        yield model


@pytest.yield_fixture
def stage(db, job, randid):
    """ Stage in the DB """
    with db_fixture_helper(JobStageTmp(job=job), delete=True) as model:
        yield model


@pytest.yield_fixture
def client():
    """ Flask app test client """
    old_testing = APP.config['TESTING']
    APP.config['TESTING'] = True
    try:
        yield APP.test_client()
    finally:
        APP.config['TESTING'] = old_testing
