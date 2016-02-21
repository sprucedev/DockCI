import datetime
import re

import pytest

from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import DB


def create_project(slug, **kwargs):
    final_kwargs = dict(
        name=slug,
        slug=slug,
        utility=False,
        repo='test',
    )
    final_kwargs.update(kwargs)
    return Project(**final_kwargs)


def create_job(**kwargs):
    final_kwargs = dict(
        repo_fs='test',
        commit='test',
    )
    final_kwargs.update(kwargs)
    return Job(**final_kwargs)


class TestProjectsSummary(object):
    @pytest.mark.parametrize('models,exp_s,exp_f,exp_b', [
        (
            (
                (create_project('p1'),              create_job(result='success')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job()),
            ),
            1, 0, 0,
        ),
        (
            (
                (create_project('p1'),              create_job()),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            1, 0, 0,
        ),
        (
            (
                (create_project('p1'),              create_job(result='success')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            2, 0, 0,
        ),
        (
            (
                (create_project('p1'),              create_job(result='fail')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            1, 1, 0,
        ),
        (
            (
                (create_project('p1'),              create_job(result='broken')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            1, 0, 1,
        ),
    ])
    def test_it(self, db, models, exp_s, exp_f, exp_b):
        for project, *jobs in models:
            DB.session.add(project)
            for job in jobs:
                job.project = project
                DB.session.add(job)

        DB.session.commit()

        assert Project.get_status_summary() == dict(
            success=exp_s,
            fail=exp_f,
            broken=exp_b,
        )
