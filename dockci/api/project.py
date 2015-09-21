import re

from flask import request
from flask_restful import fields, inputs, marshal_with, reqparse, Resource
from flask_security import login_required

from .base import BaseDetailResource, BaseRequestParser
from .exceptions import WrappedValueError
from .util import filter_query_args, new_edit_parsers, RewriteUrl
from dockci.models.project import Project
from dockci.server import API, DB


class NoValue(object):
    pass


DOCKER_REPO_RE = re.compile(r'^[a-z0-9-_.]+$')

def docker_repo_field(value, name):
    if not DOCKER_REPO_RE.match(value):
        raise ValueError(("Invalid %s. Must only contain lower case, 0-9, "
                          "and the characters '-', '_' and '.'") % name)
    return value

BASIC_FIELDS = {
    'name': fields.String(),
    'slug': fields.String(),
    'utility': fields.Boolean(),
    'status': fields.String(),
}


LIST_FIELDS = {
    'detail': RewriteUrl('project_detail', rewrites=dict(project_slug='slug')),
}
LIST_FIELDS.update(BASIC_FIELDS)


DETAIL_FIELDS = {
    'repo': fields.String(),
    'utility': fields.Boolean(),
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
    'utility': dict(
        help="Whether or not this is a utility project",
        type=inputs.boolean,
        default=False
    ),
    'hipchat_room': dict(help="Room to post HipChat notifications to"),
    'hipchat_api_token': dict(help="HipChat API token for authentication"),
}

PROJECT_NEW_PARSER = BaseRequestParser()
PROJECT_EDIT_PARSER = BaseRequestParser()
new_edit_parsers(PROJECT_NEW_PARSER, PROJECT_EDIT_PARSER, SHARED_PARSER_ARGS)

PROJECT_FILTERS_PARSER = reqparse.RequestParser()

PROJECT_FILTERS_UTILITY = SHARED_PARSER_ARGS['utility'].copy()
PROJECT_FILTERS_UTILITY.pop('default')
PROJECT_FILTERS_PARSER.add_argument('utility', **PROJECT_FILTERS_UTILITY)


class ProjectList(Resource):
    @marshal_with(LIST_FIELDS)
    def get(self):
        return filter_query_args(PROJECT_FILTERS_PARSER, Project.query).all()


class ProjectDetail(BaseDetailResource):
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug):
        return Project.query.filter_by(slug=project_slug).first_or_404()

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def put(self, project_slug):
        try:
            docker_repo_field(project_slug, 'slug')
        except ValueError as ex:
            raise WrappedValueError(ex)

        project = Project(slug=project_slug)
        return self.handle_write(project, PROJECT_NEW_PARSER)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, project_slug):
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return self.handle_write(project, PROJECT_EDIT_PARSER)

    @login_required
    def delete(self, project_slug):
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        project_name = project.name
        project.purge()
        return {'message': '%s deleted' % project_name}


API.add_resource(ProjectList,
                 '/projects',
                 endpoint='project_list')
API.add_resource(ProjectDetail,
                 '/projects/<string:project_slug>',
                 endpoint='project_detail')
