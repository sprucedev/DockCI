""" API relating to Job model objects """
import sqlalchemy
import uuid

import flask_restful
import redis
import redis_lock

from flask import abort, request, url_for
from flask_restful import fields, inputs, marshal_with, Resource
from flask_security import current_user, login_required

from . import fields as fields_
from .base import BaseDetailResource, BaseRequestParser
from .fields import datetime_or_now, GravatarUrl, NonBlankInput, RewriteUrl
from .util import DT_FORMATTER
from dockci.models.job import Job, JobResult, JobStageTmp
from dockci.models.project import Project
from dockci.server import API, CONFIG, pika_conn, redis_pool
from dockci.stage_io import redis_len_key, redis_lock_name
from dockci.util import str2bool, require_agent


BASIC_FIELDS = {
    'slug': fields.String(),
    'state': fields.String(),
    'commit': fields.String(),
    'create_ts': DT_FORMATTER,
    'tag': fields.String(),
    'git_branch': fields.String(),
    'git_author_avatar': GravatarUrl(attr_name='git_author_email'),
}


LIST_FIELDS = {
    'detail': RewriteUrl('job_detail', rewrites=dict(
        project_slug='project.slug',
        job_slug='slug',
    )),
}
LIST_FIELDS.update(BASIC_FIELDS)

ITEMS_MARSHALER = fields.List(fields.Nested(LIST_FIELDS))
ALL_LIST_ROOT_FIELDS = {
    'items': ITEMS_MARSHALER,
    'meta': fields.Nested({
        'total': fields.Integer(default=None),
    }),
}

STAGE_DETAIL_FIELDS = {
    'success': fields.Boolean(),
}
STAGE_LIST_FIELDS = {
    'slug': fields.String(),
    'success': fields.Boolean(),
}


CREATE_FIELDS = {
    'project_detail': RewriteUrl('project_detail', rewrites=dict(
        project_slug='project.slug',
    )),
    'display_repo': fields.String(),
}
CREATE_FIELDS.update(LIST_FIELDS)

DETAIL_FIELDS = {
    'ancestor_detail': RewriteUrl('job_detail', rewrites=dict(
        project_slug='project.slug',
        job_slug='ancestor_job.slug',
    )),
    'project_detail': RewriteUrl('project_detail', rewrites=dict(
        project_slug='project.slug',
    )),
    'project_slug': fields.String(),
    'job_stage_slugs': fields.List(fields.String),

    'start_ts': DT_FORMATTER,
    'complete_ts': DT_FORMATTER,

    'display_repo': fields.String(),

    'image_id': fields.String(),
    'container_id': fields.String(),
    'docker_client_host': fields.String(),

    'exit_code': fields.Integer(default=None),
    'result': fields.String(),

    'git_author_name': fields.String(),
    'git_author_email': fields.String(),
    'git_committer_name': fields.String(),
    'git_committer_email': fields.String(),
    'git_committer_avatar': GravatarUrl(attr_name='git_committer_email'),
}
DETAIL_FIELDS.update(BASIC_FIELDS)
DETAIL_FIELDS.update(CREATE_FIELDS)

JOB_NEW_PARSER = BaseRequestParser()
JOB_NEW_PARSER.add_argument('commit',
                            required=True,
                            type=fields_.strip(NonBlankInput()),
                            help="Git ref to check out")

JOB_EDIT_PARSER = BaseRequestParser()
JOB_EDIT_PARSER.add_argument('start_ts', type=datetime_or_now)
JOB_EDIT_PARSER.add_argument('complete_ts', type=datetime_or_now)
JOB_EDIT_PARSER.add_argument('result',
                             choices=tuple(JobResult.__members__) + (None,))
JOB_EDIT_PARSER.add_argument('commit')
JOB_EDIT_PARSER.add_argument('tag')
JOB_EDIT_PARSER.add_argument('image_id')
JOB_EDIT_PARSER.add_argument('container_id')
JOB_EDIT_PARSER.add_argument('exit_code')
JOB_EDIT_PARSER.add_argument('git_branch')
JOB_EDIT_PARSER.add_argument('git_author_name')
JOB_EDIT_PARSER.add_argument('git_author_email')
JOB_EDIT_PARSER.add_argument('git_committer_name')
JOB_EDIT_PARSER.add_argument('git_committer_email')
JOB_EDIT_PARSER.add_argument('ancestor_job_id')

