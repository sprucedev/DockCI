"""
Job stages that occur after a job is complete
"""

import docker

from dockci.models.job_meta.stages import JobStageBase, DockerStage
from dockci.exceptions import DockerAPIError, StageFailedError
from dockci.server import CONFIG
from dockci.util import (bytes_human_readable,
                         FauxDockerLog,
                         stream_write_status,
                         )


class PushStage(DockerStage):
    """
    Push the built container to the Docker registry, if versioned and
    configured
    """

    slug = 'docker_push'

    def _login_gen(self):
        """
        Generator for the login process to output actions, and their results in
        docker JSON log format
        """
        faux_log = FauxDockerLog()
        with faux_log.more_defaults(id="Logging in"):
            yield next(faux_log.update())
            try:
                response = self.job.docker_client.login(
                    username=CONFIG.docker_registry_username,
                    password=CONFIG.docker_registry_password,
                    email=CONFIG.docker_registry_email,
                    registry=CONFIG.docker_registry,
                    reauth=True,
                )
                yield next(faux_log.update(status=response['Status']))
            except docker.errors.APIError as ex:
                message = str(DockerAPIError(self.job.docker_client, ex))
                yield next(faux_log.update(status="FAILED", error=message))

                raise StageFailedError(message=message, handled=True)

    def _runnable_docker_gen(self):
        """ Generator to chain ``login_gen`` and push outputs """
        if (
            (
                CONFIG.docker_registry_username is not None and
                CONFIG.docker_registry_username != ''
            ) or (
                CONFIG.docker_registry_password is not None and
                CONFIG.docker_registry_password != ''
            ) or (
                CONFIG.docker_registry_email is not None and
                CONFIG.docker_registry_email != ''
            )
        ):
            for line in self._login_gen():
                yield line

        # TODO docker giving back a {"error": .., "errorDetail"..} doesn't fail
        for line in self.job.docker_client.push(
            self.job.docker_image_name,
            tag=self.job.tag,
            stream=True,
            insecure_registry=CONFIG.docker_registry_insecure,
        ):
            yield line

    def runnable_docker(self):
        """
        Perform the actual Docker push operation
        """
        if self.job.tag and CONFIG.docker_use_registry:
            return self._runnable_docker_gen()


class FetchStage(JobStageBase):
    """
    Fetches any output specified in job config
    """

    slug = 'docker_fetch'

    def runnable(self, handle):
        """
        Fetch/save the files
        """
        # pylint:disable=no-member
        mappings = self.job.job_config.job_output.items()
        for key, docker_fn in mappings:
            handle.write(
                ("Fetching %s from '%s'..." % (key, docker_fn)).encode()
            )
            resp = self.job.docker_client.copy(
                self.job.container_id, docker_fn,
            )

            if 200 <= resp.status < 300:
                output_path = self.job.job_output_path().join(
                    '%s.tar' % key
                )
                with output_path.open('wb') as output_fh:
                    # TODO stream so that not buffered in RAM
                    bytes_written = output_fh.write(resp.data)

                handle.write(
                    (" DONE! %s total\n" % (
                        bytes_human_readable(bytes_written)
                    )).encode(),
                )

            else:
                handle.write(
                    (" FAIL! HTTP status %d: %s\n" % (
                        resp.status_code, resp.reason
                    )).encode(),
                )
                return 1

        # Output something on no output
        if not mappings:
            handle.write("No output files to fetch".encode())

        return 0


class CleanupStage(JobStageBase):
    """
    Clean up after the job/test
    """

    slug = 'cleanup'

    def runnable(self, handle):
        """
        Do the image/container cleanup
        """
        def cleanup_context(object_type, object_id):
            """
            Get a stream_write_status context manager with messages set
            correctly
            """
            return stream_write_status(
                handle,
                "Cleaning up %s '%s'..." % (object_type, object_id),
                "DONE!",
                "FAILED!",
            )

        if self.job.container_id:
            with cleanup_context('container', self.job.container_id):
                self.job.docker_client.remove_container(
                    self.job.container_id,
                )

        # pylint:disable=protected-access
        if self.job._provisioned_containers:
            for service_info in self.job._provisioned_containers:
                ctx = cleanup_context('provisioned container',
                                      service_info['id'])
                with ctx:
                    self.job.docker_client.remove_container(
                        service_info['id'],
                        force=True,
                    )

        # Only clean up image if this is an non-tagged job
        if self.job.tag is None or self.job.result in ('broken', 'fail'):
            if self.job.image_id:
                with cleanup_context('image', self.job.image_id):
                    self.job.docker_client.remove_image(self.job.image_id)

        # TODO catch failures
        return 0
