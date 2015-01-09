"""
Views related to build management
"""

import logging
import mimetypes
import os.path
import re
import json

from flask import (abort,
                   flash,
                   redirect,
                   render_template,
                   request,
                   Response,
                   url_for,
                   )

from dockci.models.build import Build
from dockci.models.job import Job
from dockci.server import APP
from dockci.util import is_valid_github, DateTimeEncoder


@APP.route('/jobs/<job_slug>/builds/<build_slug>', methods=('GET',))
def build_view(job_slug, build_slug):
    """
    View to display a build
    """
    job = Job(slug=job_slug)
    build = Build(job=job, slug=build_slug)

    return render_template('build.html', build=build)


@APP.route('/jobs/<job_slug>/builds/new', methods=('GET', 'POST'))
def build_new_view(job_slug):
    """
    View to create a new build
    """
    job = Job(slug=job_slug)

    if request.method == 'POST':
        build = Build(job=job)
        build.repo = job.repo

        build_url = url_for('build_view',
                            job_slug=job_slug,
                            build_slug=build.slug)

        if 'X-Github-Event' in request.headers:
            if not job.github_secret:
                logging.warn("GitHub webhook secret not setup")
                abort(403)

            if not is_valid_github(job.github_secret):
                logging.warn("Invalid GitHub payload")
                abort(403)

            if request.headers['X-Github-Event'] == 'push':
                push_data = request.json
                build.commit = push_data['head_commit']['id']

            else:
                logging.debug("Unknown GitHub hook '%s'",
                              request.headers['X-Github-Event'])
                abort(501)

            build.save()
            build.queue()

            return build_url, 201

        else:
            build.commit = request.form['commit']

            if not re.match(r'[a-fA-F0-9]{1,40}', request.form['commit']):
                flash(u"Invalid git commit hash", 'danger')
                return render_template('build_new.html', build=build)

            build.save()
            build.queue()

            flash(u"Build queued", 'success')
            return redirect(build_url, 303)

    return render_template('build_new.html', build=Build(job=job))

@APP.route('/jobs/<job_slug>/builds/<build_slug>.json', methods=('GET',))
def build_output_json(job_slug, build_slug):
    """
    View to download some build info in JSON
    """
    job = Job(slug=job_slug)
    build = Build(job=job, slug=build_slug)

    print(build.as_dict())

    return Response(json.dumps(build.as_dict(), cls=DateTimeEncoder), mimetype='application/json')


@APP.route('/jobs/<job_slug>/builds/<build_slug>/output/<filename>',
           methods=('GET',))
def build_output_view(job_slug, build_slug, filename):
    """
    View to download some build output
    """
    job = Job(slug=job_slug)
    build = Build(job=job, slug=build_slug)

    # TODO possible security issue opending files from user input like this
    data_file_path = os.path.join(*build.build_output_path() + [filename])
    if not os.path.isfile(data_file_path):
        abort(404)

    def loader():
        """
        Generator to stream the log file
        """
        with open(data_file_path, 'rb') as handle:
            while True:
                data = handle.read(1024)
                yield data
                if len(data) == 0:
                    return

    mimetype, _ = mimetypes.guess_type(filename)
    if mimetype is None:
        mimetype = 'application/octet-stream'

    return Response(loader(), mimetype=mimetype)
