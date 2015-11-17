""" Preparation for the main job stages """

import glob
import json
import re
import subprocess

from datetime import datetime
from itertools import chain
from urllib.parse import urlparse, urlunparse

import py.error  # pylint:disable=import-error
import py.path  # pylint:disable=import-error

from dockci.models.job_meta.config import JobConfig
from dockci.models.job_meta.stages import JobStageBase, CommandJobStage
from dockci.server import CONFIG
from dockci.util import (git_head_ref_name,
                         path_contained,
                         write_all,
                         )


class WorkdirStage(CommandJobStage):
    """ Prepare the working directory """

    slug = 'git_prepare'

    def __init__(self, job, workdir):
        display_repo = job.repo
        command_repo = job.repo
        repo_fs = None

        if job.project.is_type('gitlab'):
            gitlab_parts = list(urlparse(CONFIG.gitlab_base_url))
            gitlab_parts[1] = 'oauth2:{token_key}@%s' % gitlab_parts[1]
            gitlab_parts[2] = '%s.git' % job.project.gitlab_repo_id
            repo_fs = urlunparse(gitlab_parts)

        elif job.project.is_type('github'):
            repo_fs = 'https://oauth2:{token_key}@github.com/%s.git' % (
                job.project.github_repo_id
            )

        if repo_fs is not None:
            display_repo = repo_fs.format(token_key='****')
            command_repo = repo_fs.format(
                token_key=job.project.external_auth_token.key,
            )
            job.repo = display_repo
            job.db_session.add(job)
            job.db_session.commit()

        super(WorkdirStage, self).__init__(
            job, workdir, (
                dict(
                    command=['git', 'clone', command_repo, workdir.strpath],
                    display=['git', 'clone', display_repo, workdir.strpath],
                ),
                ['git',
                 '-c', 'advice.detachedHead=false',
                 'checkout', job.commit
                 ],
            )
        )

    def runnable(self, handle):
        """
        Clone and checkout the job
        """
        result = super(WorkdirStage, self).runnable(handle)

        # check for, and load job config
        job_config_file = self.workdir.join(JobConfig.slug)
        if job_config_file.check(file=True):
            # pylint:disable=no-member
            self.job.job_config.load(data_file=job_config_file)
            self.job.job_config.save()

        return result


class GitInfoStage(JobStageBase):
    """ Fill the Job with information obtained from the git repo """

    slug = 'git_info'

    def __init__(self, job, workdir):
        super(GitInfoStage, self).__init__(job)
        self.workdir = workdir

    def runnable(self, handle):
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
                                    cwd=self.workdir.strpath,
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
            'Full SHA-1 hash': ('commit', '%H'),
        }
        for display_name, (attr_name, format_string) in properties.items():
            proc = run_proc('git', 'show',
                            '-s',
                            '--format=format:%s' % format_string,
                            'HEAD')

            largest_returncode = max(largest_returncode, proc.returncode)
            value = proc.stdout.read().decode().strip()

            if value != '' and proc.returncode == 0:
                setattr(self.job, attr_name, value)
                properties_empty = False
                handle.write((
                    "%s is %s\n" % (display_name, value)
                ).encode())

        ancestor_job = self.job.project.latest_job_ancestor(
            self.workdir,
            self.job.commit,
        )
        if ancestor_job:
            properties_empty = False
            handle.write((
                "Ancestor job is %s\n" % ancestor_job.slug
            ).encode())
            self.job.ancestor_job_id = ancestor_job.id

        if self.job.git_branch is None:
            self.job.git_branch = git_head_ref_name(
                self.workdir, stderr=handle,
            )
            if self.job.git_branch is not None:
                properties_empty = False

        else:
            properties_empty = False

        if self.job.git_branch is None:
            handle.write("Branch name could not be determined\n".encode())
        else:
            handle.write(("Branch is %s\n" % self.job.git_branch).encode())

        if properties_empty:
            handle.write("No information about the git commit could be "
                         "derived\n".encode())

        else:
            self.job.db_session.add(self.job)
            self.job.db_session.commit()

        return proc.returncode


class GitChangesStage(CommandJobStage):
    """
    Get a list of changes from git between now and the most recently built
    ancestor
    """

    slug = 'git_changes'

    def __init__(self, job, workdir):
        cmd_args = None
        if job.ancestor_job is not None:
            revision_range_string = '%s..%s' % (
                job.ancestor_job.commit,  # pylint:disable=no-member
                job.commit,
            )

            cmd_args = [
                'git',
                '-c', 'color.ui=always',
                'log', revision_range_string
            ]
        super(GitChangesStage, self).__init__(job, workdir, cmd_args)

    def runnable(self, handle):
        # TODO fix YAML model to return None rather than an empty model so that
        #      if self.ancestor_job will work
        if self.cmd_args:
            return super(GitChangesStage, self).runnable(handle)

        return 0


def recursive_mtime(path, timestamp):
    """
    Recursively set mtime on the given path, returning the number of
    additional files or directories changed
    """
    path.setmtime(timestamp)
    extra = 0
    if path.isdir():
        for subpath in path.visit():
            try:
                subpath.setmtime(timestamp)
                extra += 1
            except py.error.ENOENT:
                pass

    return extra


