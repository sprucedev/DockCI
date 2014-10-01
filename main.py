"""
DockCI - CI, but with that all important Docker twist
"""

import json
import multiprocessing.pool
import os
import re
import subprocess
import tempfile

from datetime import datetime
from uuid import uuid1, uuid4

import docker

from flask import flash, Flask, redirect, render_template, request, Response

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


class InvalidOperationError(Exception):
    """
    Raised when a call is not valid at the current time
    """
    pass


class AlreadyRunError(InvalidOperationError):
    """
    Raised when a build or stage is attempted to be run that has already been
    started/completed
    """
    runnable = None

    def __init__(self, runnable):
        super(AlreadyRunError, self).__init__()
        self.runnable = runnable


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
    repo = LoadOnAccess(default=lambda _: '')
    name = LoadOnAccess(default=lambda _: '')
    builds = OnAccess(_all_builds)


class BuildStage(object):
    """
    A logged stage to a build
    """
    returncode = None

    def __init__(self, slug, build, runnable=None):
        self.slug = slug
        self.build = build
        self.runnable = runnable

    def data_dir_path(self):
        """
        Directory that the stage stores data in
        """
        return self.build.data_file_path()[:-1] + [
            '%s_output' % self.build.slug,
        ]

    def data_file_path(self):
        """
        File that stage output is logged to
        """
        return self.data_dir_path() + [self.slug]

    def run(self):
        """
        Start the child process, streaming it's output to the associated file,
        and block until it returns
        """
        if self.returncode is not None:
            raise AlreadyRunError(self)

        data_dir_path = os.path.join(*self.data_dir_path())
        data_file_path = os.path.join(*self.data_file_path())

        os.makedirs(data_dir_path, exist_ok=True)
        with open(data_file_path, 'wb') as handle:
            self.returncode = self.runnable(handle)

    @classmethod
    def from_command(cls, slug, build, cwd, cmd_args):
        """
        Create a BuildStage object from a system command
        """
        def runnable(handle):
            """
            Run a process, streaming to the given handle and wait for it to
            exit before returning it's exit code
            """
            # TODO escape args
            handle.write(bytes(">CWD %s\n" % cwd, 'utf8'))
            handle.write(bytes(">>>> %s\n" % cmd_args, 'utf8'))
            proc = subprocess.Popen(cmd_args,
                                    cwd=cwd,
                                    stdout=handle,
                                    stderr=subprocess.STDOUT)
            proc.wait()
            return proc.returncode

        return cls(slug=slug, build=build, runnable=runnable)


class Build(Model):  # pylint:disable=too-many-instance-attributes
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
    result = LoadOnAccess(default=lambda _: None)
    repo = LoadOnAccess(generate=lambda self: self.job.repo)
    commit = LoadOnAccess(default=lambda _: None)
    version = LoadOnAccess(default=lambda _: None)
    image_id = LoadOnAccess(default=lambda _: None)
    build_stage_slugs = LoadOnAccess(default=lambda _: [])
    build_stages = OnAccess(lambda self: [
        BuildStage(slug=slug, build=self)
        for slug
        in self.build_stage_slugs
    ])

    @property
    def state(self):
        """
        Current state that the build is in
        """
        if self.result is not None:
            return self.result
        elif self.start_ts is not None:
            return 'running'  # TODO check if running or dead
        else:
            return 'queued'  # TODO check if queued or queue fail

    _docker_client = None

    @property
    def docker_client(self):
        """
        Get the cached (or new) Docker Client object being used for this build
        """
        if not self._docker_client:
            self._docker_client = docker.Client(base_url=CONFIG.docker_host)

        return self._docker_client

    def data_file_path(self):
        # Add the job name before the build slug in the path
        data_file_path = super(Build, self).data_file_path()
        data_file_path.insert(-1, self.job_slug)
        return data_file_path

    def queue(self):
        """
        Add the build to the queue
        """
        if self.start_ts:
            raise AlreadyRunError(self)

        APP.workers.apply_async(self._run_now)

    def _run_now(self):
        """
        Worker func that performs the build
        """
        self.start_ts = datetime.now()
        self.save()

        try:
            with tempfile.TemporaryDirectory() as workdir:
                pre_build = (stage() for stage in (
                    lambda: self._run_prep_workdir(workdir),
                    lambda: self._run_tag_version(workdir),
                    lambda: self._run_build(workdir),
                ))
                if not all(pre_build):
                    self.result = 'error'
                    return False

            self.result = 'success'
            return True
        except Exception:  # pylint:disable=broad-except
            self.result = 'error'

            self.build_stage_slugs.append('error')  # pylint:disable=no-member
            self.save()

            import traceback
            try:
                BuildStage(
                    'error',
                    self,
                    lambda handle: handle.write(
                        bytes(traceback.format_exc(), 'utf8')
                    )
                ).run()
            except Exception:  # pylint:disable=broad-except
                print(traceback.format_exc())

            return False

        finally:
            self.complete_ts = datetime.now()
            self.save()

    def _run_prep_workdir(self, workdir):
        """
        Clone and checkout the build
        """
        to_run = (stage() for stage in (
            lambda: self._stage(
                'git_clone', workdir=workdir,
                cmd_args=['git', 'clone', self.repo, workdir]
            ),
            lambda: self._stage(
                'git_checkout', workdir=workdir,
                cmd_args=['git', 'checkout', self.commit]
            ),
        ))
        result = all((stage.returncode == 0 for stage in to_run))

        return result

    def _run_tag_version(self, workdir):
        """
        Try and add a version to the build, based on git tag
        """
        stage = self._stage(
            'git_tag', workdir=workdir,
            cmd_args=['git', 'describe', '--tags']
        )
        if not stage.returncode == 0:
            # TODO remove spoofed return
            return True  # stage result is irrelevant

        try:
            # TODO opening file to get this is kinda awful
            data_file_path = os.path.join(*stage.data_file_path())
            with open(data_file_path, 'r') as handle:
                line = handle.readline().strip()
                # TODO be more generic! GOSH
                if re.match(r'^v\d+\.\d+\.\d+$', line):
                    self.version = line
                    self.save()
                    return True

        except KeyError:
            # TODO remove spoofed return
            return True  # stage result is irrelevant

    def _run_build(self, workdir):
        """
        Tell the Docker host to build
        """
        def runnable(handle):
            """
            Tell the Docker host to build, streaming its output to file and
            parsing to see if the container was build Successfully
            """
            # saved stream for debugging
            # output = open('docker_build_stream', 'r')
            output = self.docker_client.build(path=workdir, stream=True)

            line = None
            for line in output:
                handle.write(bytes(line, 'utf8'))
                handle.flush()

            if line:
                line_data = json.loads(line)
                re_match = re.search(r'Successfully built ([0-9a-f]+)',
                                     line_data.get('stream', ''))
                if re_match:
                    self.image_id = re_match.group(1)
                    return True

            return False

        return self._stage('docker_build', runnable=runnable).returncode

    def _stage(self, stage_slug, runnable=None, workdir=None, cmd_args=None):
        """
        Create and save a new build stage, running the given args and saving
        its output
        """
        if cmd_args:
            stage = BuildStage.from_command(slug=stage_slug,
                                            build=self,
                                            cwd=workdir,
                                            cmd_args=cmd_args)
        else:
            stage = BuildStage(slug=stage_slug, build=self, runnable=runnable)

        self.build_stage_slugs.append(stage_slug)  # pylint:disable=no-member
        self.save()
        stage.run()
        return stage


