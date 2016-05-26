""" Preparation for the main job stages """

import glob
import json
import subprocess

from datetime import datetime
from itertools import chain

import py.error  # pylint:disable=import-error
import py.path  # pylint:disable=import-error
import pygit2

from dockci.models.job_meta.config import JobConfig
from dockci.models.job_meta.stages import CommandJobStage, JobStageBase
from dockci.util import (git_head_ref_name,
                         path_contained,
                         write_all,
                         )


def origin_pair(ref_str):
    """
    Ensure one ref string starts with ``'origin/'``, and one not

    Examples:

    >>> origin_pair('master')
    ('origin/master', 'master')
    >>> origin_pair('origin/master')
    ('origin/master', 'master')
    >>> origin_pair('upstream/master')
    ('origin/upstream/master', 'upstream/master')
    >>> origin_pair('origin/upstream/master')
    ('origin/upstream/master', 'upstream/master')
    """
    with_origin = (
        ref_str if ref_str.startswith('origin/')
        else 'origin/%s' % ref_str
    )
    without_origin = with_origin[7:]
    return with_origin, without_origin


class WorkdirStage(JobStageBase):
    """ Prepare the working directory """

    slug = 'git_prepare'

    def __init__(self, job, workdir):
        super(WorkdirStage, self).__init__(job)
        self.workdir = workdir

    def runnable(self, handle):
        """
        Clone and checkout the job
        """
        job = self.job
        handle.write("Cloning from %s\n" % job.display_repo)
        repo = pygit2.clone_repository(
            job.command_repo,
            self.workdir.join('.git').strpath,
        )

        handle.write("Finding %s\n" % job.commit)
        try:
            git_obj = repo.revparse_single(job.commit)  # noqa pylint:disable=no-member
        except KeyError:
            handle.write("Can't find that ref anywhere!\n")
            return False

        ref_type_str = 'unknown ref type'

        if git_obj.type == pygit2.GIT_OBJ_BLOB:
            ref_type_str = 'blob'

        elif git_obj.type == pygit2.GIT_OBJ_COMMIT:
            remote_ref, local_ref = origin_pair(job.commit)
            branch = repo.lookup_branch(  # pylint:disable=no-member
                remote_ref,
                pygit2.GIT_BRANCH_REMOTE,
            )
            if branch is not None:
                git_obj = branch
                ref_type_str = 'branch'
                if job.git_branch is None:
                    job.git_branch = local_ref
            else:
                ref_type_str = 'commit'

        elif git_obj.type == pygit2.GIT_OBJ_TAG:
            ref_type_str = 'tag'
            if job.tag is None:
                job.tag = git_obj.name

        elif git_obj.type == pygit2.GIT_OBJ_TREE:
            ref_type_str = 'treeish'

        oid = getattr(git_obj, 'oid', None) or git_obj.target
        job.commit = oid.hex

        job.db_session.add(job)
        job.db_session.commit()

        ref_name_str = (
            getattr(git_obj, 'shorthand', None) or
            getattr(git_obj, 'name', None) or
            job.commit
        )

        handle.write("Checking out %s %s\n" % (ref_type_str, ref_name_str))
        repo.reset(  # pylint:disable=no-member
            oid,
            pygit2.GIT_RESET_HARD,
        )

        # check for, and load job config
        job_config_file = self.workdir.join(JobConfig.slug)
        if job_config_file.check(file=True):
            # pylint:disable=no-member
            job.job_config.load(data_file=job_config_file)
            job.job_config.save()

        return True


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


