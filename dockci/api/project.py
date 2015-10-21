""" API relating to Project model objects """
import re

import sqlalchemy

from flask_restful import fields, inputs, marshal_with, reqparse, Resource
from flask_security import login_required

from .base import BaseDetailResource, BaseRequestParser
from .exceptions import WrappedValueError
from .fields import NonBlankInput, RewriteUrl
from .util import filter_query_args, new_edit_parsers
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import API


DOCKER_REPO_RE = re.compile(r'^[a-z0-9-_.]+$')


def docker_repo_field(value, name):
    """ User input validation that a value is a valid Docker image name """
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

BASIC_BRANCH_FIELDS = {
    'name': fields.String(),
}


SHARED_PARSER_ARGS = {
    'name': dict(
        help="Project display name",
        required=None, type=NonBlankInput(),
    ),
    'repo': dict(
        help="Git repository for the project code",
        required=None, type=NonBlankInput(),
    ),
    'github_secret': dict(help="Shared secret to validate GitHub hooks"),
    'hipchat_room': dict(help="Room to post HipChat notifications to"),
    'hipchat_api_token': dict(help="HipChat API token for authentication"),
}

UTILITY_ARG = dict(
    help="Whether or not this is a utility project",
    type=inputs.boolean,  # Implies not-null/blank
)

PROJECT_NEW_PARSER = BaseRequestParser()
PROJECT_EDIT_PARSER = BaseRequestParser()
new_edit_parsers(PROJECT_NEW_PARSER, PROJECT_EDIT_PARSER, SHARED_PARSER_ARGS)

PROJECT_NEW_UTILITY_ARG = UTILITY_ARG.copy()
PROJECT_NEW_UTILITY_ARG['required'] = True
PROJECT_NEW_PARSER.add_argument('utility', **PROJECT_NEW_UTILITY_ARG)

PROJECT_FILTERS_PARSER = reqparse.RequestParser()
PROJECT_FILTERS_PARSER.add_argument('utility', **UTILITY_ARG)


# pylint:disable=no-self-use

class ProjectList(Resource):
    """ API resource that handles listing projects """
    @marshal_with(LIST_FIELDS)
    def get(self):
        """ List of all projects """
        return filter_query_args(PROJECT_FILTERS_PARSER, Project.query).all()


class ProjectDetail(BaseDetailResource):
    """
    API resource to handle getting project details, creating new projects,
    updating existing projects, and deleting projects
    """
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug):
        """ Get project details """
        return Project.query.filter_by(slug=project_slug).first_or_404()

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def put(self, project_slug):
        """ Create a new project """
        try:
            docker_repo_field(project_slug, 'slug')
        except ValueError as ex:
            raise WrappedValueError(ex)

        project = Project(slug=project_slug)
        return self.handle_write(project, PROJECT_NEW_PARSER)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, project_slug):
        """ Update an existing project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return self.handle_write(project, PROJECT_EDIT_PARSER)

    @login_required
    def delete(self, project_slug):
        """ Delete a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        project_name = project.name
        project.purge()
        return {'message': '%s deleted' % project_name}


class ProjectBranchList(Resource):
    """ API resource that handles listing branches for a project """
    @marshal_with(BASIC_BRANCH_FIELDS)
    def get(self, project_slug):
        """ List of all branches in a project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        return [
            dict(name=job.git_branch)
            for job
            in (
                project.jobs.distinct(Job.git_branch)
                .order_by(sqlalchemy.asc(Job.git_branch))
            )
            if job.git_branch is not None
        ]


API.add_resource(ProjectList,
                 '/projects',
                 endpoint='project_list')
API.add_resource(ProjectDetail,
                 '/projects/<string:project_slug>',
                 endpoint='project_detail')
API.add_resource(ProjectBranchList,
                 '/projects/<string:project_slug>/branches',
                 endpoint='project_branch_list')
