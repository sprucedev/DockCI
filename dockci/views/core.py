"""
Core app views
"""

import py.error  # pylint:disable=import-error

from flask import abort, render_template, request
from flask_security import login_required

from dockci.server import APP, CONFIG
from dockci.util import request_fill


@APP.route('/')
def index_view():
    """
    View to display the list of all projects
    """
    return render_template('index.html')


@APP.route('/config', methods=('GET', 'POST'))
@login_required
def config_edit_view():
    """
    View to edit global config
    """
    restart_fields = (
        'secret',
        'docker_use_env_vars', 'docker_hosts',
        'mail_host_string', 'mail_use_tls', 'mail_use_ssl',
        'mail_username', 'mail_password', 'mail_default_sender',
        'security_registerable', 'security_recoverable',
        'external_url',
        'github_key', 'github_secret',
        'gitlab_key', 'gitlab_secret', 'gitlab_base_url',
    )
    all_fields = restart_fields + (
        'docker_use_registry', 'docker_registry',
        'docker_registry_username', 'docker_registry_password',
        'docker_registry_email',
    )
    blanks = (
        'external_url', 'github_key', 'gitlab_key', 'gitlab_base_url',
        'mail_host_string', 'mail_default_sender', 'mail_username',
        'docker_registry', 'docker_registry_email', 'docker_registry_username',
    )

    if request.method == 'POST':
        saved = request_fill(CONFIG, all_fields, accept_blank=blanks)
    else:
        saved = False

    try:
        CONFIG.load()

    except py.error.ENOENT:
        pass

    if saved:
        restart_needed = any((
            (
                attr in request.form and
                request.form[attr] != getattr(CONFIG, attr)
            )
            for attr in restart_fields
        ))
        if restart_needed:
            CONFIG.restart_needed = True

    return render_template('config_edit.html')


@APP.route('/config/<page>', methods=('GET',))
@login_required
def config_page_view(page):
    """ View and edit misc config """
    if page not in ('registries',):
        abort(404)
    return render_template('config_page.html', page=page)