class Config(SingletonModel):
    """
    Global application configuration
    """
    restart_needed = False

    # TODO docker_hosts
    docker_host = LoadOnAccess(default=lambda _: 'unix:///var/run/docker.sock')
    secret = LoadOnAccess(generate=lambda _: uuid4().hex)
    workers = LoadOnAccess(default=lambda _: 5)


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


APP.config.model = CONFIG  # For templates


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
    restart_needed = any((
        attr in request.form and request.form[attr] != getattr(CONFIG, attr)
        for attr in ('docker_host', 'secret', 'workers')
    ))
    if restart_needed:
        CONFIG.restart_needed = True
        flash(u"An application restart is required for some changes to take "
              "effect", 'warning')

    request_fill(CONFIG, ('docker_host', 'secret', 'workers'))

    return render_template('config_edit.html')


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
    return render_template('job_edit.html',
                           job=Job(slug),
                           edit_operation='edit')


@APP.route('/jobs/new', methods=('GET', 'POST'))
def job_new_view():
    """
    View to make a new job
    """
    job = Job()
    if request.method == 'POST':
        request_fill(job, ('slug', 'name', 'repo'))
        return redirect('/jobs/{job_slug}'.format(job_slug=job.slug))
    return render_template('job_edit.html', job=job, edit_operation='new')


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
        build.queue()

        flash(u"Build queued", 'success')
        return redirect('/jobs/{job_slug}/builds/{build_slug}'.format(
            job_slug=job_slug,
            build_slug=build.slug,
        ), 303)

    return render_template('build_new.html', build=Build(job=job))


@APP.route('/jobs/<job_slug>/builds/<build_slug>/stage_logs/<stage_slug>',
           methods=('GET',))
def stage_log_view(job_slug, build_slug, stage_slug):
    """
    View to display a build
    """
    job = Job(slug=job_slug)
    build = Build(job=job, slug=build_slug)
    stage = BuildStage(build=build, slug=stage_slug)

    def loader():
        """
        Generator to stream the log file
        """
        # TODO possible security issue opending files from user input like this
        data_file_path = os.path.join(*stage.data_file_path())
        with open(data_file_path, 'r') as handle:
            while True:
                data = handle.read(1024)
                yield data
                if data == '':
                    return

    return Response(loader(), mimetype='text/plain')


def app_setup_extra():
    """
    Pre-run app setup
    """
    APP.secret_key = CONFIG.secret
    APP.workers = multiprocessing.pool.Pool(int(CONFIG.workers))


if __name__ == "__main__":
    app_setup_extra()
    APP.run(debug=True)
