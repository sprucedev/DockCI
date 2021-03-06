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
    project = Project.query.filter_by(slug=project_slug).first_or_404()
    if not (project.public or current_user.is_authenticated()):
        abort(404)

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
    project = Project.query.filter_by(slug=project_slug).first_or_404()
    if not (project.public or current_user.is_authenticated()):
        abort(404)

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

    byte_seek = request.args.get('seek', None, type=int)
    line_seek = request.args.get('seek_lines', None, type=int)
    bytes_count = request.args.get('count', None, type=int)
    lines_count = request.args.get('count_lines', None, type=int)

    if byte_seek and line_seek:
        return "byte_seek and line_seek are mutually exclusive", 400
    if bytes_count and lines_count:
        return "bytes_count and lines_count are mutually exclusive", 400

    def loader():
        """ Stream the parts of the log that we want """
        with data_file_path.open('rb') as handle:
            if byte_seek is not None:
                _seeker_bytes(handle, byte_seek)
            if line_seek is not None:
                _seeker_lines(handle, line_seek)

            if bytes_count is not None:
                gen = _reader_bytes(handle, bytes_count)
            elif lines_count is not None:
                gen = _reader_lines(handle, lines_count)
            else:
                gen = _reader_bytes(handle)

            for data in gen:
                yield data

    return Response(loader(), mimetype='text/plain')


def _reader_bytes(handle, count=None, chunk_size=1024):
    """
    Read a given number of bytes

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abcdefghi')

    >>> handle = tmp_file.open()
    >>> handle.seek(4)
    4
    >>> list(_reader_bytes(handle, 2))
    ['ef']

    >>> handle = tmp_file.open()
    >>> handle.seek(4)
    4
    >>> list(_reader_bytes(handle, chunk_size=3))
    ['efg', 'hi']
    """
    remain = count
    while remain is None or remain > 0:
        if remain is not None:
            chunk_size = min(chunk_size, remain)

        data = handle.read(chunk_size)

        if remain is not None:
            remain -= len(data)

        if len(data) == 0:
            return

        yield data


def _reader_lines(handle, count=None):
    """
    Read a given number of lines

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> handle.seek(4)
    4
    >>> list(_reader_lines(handle, 2))
    ['def\\n', 'ghi\\n']

    >>> handle = tmp_file.open()
    >>> handle.seek(8)
    8
    >>> list(_reader_lines(handle))
    ['ghi\\n', 'jkl\\n', 'mno']

    >>> handle = tmp_file.open()
    >>> handle.seek(5)
    5
    >>> list(_reader_lines(handle, 1))
    ['ef\\n']

    >>> tmp_file.write('abc\\n\\ndef\\n')
    >>> handle = tmp_file.open()
    >>> list(_reader_lines(handle))
    ['abc\\n', '\\n', 'def\\n', '']

    >>> handle = tmp_file.open('rb')
    >>> list(_reader_lines(handle))
    [b'abc\\n', b'\\n', b'def\\n', b'']
    """
    remain = count
    while remain is None or remain > 0:
        data = handle.readline()

        if remain is not None:
            remain -= 1

        yield data

        search_char = b'\n' if isinstance(data, bytes) else '\n'
        if search_char not in data:
            return


def _seeker_bytes(handle, seek):
    """
    Seek ahead in handle by the given number of bytes. If ``seek`` is
    negative, seeks that number of bytes from the end of the file

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abcdefghi')

    >>> handle = tmp_file.open()
    >>> _seeker_bytes(handle, 3)
    >>> handle.read(1)
    'd'

    >>> handle = tmp_file.open()
    >>> _seeker_bytes(handle, -3)
    >>> handle.read(1)
    'g'
    """
    if seek >= 0:
        handle.seek(seek)
    else:
        handle.seek(0, 2)
        file_size = handle.tell()
        handle.seek(file_size + seek)  # seek is negative


def _seeker_lines(handle, seek):
    """
    Seek ahead in handle by the given number of lines

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, 3)
    >>> handle.read(1)
    'j'

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, -1)
    >>> handle.read(3)
    'mno'

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, -3)
    >>> handle.read(1)
    'g'

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, -20)
    >>> handle.read(3)
    'abc'

    >>> handle = tmp_file.open('rb')
    >>> _seeker_lines(handle, -20)
    >>> handle.read(3)
    b'abc'
    """
    if seek >= 0:
        for _ in range(seek):
            _seeker_lines_one_ahead(handle)
    else:
        handle.seek(0, 2)
        seek = seek * -1
        for idx in range(seek):
            current_pos = _seeker_lines_one_back(handle)

            if current_pos == 0:
                return

            # unless last iter, seek back 1 for the new line
            if idx + 1 < seek:
                handle.seek(current_pos - 1)


def _seeker_lines_one_ahead(handle):
    """
    Seek ahead in handle by 1 line

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> handle.seek(10)
    10
    >>> _seeker_lines_one_ahead(handle)
    >>> handle.read(3)
    'jkl'
    >>>
    """
    while handle.read(1) not in ('\n', b'\n', None, '', b''):
        pass


def _seeker_lines_one_back(handle):
    """
    Seek back in handle by 1 line

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> handle.seek(10)
    10
    >>> _seeker_lines_one_back(handle)
    8
    >>> handle.read(3)
    'ghi'

    >>> handle = tmp_file.open()
    >>> _seeker_lines_one_back(handle)
    0
    >>> handle.read(3)
    'abc'
    """
    first = True
    current_pos = handle.tell()
    while first or handle.read(1) not in ('\n', b'\n', None, '', b''):
        first = False
        current_pos -= 1

        if current_pos < 0:
            handle.seek(0)
            return 0

        handle.seek(current_pos)

    return current_pos + 1  # add 1 for the read


@APP.route('/projects/<project_slug>/jobs/<job_slug>/output/<filename>',
           methods=('GET',))
def job_output_view(project_slug, job_slug, filename):
    """ View to download some job output """
    data_file_path = check_output(project_slug, job_slug, filename)
    send_file(data_file_path.strpath)
