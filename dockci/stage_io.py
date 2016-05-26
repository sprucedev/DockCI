""" IO for handling stage output/logging """

import logging
import warnings

from contextlib import contextmanager
from io import RawIOBase

import redis
import redis_lock

from dockci.server import CONFIG
from dockci.util import rabbit_stage_key


def redis_len_key(stage):
    """ Key for Redis value storing bytes saved """
    return 'dockci/{project_slug}/{job_slug}/{stage_slug}/bytes'.format(
        project_slug=stage.job.project.slug,
        job_slug=stage.job.slug,
        stage_slug=stage.slug,
    )


def redis_lock_name(job):
    """ Name of the lock for the job """
    return 'dockci/{project_slug}/{job_slug}/lock'.format(
        project_slug=job.project.slug,
        job_slug=job.slug,
    )


class StageIO(RawIOBase):
    """
    Handle IO for stage output. This includes total bytes count, handling
    locking, and sending data to any RabbitMQ queues that are needed

    Examples:

    >>> from dockci.models.project import Project
    >>> from dockci.models.job import Job
    >>> from dockci.models.job_meta.stages_main import ExternalStatusStage

    >>> project = Project(slug='testproj')
    >>> job = Job(id=0x2a, project=project)
    >>> stage = ExternalStatusStage(job, 'test')

    >>> StageIO(stage, redis_pool=None, pika_conn='not none')
    Traceback (most recent call last):
      ...
    ValueError: Can't write to a stage stream without Redis

    >>> StageIO(stage, redis_pool='not none', pika_conn=None)
    Traceback (most recent call last):
      ...
    ValueError: Can't write to a stage stream without RabbitMQ

    >>> StageIO(stage, redis_pool='not none', pika_conn='not none')
    <StageIO: ...>
    """
    def __init__(self, stage, redis_pool=None, pika_conn=None):
        if redis_pool is None:
            raise ValueError("Can't write to a stage stream without Redis")
        if pika_conn is None:
            raise ValueError("Can't write to a stage stream without RabbitMQ")

        self.stage = stage
        self.redis_pool = redis_pool
        self.pika_conn = pika_conn

        super(StageIO, self).__init__()

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
        return redis_len_key(self.stage)

    @property
    def redis_lock_name(self):
        """ Name of the lock for the job """
        return redis_lock_name(self.stage.job)

    @property
    def rabbit_content_key(self):
        """ RabbitMQ routing key for content messages """
        return rabbit_stage_key(self.stage, 'content')

    @property
    def bytes_saved(self):
        """ Number of bytes saved in a live log """
        return self.redis.get(self.redis_len_key)

    def write(self, data):
        """
        Obtain the stage lock, update the byte total, write to RMQ,
        release the stage lock
        """
        try:
            redis_conn = self.redis
            with redis_lock.Lock(
                redis_conn,
                self.redis_lock_name,
                expire=5,
            ):
                try:
                    my_redis_len_key = self.redis_len_key
                    redis_conn.setnx(my_redis_len_key, 0)
                    redis_conn.incr(my_redis_len_key, len(data))
                    redis_conn.expire(my_redis_len_key,
                                      CONFIG.redis_len_expire)

                except Exception:  # pylint:disable=broad-except
                    logging.exception("Error incrementing bytes written")

                try:
                    self.pika_channel.basic_publish(
                        exchange='dockci.job',
                        routing_key=self.rabbit_content_key,
                        body=data,
                    )

                except Exception:  # pylint:disable=broad-except
                    logging.exception("Error sending to queue")

        except Exception:  # pylint:disable=broad-except
            logging.exception("Error writing live logs")

    def flush(self):
        """ Deprecated flush placeholder to save exceptions """
        warnings.warn(
            "StageIO is no longer buffered. Flushing is unnecessary",
            DeprecationWarning,
        )

    def __repr__(self):
        """
        Examples:

        >>> from dockci.models.project import Project
        >>> from dockci.models.job import Job
        >>> from dockci.models.job_meta.stages_main import ExternalStatusStage

        >>> project = Project(slug='testproj')
        >>> job = Job(id=0x2a, project=project)
        >>> stage = ExternalStatusStage(job, 'test')

        >>> StageIO(stage, redis_pool='test', pika_conn='test')
        <StageIO: project=testproj, job=...2a, stage=...test>
        """
        return ('<{klass}: project={project_slug}, job={job_slug}, '
                'stage={stage_slug}>').format(
            klass=self.__class__.__name__,
            project_slug=self.stage.job.project.slug,
            job_slug=self.stage.job.slug,
            stage_slug=self.stage.slug,
        )
