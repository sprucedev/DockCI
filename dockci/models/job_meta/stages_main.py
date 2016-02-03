"""
Main job stages that constitute a job
"""

import json

from subunit.v2 import ByteStreamToStreamResult

from dockci.models.base import ServiceBase
from dockci.models.job_meta.stages import JobStageBase, DockerStage
from dockci.util import built_docker_image_id


def parse_oauth_response(response):
    """ Parse a response from Flask-OAuthlib """
    return response.status, response.data


# UNUSED, but kept for non-oauth integrations
def parse_requests_response(response):
    """ Parse a response from requests """
    try:
        return response.status_code, response.json()

    except ValueError:
        return response.status_code, {}


# TODO should be a post stage, not main
class ExternalStatusStage(JobStageBase):
    """ Send the job status to external providers """

    def __init__(self, job, suffix):
        super(ExternalStatusStage, self).__init__(job)
        self.slug = 'external_status_%s' % suffix

    # TODO state, state_msg, context config via OO means
    # pylint:disable=no-self-use
    def _send_gitserv_status_stage(self,
                                   handle,
                                   service_name,
                                   service_method,
                                   response_parse,
                                   context='push'):
        """
        Update the GitHub/GitLab status for the project, handling feedback by
        writing to a log handle. Expected to be run from inside a stage in
        order to write to the job log
        """
        handle.write((
            "Submitting status to %s... " % service_name
        ).encode())
        handle.flush()
        response = service_method(context=context)

        status, data = response_parse(response)

        if status == 201:
            handle.write("DONE!\n".encode())
            handle.flush()
            return True

        else:
            handle.write("FAILED!\n".encode())
            handle.write(("%s\n" % data.get(
                'message',
                "Unexpected response from %s. HTTP status %d" % (
                    service_name,
                    status,
                )
            )).encode())
            handle.flush()
            return False

    def runnable(self, handle):
        # Externals to update is any set that doesn't have a None value for
        # it's repo id
        externals = filter(lambda pair: pair[1][0] is not None, {
            'GitHub': (self.job.project.github_repo_id,
                       self.job.send_github_status,
                       parse_oauth_response,
                       ),
            'GitLab': (self.job.project.gitlab_repo_id,
                       self.job.send_gitlab_status,
                       parse_oauth_response,
                       ),
        }.items())

        success = None
        for service_name, (_, service_method, response_parse) in externals:
            success = True if success is None else success
            success &= self._send_gitserv_status_stage(
                handle, service_name, service_method, response_parse,
            )

        if success is None:
            handle.write("No external providers with status updates "
                         "configured\n".encode())

        handle.flush()
        return 0 if success else 1


class BuildStage(DockerStage):
    """
    Tell the Docker host to job
    """

    slug = 'docker_build'

    def __init__(self, job, workdir):
        super(BuildStage, self).__init__(job)
        self.workdir = workdir
        self.tag = None
        self.no_cache = None

    @property
    def dockerfile(self):
        """ Dockerfile used to build """
        return self.job.job_config.dockerfile

    def get_services(self):
        """ Services for registries required by Dockerfile FROM """
        with self.workdir.join(self.dockerfile).open() as dockerfile_handle:
            for line in dockerfile_handle:
                line = line.strip()
                if line.startswith('FROM '):
                    return [ServiceBase.from_image(
                        line[5:].strip(),
                        name='Base Image',
                    )]

        return []

    def runnable_docker(self):
        """
        Determine the image tag, and cache flag value, then trigger a Docker
        image job, returning the output stream so that DockerStage can handle
        the output
        """
        # Don't use the docker caches if a version tag is defined
        no_cache = (self.job.tag is not None)

        return self.job.docker_client.build(path=self.workdir.strpath,
                                            dockerfile=self.dockerfile,
                                            nocache=no_cache,
                                            rm=True,
                                            stream=True)

    def on_done(self, line):
        """
        Check the final line for success, and image id
        """
        if line:
            if isinstance(line, bytes):
                line = line.decode()

            line_data = json.loads(line)
            self.job.image_id = built_docker_image_id(line_data)
            if self.job.image_id is not None:
                return 0

        return 1