class GitMtimeStage(JobStageBase):
    """
    Change the modified time to the commit time for any files in an ADD
    directive of a Dockerfile
    """

    slug = 'git_mtime'

    def __init__(self, job, workdir):
        super(GitMtimeStage, self).__init__(job)
        self.workdir = workdir

    def dockerfile_globs(self, dockerfile='Dockerfile'):
        """ Get all glob patterns from the Dockerfile """
        dockerfile_path = self.workdir.join(dockerfile)
        with dockerfile_path.open() as handle:
            for line in handle:
                if line[:4] == 'ADD ':
                    add_value = line[4:]
                    try:
                        for path in json.loads(add_value)[:-1]:
                            yield path

                    except ValueError:
                        add_file, _ = add_value.split(' ', 1)
                        yield add_file

        yield dockerfile
        yield '.dockerignore'

    def sorted_dockerfile_globs(self, reverse=False, dockerfile='Dockerfile'):
        """
        Sorted globs from the Dockerfile. Paths are sorted based on depth
        """
        def keyfunc(glob_str):
            """ Compare paths, ranking higher level dirs lower """
            path = self.workdir.join(glob_str)
            try:
                if path.samefile(self.workdir):
                    return -1
            except py.error.ENOENT:
                pass

            return len(path.parts())

        return sorted(self.dockerfile_globs(dockerfile),
                      key=keyfunc,
                      reverse=reverse)

    def timestamp_for(self, path):
        """ Get the timestamp for the given path """
        if path.samefile(self.workdir):
            git_cmd = [
                'git', 'log', '-1', '--format=format:%ct',
            ]
        else:
            git_cmd = [
                'git', 'log', '-1', '--format=format:%ct', '--', path.strpath,
            ]

        # Get the timestamp
        return int(subprocess.check_output(
            git_cmd,
            stderr=subprocess.STDOUT,
            cwd=self.workdir.strpath,
        ))

    def path_mtime(self, handle, path):
        """
        Set the mtime on the given path, writitng messages to the file handle
        given as necessary
        """
        # Ensure path is inside workdir
        if not path_contained(self.workdir, path):
            write_all(handle,
                      "%s not in the workdir; failing" % path.strpath)
            return False

        if not path.check():
            return True

        # Show the file, relative to workdir
        relpath = self.workdir.bestrelpath(path)
        write_all(handle, "%s: " % relpath)

        try:
            timestamp = self.timestamp_for(path)

        except subprocess.CalledProcessError as ex:
            # Something happened with the git command
            write_all(handle, [
                "Could not retrieve commit time from git. Exit "
                "code %d:\n" % ex.returncode,

                ex.output,
            ])
            return False

        except ValueError as ex:
            # A non-int value returned
            write_all(handle,
                      "Unexpected output from git: %s\n" % ex.args[0])
            return False

        # User output
        mtime = datetime.fromtimestamp(timestamp)
        write_all(handle, "%s... " % mtime.strftime('%Y-%m-%d %H:%M:%S'))

        # Set the time!
        extra = recursive_mtime(path, timestamp)

        extra_txt = ("(and %d more) " % extra) if extra > 0 else ""
        handle.write("{}DONE!\n".format(extra_txt).encode())
        if path.samefile(self.workdir):
            write_all(
                handle,
                "** Note: Performance benefits may be gained by adding "
                "only necessary files, rather than the whole source tree "
                "**\n",
            )

        return True

    def runnable(self, handle):
        """ Scrape the Dockerfile, update any ``mtime``s """
        dockerfile = self.job.job_config.dockerfile
        try:
            globs = self.sorted_dockerfile_globs(dockerfile=dockerfile)

        except py.error.ENOENT:
            write_all(
                handle,
                "Dockerfile '%s' not found! Can not continue" % dockerfile,
            )
            return 1

        # Join with workdir, unglob, and turn into py.path.local
        all_files = chain(*(
            (
                py.path.local(path)
                for path in glob.iglob(self.workdir.join(repo_glob).strpath)
            )
            for repo_glob in globs
        ))

        success = True
        for path in all_files:
            success &= self.path_mtime(handle, path)

        return 0 if success else 1


class TagVersionStage(CommandJobStage):
    """
    Try and add a version to the job, based on git tag
    """

    slug = 'git_tag'
    tag_re = re.compile(r'[a-z0-9_.]')

    def __init__(self, job, workdir):
        super(TagVersionStage, self).__init__(
            job, workdir,
            ['git', 'describe', '--tags', '--exact-match'],
        )

    def runnable(self, out_handle):
        returncode = super(TagVersionStage, self).runnable(out_handle)
        if returncode != 0:
            return returncode

        try:
            # TODO opening file to get this is kinda awful
            with self.data_file_path().open() as in_handle:
                last_line = None
                for line in in_handle:
                    line = line.strip()
                    if line and self.tag_re.match(line):
                        last_line = line

                if last_line:
                    self.job.tag = last_line
                    self.job.db_session.add(self.job)
                    self.job.db_session.commit()

        except KeyError:
            pass

        return returncode
