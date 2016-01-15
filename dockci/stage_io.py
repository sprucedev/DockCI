""" IO for handling stage output/logging """

import logging

from contextlib import contextmanager
from io import FileIO

import redis


class StageIO(FileIO):
    """
    Handle IO for stage output. This includes writing the log file, updating
    the total bytes count, handling locking, and sending data to any RabbitMQ
    queues that are needed

    Examples:

    >>> test_path = getfixture('tmpdir')
    >>> old_path = test_path.chdir()
    >>> test_path.join('data', 'testproj', '00002a').ensure_dir()
    local('.../data/testproj/00002a')

    >>> from dockci.models.project import Project
    >>> from dockci.models.job import Job
    >>> from dockci.models.job_meta.stages_main import ExternalStatusStage

    >>> project = Project(slug='testproj')
    >>> job = Job(id=0x2a, project=project)
    >>> stage = ExternalStatusStage(job, 'test')

    >>> StageIO(stage, mode='wb', redis_pool=None, pika_conn='not none')
    Traceback (most recent call last):
      ...
    ValueError: Can't write to a stage stream without Redis

    >>> StageIO(stage, mode='wb', redis_pool='not none', pika_conn=None)
    Traceback (most recent call last):
      ...
    ValueError: Can't write to a stage stream without RabbitMQ

    >>> StageIO(stage, mode='wb', redis_pool='not none', pika_conn='not none')
    <StageIO: ...>

    >>> StageIO(stage, mode='rb', redis_pool=None, pika_conn=None)
    <StageIO: ...>

    >>> old_path.chdir()
    local(...)
    """
    def __init__(self, stage, mode='wb', redis_pool=None, pika_conn=None):
        if 'w' in mode and redis_pool is None:
            raise ValueError("Can't write to a stage stream without Redis")
        if 'w' in mode and pika_conn is None:
            raise ValueError("Can't write to a stage stream without RabbitMQ")

        self.stage = stage
        self.redis_pool = redis_pool
        self.pika_conn = pika_conn

        super(StageIO, self).__init__(
            self._log_path.strpath,
            mode=mode,
        )

    @classmethod
    @contextmanager
    def open(cls, stage, mode='wb', redis_pool=None, pika_conn=None):
        """
        Context manager for getting a stage log

        Examples:

        >>> test_path = getfixture('tmpdir')
        >>> old_path = test_path.chdir()
        >>> test_path.join('data', 'testproj', '00002a').ensure_dir()
        local('.../data/testproj/00002a')

        >>> from dockci.models.project import Project
        >>> from dockci.models.job import Job
        >>> from dockci.models.job_meta.stages_main import ExternalStatusStage

        >>> project = Project(slug='testproj')
        >>> job = Job(id=0x2a, project=project)
        >>> stage = ExternalStatusStage(job, 'test')

        >>> with StageIO.open(stage, redis_pool='red', pika_conn='pika') as h:
        ...     h.pika_conn
        'pika'

        >>> with StageIO.open(stage, redis_pool='red', pika_conn='pika') as h:
        ...     h.redis_pool
        'red'

        >>> with StageIO.open(stage, mode='rb') as h:
        ...     h.mode
        'rb'
        """
        handle = cls(
            stage,
            mode=mode,
            redis_pool=redis_pool,
            pika_conn=pika_conn,
        )
        try:
            yield handle
        finally:
            handle.close()

    @property
    def _log_path(self):
        """
        Path to the stage log being written

        Examples:

        >>> test_path = getfixture('tmpdir')
        >>> old_path = test_path.chdir()
        >>> test_path.join('data', 'testproj', '00002a').ensure_dir()
        local('.../data/testproj/00002a')

        >>> from dockci.models.project import Project
        >>> from dockci.models.job import Job
        >>> from dockci.models.job_meta.stages_main import ExternalStatusStage

        >>> project = Project(slug='testproj')
        >>> job = Job(id=0x2a, project=project)
        >>> stage = ExternalStatusStage(job, 'test')

        >>> StageIO(stage, redis_pool='test', pika_conn='test')._log_path
        local('.../testproj/00002a/external_status_test.log')

        >>> old_path.chdir()
        local(...)
        """
        return self.stage.job.job_output_path().join(
            '%s.log' % self.stage.slug
        )

    _redis = None

    @property
    def redis(self):
        """ Get a Redis object """
        if self._redis is None:
            self._redis = redis.Redis(connection_pool=self.redis_pool)

        return self._redis

    _pika_channel = None

    @property
    def pika_channel(self):
        """ Get the RabbitMQ channel """
        if self._pika_channel is None:
            self._pika_channel = self.pika_conn.channel()

        return self._pika_channel


    @property
    def redis_len_key(self):
        """ Key for Redis value storing bytes saved """
        return 'dockci/{project_slug}/{job_slug}/{stage_slug}/bytes'.format(
            project_slug=self.stage.job.project.slug,
            job_slug=self.stage.job.slug,
            stage_slug=self.stage.slug,
        )

    @property
    def rabbit_content_key(self):
        """ RabbitMQ routing key for content messages """
        return 'dockci.{project_slug}.{job_slug}.{stage_slug}.content'.format(
            project_slug=self.stage.job.project.slug,
            job_slug=self.stage.job.slug,
            stage_slug=self.stage.slug,
        )

    @property
    def bytes_saved(self):
        """ Number of bytes saved in a live log """
        return self.redis.get(self.redis_len_key)

    def write(self, data):
        """
        Obtain the stage lock, update the byte total, write to RMQ,
        write to file, release the stage lock
        """
        super(StageIO, self).write(data)
        try:
            redis = self.redis
            redis_len_key = self.redis_len_key
            # TODO expiry
            redis.setnx(redis_len_key, 0)
            redis.incr(redis_len_key, len(data))

        except Exception:
            logging.exception("Error incrementing bytes written")

        try:
            self.pika_channel.basic_publish(
                exchange='dockci.job',
                routing_key=self.rabbit_content_key,
                body=data,
            )

        except Exception:
            logging.exception("Error sending to queue")

    def __repr__(self):
        """
        Examples:

        >>> test_path = getfixture('tmpdir')
        >>> old_path = test_path.chdir()
        >>> test_path.join('data', 'testproj', '00002a').ensure_dir()
        local('.../data/testproj/00002a')

        >>> from dockci.models.project import Project
        >>> from dockci.models.job import Job
        >>> from dockci.models.job_meta.stages_main import ExternalStatusStage

        >>> project = Project(slug='testproj')
        >>> job = Job(id=0x2a, project=project)
        >>> stage = ExternalStatusStage(job, 'test')

        >>> StageIO(stage, mode='wb', redis_pool='test', pika_conn='test')
        <StageIO: project=testproj, job=...2a, stage=...test, mode=wb>
        """
        return ('<{klass}: project={project_slug}, job={job_slug}, '
                'stage={stage_slug}, mode={mode}>').format(
            klass=self.__class__.__name__,
            project_slug=self.stage.job.project.slug,
            job_slug=self.stage.job.slug,
            stage_slug=self.stage.slug,
            mode=self.mode,  # pylint:disable=no-member
        )
