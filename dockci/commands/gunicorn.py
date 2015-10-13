import time

from sys import stderr

from flask_migrate import upgrade as db_upgrade
from gunicorn.app.base import BaseApplication
from py.path import local
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from dockci.server import APP, app_init, get_db_uri, MANAGER


class GunicornWrapper(BaseApplication):
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
                default=20)
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
@MANAGER.option("--db-timeout",
                default=0, type=int,
                help="Time to wait for the database to be available")
def run(**kwargs):
    """ Run the Gunicorn worker """
    kwargs['reload'] = kwargs['debug']
    kwargs['preload'] = not kwargs['debug']
    APP.debug = kwargs['debug']

    if kwargs['db_timeout'] != 0:
        start_time = time.time()
        db_engine = create_engine(
            get_db_uri(kwargs),
            connect_args=dict(connect_timeout=2),
        )
        db_conn = None
        while time.time() - start_time < kwargs['db_timeout']:
            try:
                db_conn = db_engine.connect()
            except OperationalError as ex:
                time.sleep(2)
            else:
                break

        if db_conn is None or db_conn.closed:
            stderr.write("Timed out waiting for the database to be ready\n")
            return 1

    if kwargs['db_migrate']:
        ret = db_upgrade(
            local(__file__).dirpath().join('../../alembic').strpath
        )
        if ret != 0 and ret is not None:
            return ret

    else:
        # Migrate will init the app for us
        app_init(kwargs)

    GunicornWrapper(kwargs).run()
