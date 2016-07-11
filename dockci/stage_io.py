""" IO for handling stage output/logging """


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
