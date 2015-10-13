"""
Views related to job management
"""

import json
import logging
import mimetypes
import select

from flask import (abort,
                   render_template,
                   request,
                   Response,
                   url_for,
                   )
from yaml_model import ValidationError

from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import APP, DB
from dockci.util import (DateTimeEncoder,
                         is_valid_github,
                         path_contained
                         )


@APP.route('/projects/<project_slug>/jobs/<job_slug>', methods=('GET',))
def job_view(project_slug, job_slug):
    """
    View to display a job
    """
    project = Project.query.filter_by(slug=project_slug).first_or_404()
    job = Job.query.get_or_404(Job.id_from_slug(job_slug))

    return render_template('job.html', job=job)


@APP.route('/projects/<project_slug>/jobs/new', methods=('POST',))
def job_new_view(project_slug):
    """
    View to create a new job
    """
    if 'X-Github-Event' not in request.headers:
        abort(400)

    project = Project.query.filter_by(slug=project_slug).first_or_404()
    job = Job(project=project, repo=project.repo)

    if not project.github_secret:
        logging.warn("GitHub webhook secret not setup")
        abort(403)

    if not is_valid_github(project.github_secret):
        logging.warn("Invalid GitHub payload")
        abort(403)

    if request.headers['X-Github-Event'] == 'push':
        push_data = request.json
        job.commit = push_data['head_commit']['id']

    else:
        logging.debug("Unknown GitHub hook '%s'",
                      request.headers['X-Github-Event'])
        abort(501)

    try:
        DB.session.add(job)
        DB.session.commit()
        job.queue()

        job_url = url_for('job_view',
                          project_slug=project_slug,
                          job_slug=job.slug)
        return job_url, 201

    except ValidationError as ex:
        logging.exception("GitHub hook error")
        return json.dumps({
            'errors': ex.messages,
        }), 400

    return render_template('job_new.html', job=Job(
        project=project,
        repo=project.repo,
    ))


@APP.route('/projects/<project_slug>/jobs/<job_slug>.json',
           methods=('GET',))
def job_output_json(project_slug, job_slug):
    """
    View to download some job info in JSON
    """
    project = Project.query.filter_by(slug=project_slug).first_or_404()
    job = Job.query.get_or_404(Job.id_from_slug(job_slug))

    # TODO flask-restful
    return Response(
        json.dumps(
            dict(
                tuple((key, getattr(job, key)) for key in (
                    'id', 'slug',
                    'create_ts', 'start_ts', 'complete_ts',
                    'result', 'repo', 'commit', 'tag',
                    'image_id', 'container_id', 'docker_client_host',
                    'exit_code',
                    'git_author_name', 'git_author_email',
                    'git_committer_name', 'git_committer_email',
                    'git_changes',
                )) + (
                    ('project_slug', project.slug),
                    ('job_stage_slugs', [stage.slug for stage in job.job_stages]),
                )
            ),
            cls=DateTimeEncoder,
        ),
        mimetype='application/json',
    )


@APP.route('/projects/<project_slug>/jobs/<job_slug>/output/<filename>',
           methods=('GET',))
def job_output_view(project_slug, job_slug, filename):
    """
    View to download some job output
    """
    project = Project.query.filter_by(slug=project_slug).first_or_404()
    job = Job.query.get_or_404(Job.id_from_slug(job_slug))
    job_id = job.id

    job_output_path = job.job_output_path()
    data_file_path = job_output_path.join(filename)

    # Ensure no security issues opening path above our output dir
    if not path_contained(job_output_path, data_file_path):
        abort(404)

    if not data_file_path.check(file=True):
        abort(404)

    def loader():
        """
        Generator to stream the log file
        """
        with APP.app_context():
            job = Job.query.get(job_id)  # Session is closed
            with data_file_path.open('rb') as handle:
                while True:
                    data = handle.read(1024)
                    yield data

                    DB.session.refresh(job)
                    is_live_log = (
                        job.state == 'running' and
                        filename == "%s.log" % job.job_stages[-1].slug
                    )
                    if is_live_log:
                        select.select((handle,), (), (), 2)

                    elif len(data) == 0:
                        return

    mimetype, _ = mimetypes.guess_type(filename)
    if mimetype is None:
        mimetype = 'application/octet-stream'

    return Response(loader(), mimetype=mimetype)
