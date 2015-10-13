"""
Views related to project management
"""

import re

import sqlalchemy

from flask import redirect, render_template, request

from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import APP


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
    versioned = 'versioned' in request.args

    jobs = project.jobs

    if versioned:
        jobs = jobs.filter(
            Job.result == 'success',
            Job.tag is not None,
        )

    jobs = jobs.order_by(sqlalchemy.desc(Job.create_ts))
    jobs = jobs.paginate(page, page_size)

    return render_template(
        'project.html',
        project=project,
        jobs=jobs,
        versioned=versioned,
    )
