import os

from dockci.server import MANAGER


@MANAGER.command
def bash():
    """ Execute a bash shell """
    os.execvp('/bin/bash', ['/bin/bash'])
