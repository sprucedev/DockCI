"""
Views related to job management
"""

import json
import logging
import rollbar

from flask import (abort,
                   render_template,
                   request,
                   Response,
                   send_file,
                   url_for,
                   )
from flask_security import current_user
from yaml_model import ValidationError

from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import APP, DB
from dockci.util import (is_valid_github,
                         parse_branch_from_ref,
                         parse_ref,
                         parse_tag_from_ref,
                         path_contained,
                         )


@APP.route('/projects/<project_slug>/jobs/<job_slug>', methods=('GET',))
def job_view(project_slug, job_slug):
    """
    View to display a job
    """
    Project.query.filter_by(slug=project_slug).first_or_404()  # ensure exist
    job = Job.query.get_or_404(Job.id_from_slug(job_slug))

    return render_template('job.html', job=job)


@APP.route('/projects/<project_slug>/jobs/new', methods=('POST',))
def job_new_view(project_slug):
    """
    View to create a new job
    """

    has_event_header = any((
        header in request.headers
        for header in (
            'X-Github-Event',
            'X-Gitlab-Event',
        )
    ))
    if not has_event_header:
        abort(400)

    project = Project.query.filter_by(slug=project_slug).first_or_404()
    job = Job(project=project, repo_fs=project.repo_fs)

    if 'X-Github-Event' in request.headers:
        job_new_github(project, job)
    elif 'X-Gitlab-Event' in request.headers:
        job_new_gitlab(project, job)

    try:
        DB.session.add(job)
        DB.session.commit()
        job.queue()

        job_url = url_for('job_view',
                          project_slug=project_slug,
                          job_slug=job.slug)
        return job_url, 201

    except ValidationError as ex:
        rollbar.report_exc_info()
        logging.exception("Event hook error")
        return json.dumps({
            'errors': ex.messages,
        }), 400


def job_new_abort(job, status, message=None):
    """ Log, expunge job, and HTTP error """
    if message is not None:
        logging.warn(message)
    DB.session.expunge(job)
    abort(status)


def job_new_gitlab(_, job):
    """
    Fill in the new ``job`` model from the request, which is a GitLab push
    event
    """
    if not current_user.is_authenticated():
        job_new_abort(job, 403, "No login information for GitLab hook")

    if request.headers['X-Gitlab-Event'] in ('Push Hook', 'Tag Push Hook'):
        push_data = request.json

        job.commit = push_data['after']

        if request.headers['X-Gitlab-Event'] == 'Push Hook':
            job.git_branch = parse_branch_from_ref(push_data['ref'])
        elif request.headers['X-Gitlab-Event'] == 'Tag Push Hook':
            job.tag = parse_tag_from_ref(push_data['ref'])

    else:
        job_new_abort(
            job,
            501,
            "Unknown GitLab hook '%s'" % request.headers['X-Gitlab-Event'],
        )


def job_new_github(project, job):
    """
    Fill in the new ``job`` model from the request, which is a GitHub push
    event
    """
    if not project.github_secret:
        job_new_abort(job, 403, "GitHub webhook secret not setup")

    if not is_valid_github(project.github_secret):
        job_new_abort(job, 403, "Invalid GitHub payload")

    if request.headers['X-Github-Event'] == 'push':
        push_data = request.json

        # GitHub pushes an empty head_commit when refs are deleted
        if push_data['head_commit'] is None:
            job_new_abort(job, 204)

        job.commit = push_data['head_commit']['id']

        ref_type, ref_name = parse_ref(push_data['ref'])
        if ref_type == 'branch':
            job.git_branch = ref_name
        elif ref_type == 'tag':
            job.tag = ref_name

    else:
        job_new_abort(
            job,
            501,
            "Unknown GitHub hook '%s'" % request.headers['X-Github-Event'],
        )


def check_output(project_slug, job_slug, filename):
    """ Ensure the job exists, and that the path is not dangerous """
    Project.query.filter_by(slug=project_slug).first_or_404()  # ensure exist
    job = Job.query.get_or_404(Job.id_from_slug(job_slug))

    job_output_path = job.job_output_path()
    data_file_path = job_output_path.join(filename)

    # Ensure no security issues opening path above our output dir
    if not path_contained(job_output_path, data_file_path):
        abort(404)

    if not data_file_path.check(file=True):
        abort(404)

    return data_file_path


@APP.route('/projects/<project_slug>/jobs/<job_slug>/log_init/<stage>',
           methods=('GET',))
def job_log_init_view(project_slug, job_slug, stage):
    """ View to download initial job log """
    data_file_path = check_output(project_slug, job_slug, '%s.log' % stage)
    byte_seek = request.args.get('seek', 0, type=int)
    bytes_count = request.args.get('count', None, type=int)

    def loader():
        """ Stream the parts of the log that we want """
        with data_file_path.open('rb') as handle:
            handle.seek(byte_seek)
            bytes_remain = bytes_count
            while bytes_remain is None or bytes_remain > 0:
                if bytes_remain is not None:
                    chunk_size = min(1024, bytes_remain)
                else:
                    chunk_size = 1024

                data = handle.read(chunk_size)

                if bytes_remain is not None:
                    bytes_remain -= len(data)

                yield data

                if len(data) == 0:
                    return

    return Response(loader(), mimetype='text/plain')


@APP.route('/projects/<project_slug>/jobs/<job_slug>/output/<filename>',
           methods=('GET',))
def job_output_view(project_slug, job_slug, filename):
    """ View to download some job output """
    data_file_path = check_output(project_slug, job_slug, filename)
    send_file(data_file_path.strpath)
