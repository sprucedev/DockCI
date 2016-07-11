"""
DockCI - CI, but with that all important Docker twist
"""

# TODO fewer lines somehow
# pylint:disable=too-many-lines

import json
import logging

from datetime import datetime
from enum import Enum

import py.path  # pylint:disable=import-error
import rollbar
import sqlalchemy

from flask import url_for
from flask_mail import Message

from .base import RepoFsMixin
from dockci.exceptions import AlreadyRunError, InvalidServiceTypeError
from dockci.server import DB, MAIL, OAUTH_APPS, pika_conn
from dockci.util import (add_to_url_path,
                         bytes_human_readable,
                         ext_url_for,
                         )


STATE_MAP = {
    'github': {
        'queued': 'pending',
        'running': 'pending',
        'success': 'success',
        'fail': 'failure',
        'broken': 'error',
        None: 'error',
    },
    'gitlab': {
        'queued': 'pending',
        'running': 'running',
        'success': 'success',
        'fail': 'failed',
        'broken': 'canceled',
        None: 'canceled',
    },
}


class JobResult(Enum):
    """ Possible results for Job models """
    success = 'success'
    fail = 'fail'
    broken = 'broken'


RESULT_NOTIFICATIONS = {
    JobResult.success.value: 'started succeeding',
    JobResult.fail.value: 'started failing',
    JobResult.broken.value: 'needs attention',
}


PushableReasons = Enum(  # pylint:disable=invalid-name
    'PushableReasons',
    """
    result_success
    good_exit
    tag_push
    branch_push
    """,
)


UnpushableReasons = Enum(  # pylint:disable=invalid-name
    'UnpushableReasons',
    """
    not_good_state
    bad_state
    no_tag
    no_project
    no_target_registry
    no_branch
    no_branch_pattern
    no_branch_match
    """,
)


PUSH_REASON_MESSAGES = {
    PushableReasons.result_success: "successful job result",
    PushableReasons.good_exit: "exit code was 0",
    PushableReasons.tag_push: "commit is tagged",
    PushableReasons.branch_push: "branch matches rules",

    UnpushableReasons.not_good_state: "job is not in a successful state",
    UnpushableReasons.bad_state: "job is in a bad state",
    UnpushableReasons.no_tag: "commit not tagged",
    UnpushableReasons.no_project: "job doesn't have a project",
    UnpushableReasons.no_target_registry: "project has no registry target",
    UnpushableReasons.no_branch: "commit not on a branch",
    UnpushableReasons.no_branch_pattern: "project has no branch pattern",
    UnpushableReasons.no_branch_match:
        "branch name doesn't match branch pattern",
}

COMPLETE_STATES = (JobResult.success.value,
                   JobResult.fail.value,
                   JobResult.broken.value,
                   )


class JobStageTmp(DB.Model):  # pylint:disable=no-init
    """ Quick and dirty list of job stages for the time being """
    id = DB.Column(DB.Integer(), primary_key=True)
    slug = DB.Column(DB.String(31))
    job_id = DB.Column(DB.Integer, DB.ForeignKey('job.id'), index=True)
    success = DB.Column(DB.Boolean(), nullable=True)
    job = DB.relationship(
        'Job',
        foreign_keys="JobStageTmp.job_id",
        backref=DB.backref(
            'job_stages',
            order_by=sqlalchemy.asc('id'),
            ))


