""" Flask-Script commands for starting/managing Gunicorn """
import subprocess
import time

from sys import stderr

from flask_migrate import upgrade as db_upgrade
from gunicorn.app.base import BaseApplication
from pika.exceptions import AMQPError
from py.path import local  # pylint:disable=import-error
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from dockci.server import APP, app_init, get_db_uri, get_pika_conn, MANAGER
from dockci.util import project_root


class GunicornWrapper(BaseApplication):  # pylint:disable=abstract-method
    """ Gunicorn application for DockCI Flask app """
    def __init__(self, options=None):
        self.options = options or {}
        super(GunicornWrapper, self).__init__()

    def load_config(self):
        """ Setup Gunicorn config """
        config = dict([(key, value) for key, value in self.options.items()
                       if key in self.cfg.settings and value is not None])
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

        # TODO required for streaming logs, but a bad idea in other cases
        self.cfg.set('timeout', 0)

    def load(self):
        """ Get the Flask app """
        return APP


@MANAGER.option("-w", "--workers",
                help="Number of gunicorn workers to start",
                default=10)
@MANAGER.option("--bind",
                help="Interface, and port to listen on",
                default="127.0.0.1:5000")
@MANAGER.option("--debug",
                help="Turn debug mode on for Flask, and stops app preload for "
                     "auto reloading",
                default=False, action='store_true')
@MANAGER.option("--db-migrate",
                default=False, action='store_true',
                help="Migrate the DB on load")
@MANAGER.option("--timeout",
                default=0, type=int,
                help="Time to wait for the resources to be available")
@MANAGER.option("--collect-static",
                default=False, action='store_true',
                help="Collect static dependencies before start")
def run(**kwargs):
    """ Run the Gunicorn worker """
    kwargs['reload'] = kwargs['debug']
    kwargs['preload'] = not kwargs['debug']
    APP.debug = kwargs['debug']

    if kwargs['collect_static']:
        subprocess.check_call('./_deps_collectstatic.sh',
                              cwd=project_root().strpath)

    if kwargs['timeout'] != 0:
        start_time = time.time()
        db_engine = create_engine(
            get_db_uri(),
            connect_args=dict(connect_timeout=2),
        )
        db_conn = None
        mq_conn = None
        while time.time() - start_time < kwargs['timeout']:
            try:
                if db_conn is None or db_conn.closed:
                    db_conn = db_engine.connect()
            except OperationalError:
                time.sleep(2)
                continue

            try:
                if mq_conn is None:
                    mq_conn = get_pika_conn()
            except AMQPError:
                time.sleep(2)
                continue

            break

        if db_conn is None or db_conn.closed:
            stderr.write("Timed out waiting for the database to be ready\n")
            return 1

        if mq_conn is None:
            stderr.write("Timed out waiting for RabbitMQ to be ready\n")
            return 1

    # Setup the exchange
    channel = mq_conn.channel()
    channel.exchange_declare(exchange='dockci.job', type='topic')
    mq_conn.close()

    if kwargs['db_migrate']:
        db_upgrade(  # doesn't return anything
            local(__file__).dirpath().join('../../alembic').strpath
        )

    else:
        # Migrate will init the app for us
        app_init()

    GunicornWrapper(kwargs).run()