STAGE_EDIT_PARSER = BaseRequestParser()
STAGE_EDIT_PARSER.add_argument('success', type=inputs.boolean)


def get_validate_job(project_slug, job_slug):
    """ Get the job object, validate that project slug matches expected """
    job_id = Job.id_from_slug(job_slug)
    job = Job.query.get_or_404(job_id)
    if job.project.slug != project_slug:
        flask_restful.abort(404)

    if not (job.project.public or current_user.is_authenticated()):
        flask_restful.abort(404)

    return job


def stage_from_job(job, stage_slug):
    """ Get a stage object from a job """
    try:
        return next(
            stage for stage in job.job_stages
            if stage.slug == stage_slug
        )
    except StopIteration:
        return None


def get_validate_stage(project_slug, job_slug, stage_slug):
    """ Get a stage from a validated job """
    job = get_validate_job(project_slug, job_slug)
    stage = stage_from_job(job, stage_slug)
    if stage is None:
        abort(404)
    return stage


def filter_jobs_by_request(project):
    """ Get all jobs for a project, filtered by some request parameters """
    filter_args = {}
    for filter_name in ('passed', 'versioned', 'completed'):
        try:
            value = request.values[filter_name]
            if value == '':  # Acting as a switch
                filter_args[filter_name] = True
            else:
                filter_args[filter_name] = str2bool(value)

        except KeyError:
            pass

    for filter_name in ('branch', 'tag', 'commit'):
        try:
            filter_args[filter_name] = request.values[filter_name]
        except KeyError:
            pass

    return Job.filtered_query(
        query=project.jobs.order_by(sqlalchemy.desc(Job.create_ts)),
        **filter_args
    )


# pylint:disable=no-self-use

class JobList(BaseDetailResource):
    """ API resource that handles listing, and creating jobs """
    @marshal_with(ALL_LIST_ROOT_FIELDS)
    def get(self, project_slug):
        """ List all jobs for a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()

        if not (project.public or current_user.is_authenticated()):
            flask_restful.abort(404)

        base_query = filter_jobs_by_request(project)
        return {
            'items': base_query.paginate().items,
            'meta': {'total': base_query.count()},
        }

    @login_required
    @marshal_with(CREATE_FIELDS)
    def post(self, project_slug):
        """ Create a new job for a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        job = Job(project=project, repo_fs=project.repo_fs)
        self.handle_write(job, JOB_NEW_PARSER)
        job.queue()

        return job


