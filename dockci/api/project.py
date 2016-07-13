""" API relating to Project model objects """
import re

import flask_restful
import sqlalchemy

from flask import request
from flask_restful import (fields,
                           inputs,
                           marshal,
                           marshal_with,
                           reqparse,
                           Resource,
                           )
from flask_security import current_user, login_required
from sqlalchemy.sql import functions as sql_func

from .base import BaseDetailResource, BaseRequestParser
from .exceptions import NoModelError, WrappedValueError
from .fields import (GravatarUrl,
                     NonBlankInput,
                     RegexField,
                     RegexInput,
                     RewriteUrl,
                     )
from .util import (clean_attrs,
                   DT_FORMATTER,
                   new_edit_parsers,
                   )
from dockci.models.auth import AuthenticatedRegistry
from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import API


DOCKER_REPO_RE = re.compile(r'^[a-z0-9]+(?:[._-][a-z0-9]+)*$')


def docker_repo_field(value, name):
    """ User input validation that a value is a valid Docker image name """
    if not DOCKER_REPO_RE.match(value):
        raise ValueError(("Invalid %s. Must start with a lower case, "
                          "alphanumeric character, and contain only the "
                          "additional characters '-', '_' and '.'") % name)
    return value


BASIC_FIELDS = {
    'name': fields.String(),
    'slug': fields.String(),
    'utility': fields.Boolean(),
    'status': fields.String(),
    'display_repo': fields.String(),
}


LIST_FIELDS = {
    'detail': RewriteUrl('project_detail', rewrites=dict(project_slug='slug')),
}
LIST_FIELDS.update(BASIC_FIELDS)

LATEST_JOB_FIELDS = {
    'slug': fields.String(),
    'detail': RewriteUrl('job_detail', rewrites=dict(
        project_slug='project.slug',
        job_slug='slug',
    )),
    'state': fields.String(),
    'create_ts': DT_FORMATTER,
    'git_author_avatar': GravatarUrl(attr_name='git_author_email')
}
LIST_FIELDS_LATEST_JOB = {
    'latest_job': fields.Nested(
        LATEST_JOB_FIELDS,
        attribute=lambda project: project.latest_job(),
        allow_null=True,
    ),
}
LIST_FIELDS_LATEST_JOB.update(LIST_FIELDS)

ITEMS_MARSHALER = fields.List(fields.Nested(LIST_FIELDS))
ITEMS_MARSHALER_LATEST_JOB = fields.List(fields.Nested(LIST_FIELDS_LATEST_JOB))

ALL_LIST_ROOT_FIELDS = {
    'items': ITEMS_MARSHALER,
    'meta': fields.Nested({
        'total': fields.Integer(default=None),
        'success': fields.Integer(default=None),
        'broken': fields.Integer(default=None),
        'fail': fields.Integer(default=None),
    }),
}


DETAIL_FIELDS = {
    'branch_pattern': RegexField(),
    'utility': fields.Boolean(),
    'github_repo_id': fields.String(),
    'github_hook_id': fields.String(),
    'gitlab_repo_id': fields.String(),
    'public': fields.Boolean(),
    'shield_text': fields.String(),
    'shield_color': fields.String(),
    'target_registry': RewriteUrl(
        'registry_detail',
        rewrites=dict(base_name='target_registry.base_name'),
    ),
}
DETAIL_FIELDS.update(BASIC_FIELDS)

BASIC_BRANCH_FIELDS = {
    'name': fields.String(),
}


TARGET_REGISTRY_ARGS = ('target_registry',)
TARGET_REGISTRY_KWARGS = dict(help="Base name of the registry to push to")

TARGET_REGISTRY_ARGUMENT_NEW = reqparse.Argument(
    *TARGET_REGISTRY_ARGS, required=True, **TARGET_REGISTRY_KWARGS
)
TARGET_REGISTRY_ARGUMENT_EDIT = reqparse.Argument(
    *TARGET_REGISTRY_ARGS, required=False, **TARGET_REGISTRY_KWARGS
)

