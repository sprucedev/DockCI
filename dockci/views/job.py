"""
Views related to job management
"""

from flask import abort, redirect, render_template, request

from dockci.models.job import Job
from dockci.server import APP
from dockci.util import request_fill


@APP.route('/jobs/<slug>', methods=('GET', 'POST'))
def job_view(slug):
    """
    View to display a job
    """
    job = Job(slug)
    if not job.exists():
        abort(404)

    request_fill(job, ('name', 'repo', 'github_secret',
                       'hipchat_api_token', 'hipchat_room'))

    return render_template('job.html', job=job)


@APP.route('/jobs/<slug>/edit', methods=('GET',))
def job_edit_view(slug):
    """
    View to edit a job
    """
    job = Job(slug)
    if not job.exists():
        abort(404)

    return render_template('job_edit.html',
                           job=job,
                           edit_operation='edit')


@APP.route('/jobs/new', methods=('GET', 'POST'))
def job_new_view():
    """
    View to make a new job
    """
    job = Job()
    if request.method == 'POST':
        saved = request_fill(job, ('slug', 'name', 'repo',
                                   'hipchat_api_token', 'hipchat_room'))
        if saved:
            return redirect('/jobs/{job_slug}'.format(job_slug=job.slug))

    return render_template('job_edit.html', job=job, edit_operation='new')
