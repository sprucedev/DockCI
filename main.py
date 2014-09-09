import os
import re

from datetime import datetime
from uuid import uuid1

from flask import flash, Flask, redirect, render_template, request

from yaml_model import LoadOnAccess, Model, OnAccess, SingletonModel

app = Flask(__name__)


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


@app.route('/')
def root():
    return render_template('index.html', jobs=list(all_jobs()))


@app.route('/config', methods=('GET', 'POST'))
def config():
    config = Config()
    request_fill(config, ('docker_host', 'secret'))

    if 'secret' in request.form:
        flash(u"An application restart is required for some changes to take effect",
              'warning')

    return render_template('config.html', config=config)


@app.route('/jobs/<slug>', methods=('GET', 'POST'))
def job(slug):
    job = Job(slug)
    request_fill(job, ('name', 'repo'))

    return render_template('job.html', job=job)


@app.route('/jobs/<slug>/edit', methods=('GET',))
def job_edit(slug):
    return render_template('job_edit.html', job=Job(slug))


@app.route('/jobs/<job_slug>/builds/<build_slug>', methods=('GET',))
def build(job_slug, build_slug):
    job = Job(slug=job_slug)
    build = Build(job=job, slug=build_slug)

    return render_template('build.html', build=build)

@app.route('/jobs/<job_slug>/builds/new', methods=('GET', 'POST'))
def build_new(job_slug):
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


def is_yaml_file(filename):
    return os.path.isfile(filename) and filename.endswith('.yaml')


class Job(Model):
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

            for fn in os.listdir(os.path.join(*my_data_dir_path)):
                full_path = Build.data_dir_path() + [self.slug, fn]
                if is_yaml_file(os.path.join(*full_path)):
                    builds.append(Build(job=self,
                                        slug=fn[:-5]))

            return builds

        except FileNotFoundError:
            return []

    repo = LoadOnAccess()
    name = LoadOnAccess()
    builds = OnAccess(_all_builds)


class Build(Model):
    def __init__(self, job=None, slug=None):
        super(Build, self).__init__()

        assert job is not None, \
            "Job is given"

        self.job = job
        self.job_slug = job.slug

        if slug:
            self.slug = slug

    slug = OnAccess(lambda _: str(uuid1()))
    job = OnAccess(lambda self: Job(self.job_slug))
    job_slug = OnAccess(lambda self: self.job.slug)  # TODO infinite loop
    timestamp = LoadOnAccess(generate=lambda _: datetime.now())
    repo = LoadOnAccess(generate=lambda self: self.job.repo)
    commit = LoadOnAccess(default=lambda _: None)

    def data_file_path(self):
        # Add the job name before the build slug in the path
        data_file_path = super(Build, self).data_file_path()
        data_file_path.insert(-1, self.job_slug)
        return data_file_path


class Config(SingletonModel):
    # TODO docker_hosts
    docker_host = LoadOnAccess(default=lambda _: 'unix:///var/run/docker.sock')
    secret = LoadOnAccess(generate=lambda _: os.random(24))


def all_jobs():
    """
    Get the list of jobs
    """
    try:
        for fn in os.listdir(os.path.join(*Job.data_dir_path())):
            full_path = Job.data_dir_path() + [fn]
            if is_yaml_file(os.path.join(*full_path)):
                job = Job(fn[:-5])
                yield job

    except FileNotFoundError:
        return


if __name__ == "__main__":
    config = Config()
    app.secret_key = config.secret
    app.run(debug=True)