SHARED_PARSER_ARGS = {
    'name': dict(
        help="Project display name",
        required=None, type=NonBlankInput(),
    ),
    'repo': dict(
        help="Git repository for the project code",
        required=None, type=NonBlankInput(),
    ),
    'branch_pattern': dict(
        help="Always tag, and push branches matching this pattern",
        type=RegexInput(),
    ),
    'github_secret': dict(help="Shared secret to validate GitHub hooks"),
    'public': dict(
        help="Whether or not to allow read-only guest access",
        type=inputs.boolean,
    ),
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
PROJECT_NEW_PARSER.add_argument(
    'gitlab_repo_id',
    help="ID of the project repository",
)
PROJECT_NEW_PARSER.add_argument(
    'github_repo_id',
    help="Full repository ID in GitHub",
)
PROJECT_NEW_PARSER.add_argument(TARGET_REGISTRY_ARGUMENT_NEW)
PROJECT_EDIT_PARSER.add_argument(TARGET_REGISTRY_ARGUMENT_EDIT)

PROJECT_LIST_PARSER = BaseRequestParser()
PROJECT_LIST_PARSER.add_argument(
    'meta',
    type=inputs.boolean,
    default=False,
    help="Whether to include metadata with the list",
)
PROJECT_LIST_PARSER.add_argument(
    'latest_job',
    type=inputs.boolean,
    default=False,
    help="Whether to include information about the latest job",
)

PROJECT_FILTERS_PARSER = reqparse.RequestParser()
PROJECT_FILTERS_PARSER.add_argument('utility', **UTILITY_ARG)

PROJECTS_OPTS_PARSER = reqparse.RequestParser()
PROJECTS_OPTS_PARSER.add_argument(
    'order',
    choices=('none', 'recent'),
    default='none',
    help="How to sort the projects list",
)


def set_target_registry(args):
    """ Set the ``target_registry`` to the model object """
    if 'target_registry' not in args:
        return

    if args['target_registry'] == '':
        args['target_registry'] = None
        return

    args['target_registry'] = (
        AuthenticatedRegistry.query.filter_by(
            base_name=args['target_registry'])).first()

    if args['target_registry'] is None:
        raise NoModelError('Registry')


def ensure_target_registry(required):
    """ Ensures that the ``target_registry`` is non-blank for utilities """
    value, found = reqparse.Argument(
        *TARGET_REGISTRY_ARGS,
        required=required,
        type=NonBlankInput(),
        **TARGET_REGISTRY_KWARGS
    ).parse(request, False)
    if isinstance(value, ValueError):
        flask_restful.abort(400, message=found)


# pylint:disable=no-self-use

class ProjectList(Resource):
    """ API resource that handles listing projects """
    def get(self):
        """ List of all projects """
        opts = PROJECTS_OPTS_PARSER.parse_args()
        filters = PROJECT_FILTERS_PARSER.parse_args()
        filters = clean_attrs(filters)

        query = Project.query

        if not current_user.is_authenticated():
            query = query.filter_by(public=True)

        if opts['order'] == 'recent':
            query = (
                query.
                join(Project.jobs, isouter=True).
                group_by(Project).
                order_by(sql_func.max(Job.create_ts).desc().nullslast())
            )

        if filters:
            query = query.filter(*[
                getattr(Project, field) == value
                for field, value in filters.items()
            ])

        marshaler = dict(items=ALL_LIST_ROOT_FIELDS['items'])
        values = dict(items=query.all())

        args = PROJECT_LIST_PARSER.parse_args()

        if args['meta']:
            marshaler['meta'] = ALL_LIST_ROOT_FIELDS['meta']
            values['meta'] = {'total': query.count()}
            values['meta'].update(Project.get_status_summary(filters))

        if args['latest_job']:
            marshaler['items'] = ITEMS_MARSHALER_LATEST_JOB

        return marshal(values, marshaler)


class ProjectDetail(BaseDetailResource):
    """
    API resource to handle getting project details, creating new projects,
    updating existing projects, and deleting projects
    """
    @marshal_with(DETAIL_FIELDS)
    def get(self, project_slug):
        """ Get project details """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        if not project.public or current_user.is_authenticated():
            flask_restful.abort(404)
        return project

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def put(self, project_slug):
        """ Create a new project """
        try:
            docker_repo_field(project_slug, 'slug')
        except ValueError as ex:
            raise WrappedValueError(ex)

        args = PROJECT_NEW_PARSER.parse_args(strict=True)
        args = clean_attrs(args)

        args['slug'] = project_slug

        if 'gitlab_repo_id' in args:
            args['external_auth_token'] = (
                current_user.oauth_token_for('gitlab'))

        elif 'github_repo_id' in args:
            args['external_auth_token'] = (
                current_user.oauth_token_for('github'))

        if args['utility']:  # Utilities must have target registry set
            ensure_target_registry(True)

        set_target_registry(args)

        return self.handle_write(Project(), data=args)

    @login_required
    @marshal_with(DETAIL_FIELDS)
    def post(self, project_slug):
        """ Update an existing project """
        project = Project.query.filter_by(slug=project_slug).first_or_404()
        args = PROJECT_EDIT_PARSER.parse_args(strict=True)
        args = clean_attrs(args)

        if args.get('utility', project.utility):
            ensure_target_registry(False)

        set_target_registry(args)
        return self.handle_write(project, data=args)

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

        if not project.public or current_user.is_authenticated():
            flask_restful.abort(404)

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