class TagVersionStage(JobStageBase):
    """ Try and add a version to the job, based on git tag """

    slug = 'git_tag'

    def __init__(self, job, workdir):
        super(TagVersionStage, self).__init__(job)
        self.workdir = workdir

    def runnable(self, handle):
        """
        Examples:

        >>> from io import StringIO
        >>> from subprocess import check_call

        >>> test_path = getfixture('tmpdir')
        >>> test_file = test_path.join('test.txt')
        >>> test_file.write('test')
        >>> _ = test_path.chdir()
        >>> _ = check_call(['git', 'init'])
        >>> _ = check_call(['git', 'config', 'user.email', 'a@example.com'])
        >>> _ = check_call(['git', 'config', 'user.name', 'Test'])
        >>> _ = check_call(['git', 'add', '.'])
        >>> _ = check_call(['git', 'commit', '-m', 'First'])

        Identifies untagged commits:

        >>> output = StringIO()
        >>> TagVersionStage(None, test_path).runnable(output)
        True
        >>> print(output.getvalue())
        Untagged commit
        <BLANKLINE>

        Finds all annotated commits, warns when multiple, ignores light tags:

        >>> _ = check_call(['git', 'tag', '-a', 'test-1', '-m', 'Test 1'])
        >>> _ = check_call(['git', 'tag', '-a', 'test-2', '-m', 'Test 2'])
        >>> _ = check_call(['git', 'tag', 'test-3'])
        >>> output = StringIO()
        >>> TagVersionStage(None, test_path).runnable(output)
        True
        >>> print(output.getvalue())
        Tag: Test 1 (test-1)
        Tag: Test 2 (test-2)
        WARNING: Multiple tags; using "test-1"
        <BLANKLINE>

        Deals with untagged commits, where tags exist elsewhere:

        >>> test_file.write('other')
        >>> _ = check_call(['git', 'commit', '-m', 'Second', '.'])
        >>> output = StringIO()
        >>> TagVersionStage(None, test_path).runnable(output)
        True
        >>> print(output.getvalue())
        Untagged commit
        <BLANKLINE>


        Finds only tags associated with the commit:

        >>> test_file.write('more')
        >>> _ = check_call(['git', 'commit', '-m', 'Third', '.'])
        >>> _ = check_call('GIT_COMMITTER_DATE=2016-01-01T12:00:00 '
        ...                'git tag -a test-4 -m "Test 4"', shell=True)
        >>> output = StringIO()
        >>> TagVersionStage(None, test_path).runnable(output)
        True
        >>> print(output.getvalue())
        Tag: Test 4 (test-4)
        <BLANKLINE>

        Uses the tag created at the latest time:

        >>> _ = check_call('GIT_COMMITTER_DATE=2016-01-01T13:00:00 '
        ...                'git tag -a zzz-later -m "ZZZ"', shell=True)
        >>> output = StringIO()
        >>> TagVersionStage(None, test_path).runnable(output)
        True
        >>> print(output.getvalue())
        Tag: Test 4 (test-4)
        Tag: ZZZ (zzz-later)
        WARNING: Multiple tags; using "zzz-later"
        <BLANKLINE>
        """
        # pygit2 fails member checks because it's CFFI
        # pylint:disable=no-member
        repo = pygit2.Repository(self.workdir.join('.git').strpath)
        head_oid = repo.head.get_object().oid

        repo_tag_refs = (
            repo.lookup_reference(ref_str)
            for ref_str in repo.listall_references()
            if ref_str.startswith('refs/tags/')
        )
        repo_ref_targets = (
            repo[ref.target] for ref in repo_tag_refs
        )
        repo_ann_tags = (
            git_obj for git_obj in repo_ref_targets
            if isinstance(git_obj, pygit2.Tag)
        )
        head_tags = (
            tag for tag in repo_ann_tags
            if tag.target == head_oid
        )

        tag_count = 0
        commit_tag = None
        for tag in head_tags:
            tag_count += 1

            if commit_tag is None:
                commit_tag = tag
            elif tag.tagger.time > commit_tag.tagger.time:
                commit_tag = tag

            handle.write("Tag: {message} ({name})\n".format(
                message=tag.message.strip(),
                name=tag.name,
            ))
            handle.flush()

        if tag_count == 0:
            handle.write("Untagged commit\n")

        elif tag_count > 1:
            handle.write("WARNING: Multiple tags; using \"{name}\"\n".format(
                name=commit_tag.name,
            ))

        handle.flush()

        if tag_count > 0 and self.job is not None:
            self.job.tag = commit_tag.name
            self.job.db_session.add(self.job)
            self.job.db_session.commit()

        return True
