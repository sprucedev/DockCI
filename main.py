"""
DockCI - CI, but with that all important Docker twist
"""

import os
import re

from datetime import datetime
from uuid import uuid1, uuid4

from flask import flash, Flask, redirect, render_template, request

from yaml_model import LoadOnAccess, Model, OnAccess, SingletonModel


def is_yaml_file(filename):
    """
    Check if the filename provided points to a file, and ends in .yaml
    """
    return os.path.isfile(filename) and filename.endswith('.yaml')


def request_fill(model_obj, fill_atts, save=True):
    """
    Fill given model attrs from a POST request (and ignore other requests).
    Will save only if the save flag is True
    """
    if request.method == 'POST':
        for att in fill_atts:
            setattr(model_obj, att, request.form[att])

        if save:
            model_obj.save()
            flash(u"%s saved" % model_obj.__class__.__name__.title(),
                  'success')


class Job(Model):
    """
    A job, representing a container to be built
    """
    def __init__(self, slug=None):
        super(Job, self).__init__()
        self.slug = slug

    def _all_builds(self):
        """
        Get all the builds associated with this job
        """
        try:
            my_data_dir_path = Build.data_dir_path()
            my_data_dir_path.append(self.slug)
            builds = []

            for filename in os.listdir(os.path.join(*my_data_dir_path)):
                full_path = Build.data_dir_path() + [self.slug, filename]
                if is_yaml_file(os.path.join(*full_path)):
                    builds.append(Build(job=self,
                                        slug=filename[:-5]))

            return builds

        except FileNotFoundError:
            return []

    slug = None
    repo = LoadOnAccess()
    name = LoadOnAccess()
    builds = OnAccess(_all_builds)


class Build(Model):
    """
    An individual job build, and result
    """
    def __init__(self, job=None, slug=None):
        super(Build, self).__init__()

        assert job is not None, "Job is given"

        self.job = job
        self.job_slug = job.slug

        if slug:
            self.slug = slug

    slug = OnAccess(lambda _: str(uuid1()))
    job = OnAccess(lambda self: Job(self.job_slug))
    job_slug = OnAccess(lambda self: self.job.slug)  # TODO infinite loop
    create_ts = LoadOnAccess(generate=lambda _: datetime.now())
    start_ts = LoadOnAccess(default=lambda _: None)
    complete_ts = LoadOnAccess(default=lambda _: None)
    repo = LoadOnAccess(generate=lambda self: self.job.repo)
    commit = LoadOnAccess(default=lambda _: None)

    @property
    def state(self):
        """
        Current state that the build is in
        """
        if self.complete_ts is not None:
            return 'complete'
        elif self.start_ts is not None:
            return 'running'  # TODO check if running or dead
        else:
            return 'queued'  # TODO check if queued or queue fail

    def data_file_path(self):
        # Add the job name before the build slug in the path
        data_file_path = super(Build, self).data_file_path()
        data_file_path.insert(-1, self.job_slug)
        return data_file_path


class Config(SingletonModel):
    """
    Global application configuration
    """
    # TODO docker_hosts
    docker_host = LoadOnAccess(default=lambda _: 'unix:///var/run/docker.sock')
    secret = LoadOnAccess(generate=lambda _: uuid4().hex)


def all_jobs():
    """
    Get the list of jobs
    """
    try:
        for filename in os.listdir(os.path.join(*Job.data_dir_path())):
            full_path = Job.data_dir_path() + [filename]
            if is_yaml_file(os.path.join(*full_path)):
                job = Job(filename[:-5])
                yield job

    except FileNotFoundError:
        return


APP = Flask(__name__)
CONFIG = Config()


@APP.route('/')
def root_view():
    """
    View to display the list of all jobs
    """
    return render_template('index.html', jobs=list(all_jobs()))


@APP.route('/config', methods=('GET', 'POST'))
def config_edit_view():
    """
    View to edit global config
    """
    if 'secret' in request.form and request.form['secret'] != CONFIG.secret:
        flash(u"An application restart is required for some changes to take "
              "effect", 'warning')

    request_fill(CONFIG, ('docker_host', 'secret'))

    return render_template('config_edit.html', config=CONFIG)


@APP.route('/jobs/<slug>', methods=('GET', 'POST'))
def job_view(slug):
    """
    View to display a job
    """
    job = Job(slug)
    request_fill(job, ('name', 'repo'))

    return render_template('job.html', job=job)


@APP.route('/jobs/<slug>/edit', methods=('GET',))
def job_edit_view(slug):
    """
    View to edit a job
    """
    return render_template('job_edit.html', job=Job(slug))


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
        build.commit = request.form['commit']

        if not re.match(r'[a-fA-F0-9]{1,40}', request.form['commit']):
            flash(u"Invalid git commit hash", 'danger')
            return render_template('build_new.html', build=build)

        build.save()

        flash(u"Build queued", 'success')
        return redirect('/jobs/{job_slug}/builds/{build_slug}'.format(
            job_slug=job_slug,
            build_slug=build.slug,
        ), 303)

    return render_template('build_new.html', build=Build(job=job))


if __name__ == "__main__":
    APP.secret_key = CONFIG.secret
    APP.run(debug=True)
