import datetime
import re

import pytest

from dockci.models.job import Job
from dockci.models.project import Project
from dockci.server import DB


def create_project(slug, **kwargs):
    """ Create a ``Project`` with defaults """
    final_kwargs = dict(
        name=slug,
        slug=slug,
        utility=False,
        repo='test',
    )
    final_kwargs.update(kwargs)
    return Project(**final_kwargs)


def create_job(**kwargs):
    """ Create a ``Job`` with defaults """
    final_kwargs = dict(
        repo_fs='test',
        commit='test',
    )
    final_kwargs.update(kwargs)
    return Job(**final_kwargs)


class TestProjectsSummary(object):
    """ Ensure ``Project.get_status_summary`` behaves as expected """

    @pytest.mark.parametrize('models,p_filters,exp_s,exp_f,exp_b', [
        (
            (
                (create_project('p1'),              create_job(result='success')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job()),
            ),
            None,
            1, 0, 0,
        ),
        (
            (
                (create_project('p1'),              create_job()),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            None,
            1, 0, 0,
        ),
        (
            (
                (create_project('p1'),              create_job(result='success')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            None,
            2, 0, 0,
        ),
        (
            (
                (create_project('p1'),              create_job(result='fail')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            None,
            1, 1, 0,
        ),
        (
            (
                (create_project('p1'),              create_job(result='broken')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            None,
            1, 0, 1,
        ),
        (
            (
                (create_project('p1'),              create_job(result='broken')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            {'utility': False},
            0, 0, 1,
        ),
        (
            (
                (create_project('p1'),              create_job(result='broken')),
                (create_project('p2'),              create_job()),
                (create_project('u', utility=True), create_job(result='success')),
            ),
            {'utility': True},
            1, 0, 0,
        ),
    ])
    def test_it(self, db, models, p_filters, exp_s, exp_f, exp_b):
        """ Commit models, assert status summary is accurate """
        for project, *jobs in models:
            DB.session.add(project)
            for job in jobs:
                job.project = project
                DB.session.add(job)

        DB.session.commit()

        assert Project.get_status_summary(p_filters) == dict(
            success=exp_s,
            fail=exp_f,
            broken=exp_b,
        )
