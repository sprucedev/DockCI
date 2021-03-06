"""
Core app views
"""

import py.error  # pylint:disable=import-error

from flask import abort, render_template, request
from flask_security import login_required, roles_required

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
@roles_required('admin')
def config_edit_view():
    """
    View to edit global config
    """
    restart_fields = (
        'secret',
        'docker_use_env_vars', 'docker_hosts',
        'mail_host_string', 'mail_use_tls', 'mail_use_ssl',
        'mail_username', 'mail_password', 'mail_default_sender',
        'security_registerable_form', 'security_login_form',
        'security_registerable_github', 'security_login_github',
        'security_registerable_gitlab', 'security_login_gitlab',
        'security_recoverable',
        'external_url', 'external_rabbit_uri',
        'github_key', 'github_secret',
        'gitlab_key', 'gitlab_secret', 'gitlab_base_url',
        'live_log_message_timeout', 'live_log_session_timeout',
        'redis_len_expire',
        'auth_fail_max', 'auth_fail_ttl_sec',
        'oauth_authorized_redirects',
    )
    all_fields = restart_fields + ()
    blanks = (
        'external_url', 'external_rabbit_uri',
        'github_key', 'gitlab_key', 'gitlab_base_url',
        'mail_host_string', 'mail_default_sender', 'mail_username',
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
@roles_required('admin')
def config_page_view(page):
    """ View and edit misc config """
    if page not in ('registries', 'users'):
        abort(404)
    return render_template('config_page.html', page=page)