class JobCommitsList(Resource):
    """ API resource to handle getting commit lists """
    def get(self, project_slug):
        """ List all distinct job commits for a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()

        if not (project.public or current_user.is_authenticated()):
            flask_restful.abort(404)

        base_query = filter_jobs_by_request(project).filter(
            Job.commit.op('SIMILAR TO')(r'[0-9a-fA-F]+')
        )
        commit_query = base_query.from_self(Job.commit).distinct(Job.commit)
        return {
            'items': [
                res_arr[0] for res_arr in commit_query.paginate().items
            ],
            'meta': {'total': commit_query.count()},
        }


class JobDetail(BaseDetailResource):
    """ API resource to handle getting job details """
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug, job_slug):
        """ Show job details """
        return get_validate_job(project_slug, job_slug)

    @require_agent
    @marshal_with(DETAIL_FIELDS)
    def patch(self, project_slug, job_slug):
        """ Update a job """
        job = get_validate_job(project_slug, job_slug)
        previous_state = job.state
        self.handle_write(job, JOB_EDIT_PARSER)
        new_state = job.state

        if new_state != previous_state:
            if job.project.is_external:
                job.send_external_status()
            if job.is_complete and job.changed_result():
                job.send_email_notification()

        return job


class StageList(Resource):
    """ API resource that handles listing stages for a job """
    @marshal_with(STAGE_LIST_FIELDS)
    def get(self, project_slug, job_slug):
        """ List all stage slugs for a job """
        def match(stage):
            """ Matches stages against query parameters """
            return not (
                'slug' in request.values and
                request.values['slug'] not in stage.slug
            )

        return [
            stage for stage in
            get_validate_job(project_slug, job_slug).job_stages
            if match(stage)
        ]


class StageDetail(BaseDetailResource):
    """ API resource to handle getting stage details """
    @marshal_with(STAGE_DETAIL_FIELDS)
    def get(self, project_slug, job_slug, stage_slug):
        """ Show job stage details """
        return get_validate_stage(project_slug, job_slug, stage_slug)

    @require_agent
    @marshal_with(STAGE_DETAIL_FIELDS)
    def put(self, project_slug, job_slug, stage_slug):
        """ Update a job stage """
        job = get_validate_job(project_slug, job_slug)
        stage = stage_from_job(job, stage_slug)
        created = True if stage is None else False
        if created:
            stage = JobStageTmp(slug=stage_slug, job=job)

        return self.handle_write(stage, STAGE_EDIT_PARSER)


class ArtifactList(Resource):
    """ API resource that handles listing artifacts for a job """
    def get(self, project_slug, job_slug):
        """ List output details for a job """
        return get_validate_job(project_slug, job_slug).job_output_details


class StageStreamDetail(Resource):
    """ API resource to handle creating stage stream queues """
    def post(self, project_slug, job_slug):
        """ Create a new stream queue for a job """
        job = get_validate_job(project_slug, job_slug)
        routing_key = 'dockci.{project_slug}.{job_slug}.*.*'.format(
            project_slug=project_slug,
            job_slug=job_slug,
        )

        with redis_pool() as redis_pool_:
            with pika_conn() as pika_conn_:
                channel = pika_conn_.channel()
                queue_result = channel.queue_declare(
                    queue='dockci.job.%s' % uuid.uuid4().hex,
                    arguments={
                        'x-expires': CONFIG.live_log_session_timeout,
                        'x-message-ttl': CONFIG.live_log_message_timeout,
                    },
                    durable=False,
                )

                redis_conn = redis.Redis(connection_pool=redis_pool_)
                with redis_lock.Lock(
                    redis_conn,
                    redis_lock_name(job),
                    expire=5,
                ):
                    channel.queue_bind(
                        exchange='dockci.job',
                        queue=queue_result.method.queue,
                        routing_key=routing_key,
                    )

                    try:
                        stage = job.job_stages[-1]

                    except IndexError:
                        stage = None
                        bytes_read = 0

                    else:
                        bytes_read = redis_conn.get(
                            redis_len_key(stage)
                        )

                        # Sometimes Redis gives us bytes :\
                        try:
                            bytes_read = bytes_read.decode()
                        except AttributeError:
                            pass

        return {
            'init_stage': None if stage is None else stage.slug,
            'init_log': None if stage is None else (
                "{url}?count={count}".format(
                    url=url_for(
                        'job_log_init_view',
                        project_slug=project_slug,
                        job_slug=job_slug,
                        stage=stage.slug
                    ),
                    count=bytes_read,
                )
            ),
            'live_queue': queue_result.method.queue,
        }


API.add_resource(
    JobList,
    '/projects/<string:project_slug>/jobs',
    endpoint='job_list',
)
API.add_resource(
    JobCommitsList,
    '/projects/<string:project_slug>/jobs/commits',
    endpoint='job_commits_list',
)
API.add_resource(
    JobDetail,
    '/projects/<string:project_slug>/jobs/<string:job_slug>',
    endpoint='job_detail',
)
API.add_resource(
    StageList,
    '/projects/<string:project_slug>/jobs/<string:job_slug>/stages',
    endpoint='stage_list',
)
API.add_resource(
    StageDetail,
    '/projects/<string:project_slug>/jobs/<string:job_slug>'
    '/stages/<string:stage_slug>',
    endpoint='stage_detail',
)
# API.add_resource(
#     ArtifactList,
#     '/projects/<string:project_slug>/jobs/<string:job_slug>/artifacts',
#     endpoint='artifact_list',
# )
API.add_resource(
    StageStreamDetail,
    '/projects/<string:project_slug>/jobs/<string:job_slug>/stream',
    endpoint='stage_stream_detail',
)
