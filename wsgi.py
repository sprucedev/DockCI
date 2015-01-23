"""
WSGI wrapper to init, and correctly name the app
"""
import logging

from dockci.server import app_init, APP as application

logging.basicConfig(level=logging.DEBUG)
app_init()
