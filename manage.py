#!/usr/bin/env python
import dockci.commands

from dockci.server import APP, app_init, MANAGER


if __name__ == "__main__":
    app_init()
    MANAGER.run()
