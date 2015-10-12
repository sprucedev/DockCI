from flask_migrate import MigrateCommand

from dockci.server import MANAGER


MANAGER.add_command('db', MigrateCommand)