# pylint:disable=too-many-instance-attributes,no-init,too-many-public-methods
class Job(DB.Model, RepoFsMixin):
    """ An individual project job, and result """

    id = DB.Column(DB.Integer(), primary_key=True)

    create_ts = DB.Column(
        DB.DateTime(), nullable=False, default=datetime.now,
    )
    start_ts = DB.Column(DB.DateTime())
    complete_ts = DB.Column(DB.DateTime())

    result = DB.Column(DB.Enum(
        *JobResult.__members__,
        name='job_results'
    ), index=True)
    repo_fs = DB.Column(DB.Text(), nullable=False)
    commit = DB.Column(DB.String(41), nullable=False)
    tag = DB.Column(DB.Text())
    image_id = DB.Column(DB.String(65))
    container_id = DB.Column(DB.String(65))
    exit_code = DB.Column(DB.Integer())
    docker_client_host = DB.Column(DB.Text())
    git_branch = DB.Column(DB.Text())
    git_author_name = DB.Column(DB.Text())
    git_author_email = DB.Column(DB.Text())
    git_committer_name = DB.Column(DB.Text())
    git_committer_email = DB.Column(DB.Text())
    git_changes = DB.Column(DB.Text())

    ancestor_job_id = DB.Column(DB.Integer, DB.ForeignKey('job.id'))
    child_jobs = DB.relationship(
        'Job',
        foreign_keys="Job.ancestor_job_id",
        backref=DB.backref('ancestor_job', remote_side=[id]),
    )
    project_id = DB.Column(DB.Integer, DB.ForeignKey('project.id'), index=True)

    _job_config = None
    _db_session = None

    def __str__(self):
        try:
            slug = self.slug
        except TypeError:
            slug = self.id

        return '<{klass}: {project_slug}/{job_slug}>'.format(
            klass=self.__class__.__name__,
            project_slug=self.project.slug,
            job_slug=slug,
        )

    @property
    def slug(self):
        """ Generated web slug for this job """
        return self.slug_from_id(self.id)

    @classmethod
    def id_from_slug(cls, slug):
        """ Convert a slug to an ID for ORM lookup """
        return int(slug, 16)

    @classmethod
    def slug_from_id(cls, id_):
        """ Convert an ID to a slug (padded hex) """
        return '{:0>6}'.format(hex(id_)[2:])

    @property
    def compound_slug(self):
        """
        A slug that includes all identifiers necessary for this model to be
        unique in the data set
        """
        return '%s/%s' % (self.project.slug, self.slug)

    @property
    def job_stage_slugs(self):
        """ List of slugs for all job stages """
        return [stage.slug for stage in self.job_stages]

    @property
    def project_slug(self):
        """ Shortcut for the API to get project slug """
        return self.project.slug

    @property
    def url(self):
        """ URL for this job """
        return url_for('job_view',
                       project_slug=self.project.slug,
                       job_slug=self.slug)

    @property
    def url_ext(self):
        """ URL for this project """
        return ext_url_for('job_view',
                           project_slug=self.project.slug,
                           job_slug=self.slug)

    @property
    def github_api_status_endpoint(self):
        """ Status endpoint for GitHub API """
        return '%s/commits/%s/statuses' % (
            self.project.github_api_repo_endpoint,
            self.commit,
        )

    @property
    def gitlab_api_status_endpoint(self):
        """ Status endpoint for GitLab API """
        return add_to_url_path(
            self.project.gitlab_api_repo_endpoint,
            '/statuses/%s' % self.commit,
        )

    @property
    def state(self):
        """
        Current state that the job is in
        """
        if self.result is not None:
            return self.result
        elif self.job_stages:
            return 'running'  # TODO check if running or dead
        else:
            return 'queued'  # TODO check if queued or queue fail

    def changed_result(self, workdir=None):
        """
        Check if this job changed the result from it's ancestor. None if
        there's no result yet
        """
        if self.result is None:
            return None

        ancestor_job = self.ancestor_job
        if not ancestor_job:
            return True

        if ancestor_job.result is None:
            if workdir is None:  # Can't get a better ancestor
                return True

            ancestor_job = self.project.latest_job_ancestor(
                workdir, self.commit, complete=True,
            )

        if not ancestor_job:
            return True

        return ancestor_job.result != self.result

    @property
    def job_output_details(self):
        """
        Details for job output artifacts
        """
        # pylint:disable=no-member
        output_files = (
            (name, self.job_output_path().join('%s.tar' % name))
            for name in self.job_config.job_output.keys()
        )
        return {
            name: {'size': bytes_human_readable(path.size()),
                   'link': url_for('job_output_view',
                                   project_slug=self.project.slug,
                                   job_slug=self.slug,
                                   filename='%s.tar' % name,
                                   ),
                   }
            for name, path in output_files
            if path.check(file=True)
        }

    @property
    def is_complete(self):
        """
        Jobs are complete if they are success, fail, or broken

        Examples:

        >>> Job(result=JobResult.fail.value).is_complete
        True

        >>> Job(result=JobResult.broken.value).is_complete
        True

        >>> Job(result=JobResult.success.value).is_complete
        True

        >>> job = Job(job_stages=[])
        >>> job.state
        'queued'
        >>> job.is_complete
        False

        >>> job = Job(job_stages=[None])
        >>> job.state
        'running'
        >>> job.is_complete
        False
        """
        return self.state in COMPLETE_STATES

    @property
    def external_auth_token(self):
        """ Pass the auth token getter off to the project """
        return self.project.external_auth_token

    @classmethod
    def delete_all_in_project(cls, project):
        """ Delete all jobs and data for the given project """
        cls.data_dir_path_for_project(project).remove(rec=True)

    @classmethod
    def data_dir_path_for_project(cls, project):
        """ Get the path that jobs reside in for the given project """
        return cls.data_dir_path().join(project.slug)

    @classmethod
    def data_dir_path(cls):
        """ Temporary mock for removing YAML model """
        path = py.path.local('data')
        path.ensure(dir=True)
        return path

    def job_output_path(self):
        """ Directory for any job output data """
        return self.data_dir_path_for_project(self.project).join(self.slug)

    @classmethod
    def filtered_query(cls,
                       query=None,
                       passed=None,
                       versioned=None,
                       tag=None,
                       completed=None,
                       branch=None,
                       commit=None,
                       ):
        """
        Generator, filtering jobs matching the criteria
        """
        if query is None:
            query = cls.query.order_by(sqlalchemy.desc(cls.create_ts))

        def filter_on_value(query, equal, field, value):
            """
            Filter the query for field on a given value being equal, or
            non-equal
            """
            if equal:
                return query.filter(field == value)
            else:
                return query.filter(field != value)

        if passed is not None:
            query = filter_on_value(query, passed, cls.result, 'success')

        if versioned is not None:
            query = filter_on_value(query, not versioned, cls.tag, None)

        if tag is not None:
            query = query.filter(cls.tag == tag)

        if completed is not None:
            query = query.filter(cls.result.in_(('success', 'fail', 'broken')))

        if branch is not None:
            query = query.filter_by(git_branch=branch)

        if commit is not None:
            query = query.filter_by(commit=commit)

        return query

    def queue(self):
        """
        Add the job to the queue
        """
        if self.start_ts:
            raise AlreadyRunError(self)

        with pika_conn() as conn:
            channel = conn.channel()
            channel.basic_publish(
                exchange='dockci.queue',
                routing_key='new_job',
                body=json.dumps(dict(
                    job_slug=self.slug,
                    project_slug=self.project.slug,
                    command_repo=self.command_repo,
                )),
            )

    def state_data_for(self, service, state=None, state_msg=None):
        """
        Get the mapped state, and associated message for a service.

        To look up state label, first the dict ``STATE_MAP`` is queried for the
        service name. If no value is found, state is kept as is. If the service
        key is found, looks up the state value. If no value is found, the
        ``None`` key is looked up.

        The state message is simply a switch on the original state.
        """
        state = state or self.state
        service_state = state

        try:
            service_state_map = STATE_MAP[service]

        except KeyError:
            pass

        else:
            try:
                service_state = service_state_map[state]

            except KeyError:
                service_state = service_state_map[None]
                state_msg = "is in an unknown state: '%s'" % state

        if state_msg is None:
            if state == 'running':
                state_msg = "is in progress"
            elif state == 'success':
                state_msg = "completed successfully"
            elif state == 'fail':
                state_msg = "completed with failing tests"
            elif state == 'broken':
                state_msg = "failed to complete due to an error"

        if state_msg is not None:
            state_msg = "The DockCI job %s" % state_msg

        return service_state, state_msg

    def send_gitlab_status(self, state=None, state_msg=None, context='push'):
        """ Send the job state to GitLab (see ``send_external_status`` """
        return self.send_external_status(
            'gitlab',
            self.gitlab_api_status_endpoint,
            state=state,
            state_msg=state_msg,
            context=context,
        )

    def send_github_status(self, state=None, state_msg=None, context='push'):
        """ Send the job state to GitHub (see ``send_external_status`` """
        return self.send_external_status(
            'github',
            self.github_api_status_endpoint,
            state=state,
            state_msg=state_msg,
            context=context,
        )

    def send_external_status(self,
                             service=None,
                             api_endpoint=None,
                             state=None,
                             state_msg=None,
                             context='push',
                             ):
        """
        Send a state to the service for the commit represented by this job. If
        state not set, is defaulted to something that makes sense, given the
        data in this model
        """
        if service is None and self.project.is_type('github'):
            service = 'github'
        if service is None and self.project.is_type('gitlab'):
            service = 'gitlab'
        if api_endpoint is None and service == 'github':
            api_endpoint = self.github_api_status_endpoint
        if api_endpoint is None and service == 'gitlab':
            api_endpoint = self.gitlab_api_status_endpoint

        state, state_msg = self.state_data_for(service, state, state_msg)

        if state_msg is not None:
            extra_dict = dict(description=state_msg)

        token_data = self.project.external_auth_token
        if token_data.service != service:
            raise InvalidServiceTypeError(
                "Project has a '%s' OAuth token, rather than '%s'" % (
                    token_data.service,
                    service,
                ),
            )

        return OAUTH_APPS[service].post(
            api_endpoint,
            dict(state=state,
                 target_url=self.url_ext,
                 context='continuous-integration/dockci/%s' % context,
                 **extra_dict),
            format='json',
            token=(token_data.key, token_data.secret),
        )

    def send_email_notification(self):
        """
        Send email notification of the job result to the git author
        and committer
        """
        recipients = []
        if self.git_author_email:
            recipients.append('%s <%s>' % (
                self.git_author_name,
                self.git_author_email
            ))
        if self.git_committer_email:
            recipients.append('%s <%s>' % (
                self.git_committer_name,
                self.git_committer_email
            ))

        if recipients:
            subject = (
                "DockCI - {project_name} {notification}".format(
                    project_name=self.project.name,
                    notification=RESULT_NOTIFICATIONS[self.result],
                )
            )
            email = Message(
                recipients=recipients,
                subject=subject,
            )

            try:
                MAIL.send(email)

            except Exception:  # pylint:disable=broad-except
                rollbar.report_exc_info()
                logging.getLogger('dockci.mail').exception(
                    "Couldn't send email message"
                )
