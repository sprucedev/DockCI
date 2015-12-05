""" API relating to Job model objects """
import sqlalchemy

from flask import abort, request
from flask_restful import fields, marshal_with, Resource
from flask_security import login_required

from . import fields as fields_
from .base import BaseDetailResource, BaseRequestParser
from .fields import NonBlankInput, RewriteUrl
from .util import DT_FORMATTER
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import API
from dockci.util import str2bool


BASIC_FIELDS = {
    'slug': fields.String(),
    'state': fields.String(),
}


LIST_FIELDS = {
    'detail': RewriteUrl('job_detail', rewrites=dict(
        project_slug='project.slug',
        job_slug='slug',
    )),
}
LIST_FIELDS.update(BASIC_FIELDS)


CREATE_FIELDS = {
    'project_detail': RewriteUrl('project_detail', rewrites=dict(
        project_slug='project.slug',
    )),
    'create_ts': DT_FORMATTER,
    'display_repo': fields.String(),
    'commit': fields.String(),
}
CREATE_FIELDS.update(LIST_FIELDS)

DETAIL_FIELDS = {
    'ancestor_detail': RewriteUrl('job_detail', rewrites=dict(
        project_slug='project.slug',
        job_slug='ancestor_job.slug',
    )),

    'start_ts': DT_FORMATTER,
    'complete_ts': DT_FORMATTER,

    'tag': fields.String(),
    'image_id': fields.String(),
    'container_id': fields.String(),
    'exit_code': fields.Integer(),
    'docker_client_host': fields.String(),
    'git_branch': fields.String(),
    'git_author_name': fields.String(),
    'git_author_email': fields.String(),
    'git_committer_name': fields.String(),
    'git_committer_email': fields.String(),
}
DETAIL_FIELDS.update(BASIC_FIELDS)
DETAIL_FIELDS.update(CREATE_FIELDS)

JOB_NEW_PARSER = BaseRequestParser()
JOB_NEW_PARSER.add_argument('commit',
                            required=True,
                            type=fields_.strip(NonBlankInput()),
                            help="Git ref to check out")


def get_validate_job(project_slug, job_slug):
    """ Get the job object, validate that project slug matches expected """
    job_id = Job.id_from_slug(job_slug)
    job = Job.query.get_or_404(job_id)
    if job.project.slug != project_slug:
        abort(404)

    return job


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

    try:
        filter_args['branch'] = request.values['branch']
    except KeyError:
        pass

    return Job.filtered_query(
        query=project.jobs.order_by(sqlalchemy.desc(Job.create_ts)),
        **filter_args
    )


# pylint:disable=no-self-use

class JobList(BaseDetailResource):
    """ API resource that handles listing, and creating jobs """
    @marshal_with(LIST_FIELDS)
    def get(self, project_slug):
        """ List all jobs for a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return filter_jobs_by_request(project).all()

    @login_required
    @marshal_with(CREATE_FIELDS)
    def post(self, project_slug):
        """ Create a new job for a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        job = Job(project=project, repo_fs=project.repo_fs)
        self.handle_write(job, JOB_NEW_PARSER)
        job.queue()

        return job


class JobDetail(BaseDetailResource):
    """ API resource to handle getting job details """
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug, job_slug):
        """ Show job details """
        return get_validate_job(project_slug, job_slug)


class StageList(Resource):
    """ API resource that handles listing stage slugs for a job """
    def get(self, project_slug, job_slug):
        """ List all stage slugs for a job """
        return [
            stage.slug for stage in
            get_validate_job(project_slug, job_slug).job_stages
        ]


class ArtifactList(Resource):
    """ API resource that handles listing artifacts for a job """
    def get(self, project_slug, job_slug):
        """ List output details for a job """
        return get_validate_job(project_slug, job_slug).job_output_details


API.add_resource(
    JobList,
    '/projects/<string:project_slug>/jobs',
    endpoint='job_list',
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
    ArtifactList,
    '/projects/<string:project_slug>/jobs/<string:job_slug>/artifacts',
    endpoint='artifact_list',
)
