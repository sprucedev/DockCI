from flask import request
from flask_restful import fields, marshal_with, Resource
from flask_security import login_required

from .base import BaseDetailResource, BaseRequestParser
from .util import new_edit_parsers, RewriteUrl
from dockci.models.project import Project
from dockci.server import API, DB


class NoValue(object):
    pass


BASIC_FIELDS = {
    'slug': fields.String(),
    'utility': fields.Boolean(),
    'status': fields.String(),
}


LIST_FIELDS = {
    'detail': RewriteUrl('project_detail', rewrites=dict(project_slug='slug')),
}
LIST_FIELDS.update(BASIC_FIELDS)


DETAIL_FIELDS = {
    'name': fields.String(),
    'repo': fields.String(),
    'hipchat_room': fields.String(),
    'github_repo_id': fields.String(),
    'github_hook_id': fields.String(),
    'shield_text': fields.String(),
    'shield_color': fields.String(),
}
DETAIL_FIELDS.update(BASIC_FIELDS)


SHARED_PARSER_ARGS = {
    'name': dict(
        help="Project display name",
        required=None,
    ),
    'repo': dict(
        help="Git repository for the project code",
        required=None,
    ),
    'hipchat_room': dict(help="Room to post HipChat notifications to"),
    'hipchat_api_token': dict(help="HipChat API token for authentication"),
}

PROJECT_NEW_PARSER = BaseRequestParser(bundle_errors=True)
PROJECT_EDIT_PARSER = BaseRequestParser(bundle_errors=True)
new_edit_parsers(PROJECT_NEW_PARSER, PROJECT_EDIT_PARSER, SHARED_PARSER_ARGS)


class ProjectList(Resource):
    @marshal_with(LIST_FIELDS)
    def get(self):
        return Project.query.all()


class ProjectDetail(BaseDetailResource):
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug):
        return Project.query.filter_by(slug=project_slug).first_or_404()

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def put(self, project_slug):
        project = Project()
        return self.handle_write(project, PROJECT_NEW_PARSER)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, project_slug):
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return self.handle_write(project, PROJECT_EDIT_PARSER)


API.add_resource(ProjectList,
                 '/projects',
                 endpoint='project_list')
API.add_resource(ProjectDetail,
                 '/projects/<string:project_slug>',
                 endpoint='project_detail')
