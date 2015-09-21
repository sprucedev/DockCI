from flask import request
from flask_restful import fields, marshal_with, Resource
from flask_security import login_required

from . import DT_FORMATTER
from .base import BaseDetailResource, BaseRequestParser
from .util import new_edit_parsers, RewriteUrl
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import API, DB


BASIC_FIELDS = {
    'slug': fields.String(),
    'state': fields.String(),
}


LIST_FIELDS = {
    'detail': RewriteUrl('job_detail', rewrites=dict(project_slug='project.slug', job_slug='slug')),
}
LIST_FIELDS.update(BASIC_FIELDS)


CREATE_FIELDS = {
    'project_detail': RewriteUrl('project_detail', rewrites=dict(project_slug='project.slug')),
    'create_ts': DT_FORMATTER,
    'repo': fields.String(),
    'commit': fields.String(),
}
CREATE_FIELDS.update(LIST_FIELDS)

DETAIL_FIELDS = {
    'ancestor_detail': RewriteUrl('job_detail', rewrites=dict(project_slug='project.slug', job_slug='ancestor_job.slug')),

    'start_ts': DT_FORMATTER,
    'complete_ts': DT_FORMATTER,

    'tag': fields.String(),
    'image_id': fields.String(),
    'container_id': fields.String(),
    'exit_code': fields.Integer(),
    'docker_client_host': fields.String(),
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
                            help="Git ref to check out")


def get_validate_job(project_slug, job_slug):
        """ Get the job object, validate that project slug matches expected """
        job_id = Job.id_from_slug(job_slug)
        job = Job.query.get_or_404(job_id)
        if job.project.slug != project_slug:
            abort(404)

        return job


class JobList(BaseDetailResource):
    @marshal_with(LIST_FIELDS)
    def get(self, project_slug):
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return project.jobs.all()

    @login_required
    @marshal_with(CREATE_FIELDS)
    def post(self, project_slug):
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        job = Job(project=project, repo=project.repo)
        self.handle_write(job, JOB_NEW_PARSER)
        job.queue()

        return job


class JobDetail(BaseDetailResource):
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug, job_slug):
        return get_validate_job(project_slug, job_slug)


class StageList(Resource):
    def get(self, project_slug, job_slug):
        return [
            stage.slug for stage in
            get_validate_job(project_slug, job_slug).job_stages
        ]


class ArtifactList(Resource):
    def get(self, project_slug, job_slug):
        return get_validate_job(project_slug, job_slug).job_output_details


API.add_resource(JobList,
                 '/projects/<string:project_slug>/jobs',
                 endpoint='job_list')
API.add_resource(JobDetail,
                 '/projects/<string:project_slug>/jobs/<string:job_slug>',
                 endpoint='job_detail')
API.add_resource(StageList,
                 '/projects/<string:project_slug>/jobs/<string:job_slug>/stages',
                 endpoint='stage_list')
API.add_resource(ArtifactList,
                 '/projects/<string:project_slug>/jobs/<string:job_slug>/artifacts',
                 endpoint='artifact_list')
