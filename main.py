import os

from datetime import datetime
from uuid import uuid1

from flask import Flask, render_template, request

from yaml_model import Model, OnAccess, LoadOnAccess

app = Flask(__name__)

@app.route('/')
def root():
    return render_template('index.html', jobs=list(all_jobs()))


@app.route('/jobs/<slug>', methods=('GET', 'POST'))
def job(slug):
    job = Job(slug)

    if request.method == 'POST':
        for att in ('name', 'repo'):
            setattr(job, att, request.form[att])

        job.save()

    return render_template('job.html', job=job)


@app.route('/jobs/<slug>/edit', methods=('GET',))
def job_edit(slug):
    return render_template('job_edit.html', job=Job(slug))


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

        assert job is not None or slug is not None, \
            "One of slug, or job is given"

        if job:
            self.job = job
            self.job_slug = job.slug
        else:
            self.job_slug = None

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
    app.run(debug=True)
