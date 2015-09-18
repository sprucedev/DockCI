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


DETAIL_FIELDS = {
    'project_detail': RewriteUrl('project_detail', rewrites=dict(project_slug='project.slug')),
    'ancestor_detail': RewriteUrl('job_detail', rewrites=dict(project_slug='project.slug', job_slug='ancestor_job.slug')),

    'create_ts': DT_FORMATTER,
    'start_ts': DT_FORMATTER,
    'complete_ts': DT_FORMATTER,

    'repo': fields.String(),
    'commit': fields.String(),
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


# SHARED_PARSER_ARGS = {
#     'name': dict(
#         help="Project display name",
#         required=None,
#     ),
#     'repo': dict(
#         help="Git repository for the project code",
#         required=None,
#     ),
#     'hipchat_room': dict(help="Room to post HipChat notifications to"),
#     'hipchat_api_token': dict(help="HipChat API token for authentication"),
# }

# PROJECT_NEW_PARSER = BaseRequestParser(bundle_errors=True)
# PROJECT_EDIT_PARSER = BaseRequestParser(bundle_errors=True)
# new_edit_parsers(PROJECT_NEW_PARSER, PROJECT_EDIT_PARSER, SHARED_PARSER_ARGS)


class JobList(Resource):
    @marshal_with(LIST_FIELDS)
    def get(self, project_slug):
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return project.jobs.all()


class JobDetail(BaseDetailResource):
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug, job_slug):
        job_id = Job.id_from_slug(job_slug)
        job = Job.query.get_or_404(job_id)
        if job.project.slug != project_slug:
            abort(404)

        return job

    # @login_required
    # @marshal_with(DETAIL_FIELDS)
    def put(self, project_slug, job_slug):
        pass
        # project = Project()
        # return self.handle_write(project, PROJECT_NEW_PARSER)

    # @login_required
    # @marshal_with(DETAIL_FIELDS)
    def post(self, project_slug, job_slug):
        pass
        # project = Project.query.filter_by(slug=project_slug).first_or_404()
        # return self.handle_write(project, PROJECT_EDIT_PARSER)


API.add_resource(JobList,
                 '/projects/<string:project_slug>/jobs',
                 endpoint='job_list')
API.add_resource(JobDetail,
                 '/projects/<string:project_slug>/jobs/<string:job_slug>',
                 endpoint='job_detail')
