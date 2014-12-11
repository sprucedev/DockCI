# pylint:disable=too-many-lines
# TODO ^^^ this is bad mmkay
"""
DockCI - CI, but with that all important Docker twist
"""

import hashlib
import hmac
import json
import logging
import mimetypes
import multiprocessing
import multiprocessing.pool
import os
import os.path
import re
import socket
import struct
import subprocess
import sys
import tempfile

from contextlib import contextmanager
from datetime import datetime
from ipaddress import ip_address
from urllib.parse import urlparse
from uuid import uuid1, uuid4

import docker

from flask import (abort,
                   flash,
                   Flask,
                   redirect,
                   render_template,
                   request,
                   Response,
                   url_for,
                   )
from flask_mail import Mail, Message

from dockci.yaml_model import LoadOnAccess, Model, OnAccess, SingletonModel


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
            if att in request.form:
                setattr(model_obj, att, request.form[att])

        if save:
            model_obj.save()
            flash(u"%s saved" % model_obj.__class__.__name__.title(),
                  'success')


def default_gateway():
    """
    Gets the IP address of the default gateway
    """
    with open('/proc/net/route') as handle:
        for line in handle:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue

            return ip_address(socket.inet_ntoa(
                struct.pack("<L", int(fields[2], 16))
            ))


def bytes_human_readable(num, suffix='B'):
    """
    Gets byte size in human readable format
    """
    for unit in ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'):
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1000.0

    return "%.1f%s%s" % (num, 'Y', suffix)


def is_valid_github(secret):
    """
    Validates a GitHub hook payload
    """
    if 'X-Hub-Signature' not in request.headers:
        return False

    hash_type, signature = request.headers['X-Hub-Signature'].split('=')
    if hash_type.lower() != 'sha1':
        logging.warn("Unknown GitHub hash type: '%s'", hash_type)
        return False

    computed_signature = hmac.new(secret.encode(),
                                  request.data,
                                  hashlib.sha1).hexdigest()

    return signature == computed_signature


def _run_build_worker(job_slug, build_slug):
    """
    Load and run a build's private run job. Used to trigger builds inside
    worker threads so that data is pickled correctly
    """
    try:
        with APP.app_context():
            job = Job(job_slug)
            build = Build(job=job, slug=build_slug)
            build_okay = build._run_now()  # pylint:disable=protected-access

            # Send the failure message
            if not build_okay:
                recipients = []
                if build.git_author_email:
                    recipients.append('%s <%s>' % (
                        build.git_author_name,
                        build.git_author_email
                    ))
                if build.git_committer_email:
                    recipients.append('%s <%s>' % (
                        build.git_committer_name,
                        build.git_committer_email
                    ))

                if recipients:
                    email = Message(
                        recipients=recipients,
                        subject="DockCI - {job_name} {build_result}ed".format(
                            job_name=job.name,
                            build_result=build.result,
                        ),
                    )
                    MAIL_QUEUE.put_nowait(email)

    except Exception:  # pylint:disable=broad-except
        logging.exception("Something went wrong in the build worker")