class WrapIt(object):
    """
    Examples:

    >>> gen = iter([b'ab', b'cd', b'ef'])
    >>> stream = WrapIt(gen)
    >>> stream.read(2)
    b'ab'
    >>> stream.read(2)
    b'cd'
    >>> stream.read(2)
    b'ef'
    >>> stream.read(2)
    b''

    >>> gen = iter([b'ab', b'cd', b'ef'])
    >>> stream = WrapIt(gen)
    >>> stream.read(3)
    b'abc'
    >>> stream.read(3)
    b'def'
    >>> stream.read(3)
    b''

    >>> gen = iter([b'abcdef'])
    >>> stream = WrapIt(gen)
    >>> stream.read(3)
    b'abc'
    >>> stream.read(3)
    b'def'
    >>> stream.read(3)
    b''

    >>> gen = iter([b'a'])
    >>> stream = WrapIt(gen)
    >>> stream.read(3)
    b'a'
    """
    def __init__(self, gen):
        self.gen = gen
        self.buffer = b''

    def read(self, count=-1):
        """ Read stuff """
        read_total = len(self.buffer)
        while count == -1 or read_total < count:
            try:
                next_data = next(self.gen)
            except StopIteration:
                break

            read_total += len(next_data)
            self.buffer += next_data

        if count == -1:
            this_data = self.buffer
            self.buffer = b''
        else:
            this_data = self.buffer[:count]
            self.buffer = self.buffer[count:]

        return this_data


class TestStage(JobStageBase):
    """
    Tell the Docker host to run the CI command
    """

    slug = 'docker_test'

    def runnable(self, handle):
        """
        Check if we should skip tests before handing over to the
        ``DockerStage`` runnable to execute Docker-based tests
        """
        if self.job.job_config.skip_tests:
            # todo output subunit
            # handle.write("Skipping tests, as per configuration".encode())
            self.job.exit_code = 0
            self.job.db_session.add(self.job)
            self.job.db_session.commit()
            return 0

        container_details = self.job.docker_client.create_container(
            self.job.image_id, 'ci'
        )
        self.job.container_id = container_details['Id']
        self.job.db_session.add(self.job)
        self.job.db_session.commit()

        def link_tuple(service_info):
            """
            Turn our provisioned service info dict into an alias string for
            Docker
            """
            if 'name' not in service_info:
                service_info['name'] = \
                    self.job.docker_client.inspect_container(
                        service_info['id']
                    )['Name'][1:]  # slice to remove the / from start

            if 'alias' not in service_info:
                if isinstance(service_info['config'], dict):
                    service_info['alias'] = service_info['config'].get(
                        'alias',
                        service_info['service'].app_name
                    )

                else:
                    service_info['alias'] = service_info['service'].app_name

            return (service_info['name'], service_info['alias'])

        stream = self.job.docker_client.attach(
            self.job.container_id,
            stream=True,
        )
        self.job.docker_client.start(
            self.job.container_id,
            links=[
                link_tuple(service_info)
                # pylint:disable=protected-access
                for service_info in self.job._provisioned_containers
            ]
        )

        result = ByteStreamToStreamResult(
            WrapIt(stream),
            non_subunit_name='otherthings',
        )

        def prep_for_json(value):
            """ Encode bytes """
            try:
                return value.decode()

            except AttributeError:
                return value

        class DoIt(object):
            """ Do things """
            def status(self, **kwargs):  # pylint:disable=no-self-use
                """ Write a status to the stream """
                for k in kwargs.keys():
                    kwargs[k] = prep_for_json(kwargs[k])

                handle.write(json.dumps(kwargs).encode())
                handle.write(b'\n')

        result.run(DoIt())

    def on_done(self, _):
        """
        Check container exit code and return True on 0, or False otherwise
        """
        details = self.job.docker_client.inspect_container(
            self.job.container_id,
        )
        self.job.exit_code = details['State']['ExitCode']
        self.job.db_session.add(self.job)
        self.job.db_session.commit()
        return details['State']['ExitCode']
