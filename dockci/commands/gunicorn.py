from gunicorn.app.base import BaseApplication

from dockci.server import APP, app_init, MANAGER


class GunicornWrapper(BaseApplication):
    """ Gunicorn application for DockCI Flask app """
    def __init__(self, options=None):
        self.options = options or {}
        super(GunicornWrapper, self).__init__()

    def load_config(self):
        """ Setup Gunicorn config """
        from pprint import pprint; pprint(self.cfg.settings)
        config = dict([(key, value) for key, value in self.options.items()
                       if key in self.cfg.settings and value is not None])
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        """ Init, and return the Flask app """
        app_init({})
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
@MANAGER.option("--db-uri",
                help="URI of the database to connect to")
def run(**kwargs):
    """ Run the Gunicorn worker """
    kwargs['reload'] = kwargs['debug']
    kwargs['preload'] = not kwargs['debug']
    APP.debug = kwargs['debug']
    GunicornWrapper(kwargs).run()