@contextmanager
def stream_write_status(handle, status, success, fail):
    """
    Context manager to write a status, followed by success message, or fail
    message if yield raises an exception
    """
    handle.write(status.encode())
    try:
        yield
        handle.write((" %s\n" % success).encode())
    except Exception:  # pylint:disable=broad-except
        handle.write((" %s\n" % fail).encode())
        raise


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
    github_secret = LoadOnAccess(default=lambda _: None)
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

    def data_file_path(self):
        """
        File that stage output is logged to
        """
        return self.build.build_output_path() + ['%s.log' % self.slug]

    def run(self):
        """
        Start the child process, streaming it's output to the associated file,
        and block until it returns
        """
        if self.returncode is not None:
            raise AlreadyRunError(self)

        data_dir_path = os.path.join(*self.build.build_output_path())
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
            Synchronously run one or more processes, streaming to the given
            handle, stopping and returning the exit code if it's non-zero.

            Returns 0 if all processes exit 0
            """
            def run_one_cmd(cmd_args_single):
                """
                Run a process
                """
                # TODO escape args
                handle.write(bytes(">CWD %s\n" % cwd, 'utf8'))
                handle.write(bytes(">>>> %s\n" % cmd_args_single, 'utf8'))
                proc = subprocess.Popen(cmd_args_single,
                                        cwd=cwd,
                                        stdout=handle,
                                        stderr=subprocess.STDOUT)
                proc.wait()
                return proc.returncode

            if isinstance(cmd_args[0], (tuple, list)):
                for cmd_args_single in cmd_args:
                    returncode = run_one_cmd(cmd_args_single)
                    if returncode != 0:
                        return returncode

                return 0

            else:
                return run_one_cmd(cmd_args)

        assert len(cmd_args) > 0, "cmd_args are given"
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
    container_id = LoadOnAccess(default=lambda _: None)
    exit_code = LoadOnAccess(default=lambda _: None)
    build_stage_slugs = LoadOnAccess(default=lambda _: [])
    build_stages = OnAccess(lambda self: [
        BuildStage(slug=slug, build=self)
        for slug
        in self.build_stage_slugs
    ])
    git_author_name = LoadOnAccess(default=lambda _: None)
    git_author_email = LoadOnAccess(default=lambda _: None)
    git_committer_name = LoadOnAccess(default=lambda self:
                                      self.git_author_name)
    git_committer_email = LoadOnAccess(default=lambda self:
                                       self.git_author_email)
    # pylint:disable=unnecessary-lambda
    build_config = OnAccess(lambda self: BuildConfig(self))

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

    @property
    def build_output_details(self):
        """
        Details for build output artifacts
        """
        # pylint:disable=no-member
        output_files = (
            (name, os.path.join(*self.build_output_path() + ['%s.tar' % name]))
            for name in self.build_config.build_output.keys()
        )
        return {
            name: {'size': bytes_human_readable(os.path.getsize(path)),
                   'link': url_for('build_output_view',
                                   job_slug=self.job_slug,
                                   build_slug=self.slug,
                                   filename='%s.tar' % name,
                                   ),
                   }
            for name, path in output_files
            if os.path.isfile(path)
        }

    def data_file_path(self):
        # Add the job name before the build slug in the path
        data_file_path = super(Build, self).data_file_path()
        data_file_path.insert(-1, self.job_slug)
        return data_file_path

    def build_output_path(self):
        """
        Directory for any build output data
        """
        return self.data_file_path()[:-1] + ['%s_output' % self.slug]

    def queue(self):
        """
        Add the build to the queue
        """
        if self.start_ts:
            raise AlreadyRunError(self)

        APP.workers.apply_async(_run_build_worker, (self.job_slug, self.slug))

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
                    lambda: self._run_git_info(workdir),
                    lambda: self._run_tag_version(workdir),
                    lambda: self._run_build(workdir),
                ))
                if not all(pre_build):
                    self.result = 'error'
                    return False

                if not self._run_test():
                    self.result = 'fail'
                    return False

                self.result = 'success'
                self.save()

                # Failing this doesn't indicade build failure
                # TODO what kind of a failure would this not working be?
                self._run_fetch_output()

            return True
        except Exception:  # pylint:disable=broad-except
            self.result = 'error'
            self._error_stage('error')

            return False

        finally:
            try:
                self._run_cleanup()

            except Exception:  # pylint:disable=broad-except
                self._error_stage('cleanup_error')

            self.complete_ts = datetime.now()
            self.save()

    def _run_prep_workdir(self, workdir):
        """
        Clone and checkout the build
        """
        stage = self._stage(
            'git_prepare', workdir=workdir,
            cmd_args=(['git', 'clone', self.repo, workdir],
                      ['git', 'checkout', self.commit],
                      )
        )
        result = stage.returncode == 0

        # check for, and load build config
        build_config_file = os.path.join(workdir, BuildConfig.slug)
        if os.path.isfile(build_config_file):
            # pylint:disable=no-member
            self.build_config.load(data_file=build_config_file)
            self.build_config.save()

        return result

    def _run_git_info(self, workdir):
        """
        Get info about the current commit from git
        """

        def runnable(handle):
            """
            Execute git to retrieve info
            """
            def run_proc(*args):
                """
                Run, and wait for a process with default args
                """
                proc = subprocess.Popen(args,
                                        stdout=subprocess.PIPE,
                                        stderr=handle,
                                        cwd=workdir,
                                        )
                proc.wait()
                return proc

            largest_returncode = 0
            properties_empty = True

            properties = {
                'Author name': ('git_author_name', '%an'),
                'Author email': ('git_author_email', '%ae'),
                'Committer name': ('git_committer_name', '%cn'),
                'Committer email': ('git_committer_email', '%ce'),
            }
            for display_name, (attr_name, format_string) in properties.items():
                proc = run_proc('git', 'show',
                                '-s',
                                '--format=format:%s' % format_string,
                                'HEAD')

                largest_returncode = max(largest_returncode, proc.returncode)
                value = proc.stdout.read().decode().strip()

                if value != '' and proc.returncode == 0:
                    setattr(self, attr_name, value)
                    properties_empty = False
                    handle.write((
                        "%s is %s\n" % (display_name, value)
                    ).encode())

            if properties_empty:
                handle.write("No information about the git commit could be "
                             "derived\n".encode())

            else:
                self.save()

            return proc.returncode

        stage = self._stage('git_info', workdir=workdir, runnable=runnable)
        return stage.returncode == 0

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
        def on_done(line):
            """
            Check the final line for success, and image id
            """
            if line:
                line_data = json.loads(line)
                re_match = re.search(r'Successfully built ([0-9a-f]+)',
                                     line_data.get('stream', ''))
                if re_match:
                    self.image_id = re_match.group(1)
                    return True

            return False

        return self._run_docker(
            'build',
            # saved stream for debugging
            # lambda: open('docker_build_stream', 'r'),
            lambda: self.docker_client.build(path=workdir,
                                             rm=True,
                                             stream=True),
            on_done=on_done,
        )

    def _run_test(self):
        """
        Tell the Docker host to run the CI command
        """
        def start_container():
            """
            Create a container instance, attache to its outputs and then start
            it, returning the output stream
            """
            container_details = self.docker_client.create_container(
                self.image_id, 'ci'
            )
            self.container_id = container_details['Id']
            self.save()

            stream = self.docker_client.attach(self.container_id, stream=True)
            self.docker_client.start(self.container_id)

            return stream

        def on_done(_):
            """
            Check container exit code and return True on 0, or False otherwise
            """
            details = self.docker_client.inspect_container(self.container_id)
            self.exit_code = details['State']['ExitCode']
            self.save()
            return self.exit_code == 0

        return self._run_docker(
            'test',
            start_container,
            on_done=on_done,
        )

    def _run_docker(self,
                    docker_stage_slug,
                    docker_command,
                    on_line=None,
                    on_done=None):
        """
        Wrapper around common Docker command process. Will send output lines to
        file, and optionally use callbacks to notify on each line, and
        completion
        """
        def runnable(handle):
            """
            Perform the Docker command given
            """
            output = docker_command()

            line = ''
            for line in output:
                if isinstance(line, bytes):
                    handle.write(line)
                else:
                    handle.write(line.encode())

                handle.flush()

                if on_line:
                    on_line(line)

            if on_done:
                return on_done(line)

            elif line:
                return True

            return False

        return self._stage('docker_%s' % docker_stage_slug,
                           runnable=runnable).returncode

    def _run_fetch_output(self):
        """
        Fetches any output specified in build config
        """

        def runnable(handle):
            """
            Fetch/save the files
            """
            # pylint:disable=no-member
            mappings = self.build_config.build_output.items()
            for key, docker_fn in mappings:
                handle.write(
                    ("Fetching %s from '%s'..." % (key, docker_fn)).encode()
                )
                resp = self.docker_client.copy(self.container_id, docker_fn)

                if 200 <= resp.status < 300:
                    output_path = os.path.join(
                        *self.build_output_path() + ['%s.tar' % key]
                    )
                    with open(output_path, 'wb') as output_fh:
                        bytes_written = output_fh.write(resp.data)

                    handle.write(
                        (" DONE! %s total\n" % (
                            bytes_human_readable(bytes_written)
                        )).encode(),
                    )

                else:
                    handle.write(
                        (" FAIL! HTTP status %d: %s\n" % (
                            resp.status_code, resp.reason
                        )).encode(),
                    )

            # Output something on no output
            if not mappings:
                handle.write("No output files to fetch".encode())

        return self._stage('docker_fetch', runnable=runnable).returncode

    def _run_cleanup(self):
        """
        Clean up after the build/test
        """
        def cleanup_context(handle, object_type, object_id):
            """
            Get a stream_write_status context manager with messages set
            correctly
            """
            return stream_write_status(
                handle,
                "Cleaning up %s '%s'..." % (object_type, object_id),
                "DONE!",
                "FAILED!",
            )

        def runnable(handle):
            """
            Do the image/container cleanup
            """
            if self.container_id:
                with cleanup_context(handle, 'container', self.container_id):
                    self.docker_client.remove_container(self.container_id)

            if self.image_id:
                with cleanup_context(handle, 'image', self.image_id):
                    self.docker_client.remove_image(self.image_id)

        return self._stage('cleanup', runnable)

    def _error_stage(self, stage_slug):
        """
        Create an error stage and add stack trace for it
        """
        self.build_stage_slugs.append(stage_slug)  # pylint:disable=no-member
        self.save()

        import traceback
        try:
            BuildStage(
                stage_slug,
                self,
                lambda handle: handle.write(
                    bytes(traceback.format_exc(), 'utf8')
                )
            ).run()
        except Exception:  # pylint:disable=broad-except
            print(traceback.format_exc())

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


class BuildConfig(Model):
    """
    Build config, loaded from the repo
    """

    slug = 'dockci.yaml'

    build = OnAccess(lambda self: Build(self.build_slug))
    build_slug = OnAccess(lambda self: self.build.slug)  # TODO infinite loop

    build_output = LoadOnAccess(default=lambda _: {})

    def __init__(self, build):
        super(BuildConfig, self).__init__()

        assert build is not None, "Build is given"

        self.build = build
        self.build_slug = build.slug

    def data_file_path(self):
        # Our data file path is <build output>/<slug>
        return self.build.build_output_path() + [BuildConfig.slug]


class Config(SingletonModel):
    """
    Global application configuration
    """
    restart_needed = False

    # TODO docker_hosts
    docker_host = LoadOnAccess(default=lambda _: Config.default_docker_host())
    secret = LoadOnAccess(generate=lambda _: uuid4().hex)
    workers = LoadOnAccess(default=lambda _: 5)

    mail_server = LoadOnAccess(default=lambda _: "localhost")
    mail_port = LoadOnAccess(default=lambda _: 25, input_transform=int)
    mail_use_tls = LoadOnAccess(default=lambda _: False, input_transform=bool)
    mail_use_ssl = LoadOnAccess(default=lambda _: False, input_transform=bool)
    mail_username = LoadOnAccess(default=lambda _: None)
    mail_password = LoadOnAccess(default=lambda _: None)
    mail_default_sender = LoadOnAccess(default=lambda _:
                                       "dockci@%s" % socket.gethostname())

    @property
    def mail_host_string(self):
        """
        Get the host/port as a h:p string
        """
        return "{host}:{port}".format(host=self.mail_server,
                                      port=self.mail_port)

    @mail_host_string.setter
    def mail_host_string(self, value):
        """
        Parse a URL string into host/port/user/pass and set the relevant attrs
        """
        url = urlparse('smtp://%s' % value)
        if url.hostname:
            self.mail_server = url.hostname
        if url.port:
            self.mail_port = url.port
        if url.username:
            self.mail_username = url.username
        if url.password:
            self.mail_password = url.password

    @classmethod
    def default_docker_host(cls):
        """
        Get a default value for the docker_host variable. This will work out
        if DockCI is running in Docker, and try and guess the Docker IP address
        to use for a TCP connection. Otherwise, defaults to the default
        unix socket.
        """
        docker_files = ('/.dockerenv', '/.dockerinit')
        if any(os.path.isfile(filename) for filename in docker_files):
            return "tcp://{ip}:2375".format(ip=default_gateway())

        return "unix:///var/run/docker.sock"


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
MAIL = Mail()
MAIL_QUEUE = multiprocessing.Queue()  # pylint:disable=no-member
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
    fields = (
        'docker_host', 'secret', 'workers',
        'mail_host_string', 'mail_use_tls', 'mail_use_ssl', 'mail_username',
        'mail_password', 'mail_default_sender'
    )
    restart_needed = any((
        attr in request.form and request.form[attr] != getattr(CONFIG, attr)
        for attr in fields
    ))
    if restart_needed:
        CONFIG.restart_needed = True
        flash(u"An application restart is required for some changes to take "
              "effect", 'warning')

    request_fill(CONFIG, fields)

    return render_template('config_edit.html')


@APP.route('/jobs/<slug>', methods=('GET', 'POST'))
def job_view(slug):
    """
    View to display a job
    """
    job = Job(slug)
    request_fill(job, ('name', 'repo', 'github_secret'))

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


def init_mail_queue():
    """
    Start the mail queue process
    """
    pid = os.fork()
    if not pid:  # child process
        with APP.app_context():
            logging.info("Email queue initiated")
            while True:
                message = MAIL_QUEUE.get()
                try:
                    MAIL.send(message)

                except Exception:  # pylint:disable=broad-except
                    logging.exception("Couldn't send email message")


def app_setup_extra():
    """
    Pre-run app setup
    """
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
    APP.secret_key = CONFIG.secret

    APP.config['MAIL_SERVER'] = CONFIG.mail_server
    APP.config['MAIL_PORT'] = CONFIG.mail_port
    APP.config['MAIL_USE_TLS'] = CONFIG.mail_use_tls
    APP.config['MAIL_USE_SSL'] = CONFIG.mail_use_ssl
    APP.config['MAIL_USERNAME'] = CONFIG.mail_username
    APP.config['MAIL_PASSWORD'] = CONFIG.mail_password
    APP.config['MAIL_DEFAULT_SENDER'] = CONFIG.mail_default_sender

    MAIL.init_app(APP)
    init_mail_queue()

    # Pool must be started after mail is initialized
    APP.workers = multiprocessing.pool.Pool(int(CONFIG.workers))

    mimetypes.add_type('application/x-yaml', 'yaml')


def main():
    """
    Setup and start the app
    """
    app_setup_extra()

    run_kwargs = {
        'debug': True
    }
    if len(sys.argv) > 1:
        run_kwargs.update({'host': sys.argv[1]})
    if len(sys.argv) > 2:
        run_kwargs.update({'port': int(sys.argv[2])})

    APP.run(**run_kwargs)


if __name__ == "__main__":
    main()
