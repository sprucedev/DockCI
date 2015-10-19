"""
Views related to project management
"""

import sqlalchemy

from flask import redirect, render_template, request

from dockci.api.job import filter_jobs_by_request
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import APP
from dockci.util import str2bool


def shields_io_sanitize(text):
    """ Replace chars in shields.io fields """
    return text.replace('-', '--').replace('_', '__').replace(' ', '_')


@APP.route('/project/<slug>.<extension>', methods=('GET',))
def project_shield_view(slug, extension):
    """ View to give shields for each project """
    project = Project.query.filter_by(slug=slug).first_or_404()

    try:
        query = '?style=%s' % request.args['style']
    except KeyError:
        query = ''

    return redirect(
        'https://img.shields.io/badge/'
        '{name}-{shield_status}-{shield_color}.{extension}{query}'.format(
            name=shields_io_sanitize(project.name),
            shield_status=shields_io_sanitize(project.shield_text),
            shield_color=shields_io_sanitize(project.shield_color),
            extension=extension,
            query=query,
        )
    )


@APP.route('/projects/<slug>', methods=('GET',))
def project_view(slug):
    """
    View to display a project
    """
    project = Project.query.filter_by(slug=slug).first_or_404()

    page_size = int(request.args.get('page_size', 20))
    page = int(request.args.get('page', 1))

    jobs = filter_jobs_by_request(project).paginate(page, page_size)

    # Copied from filter_jobs_by_request :(
    try:
        versioned = request.values['versioned']
        if versioned == '':  # Acting as a switch
            versioned = True
        else:
            versioned = str2bool(versioned)

    except KeyError:
        versioned = False

    return render_template(
        'project.html',
        project=project,
        jobs=jobs,
        versioned=versioned,
        branch=request.values.get('branch', None),
    )
