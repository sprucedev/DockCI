import re

import pytest

from dockci.models.auth import AuthenticatedRegistry
from dockci.models.job import (Job,
                               JobResult,
                               PushableReasons,
                               UnpushableReasons,
                               )
from dockci.models.project import Project


class TestJobPushables(object):
    """ Test the pushable checks """

    @pytest.mark.parametrize('method,kwargs,exp_bool,exp_reasons', [
        (
          'tag_push_candidate',
          dict( project=Project()),
          False, {UnpushableReasons.no_target_registry},
        ),
        (
          'tag_push_candidate',
          dict(
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          False, {UnpushableReasons.no_tag},
        ),
        (
          'tag_push_candidate',
          dict(
              tag='tagged',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          True, {PushableReasons.tag_push},
        ),
        (
          'branch_push_candidate',
          dict(project=Project()),
          False, {UnpushableReasons.no_target_registry},
        ),
        (
          'branch_push_candidate',
          dict(
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          False, {UnpushableReasons.no_branch},
        ),
        (
          'branch_push_candidate',
          dict(
              git_branch='branch',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          False, {UnpushableReasons.no_branch_pattern},
        ),
        (
          'branch_push_candidate',
          dict(
              git_branch='branch',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
                  branch_pattern=re.compile('not this branch'),
              ),
          ),
          False, {UnpushableReasons.no_branch_match},
        ),
        (
          'branch_push_candidate',
          dict(
              git_branch='branch',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
                  branch_pattern=re.compile('branch'),
              ),
          ),
          True, {PushableReasons.branch_push},
        ),
        (
          'push_candidate',
          dict(
              tag='tagged',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          True, {PushableReasons.tag_push},
        ),
        (
          'push_candidate',
          dict(
              git_branch='branch',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
                  branch_pattern=re.compile('branch'),
              ),
          ),
          True, {PushableReasons.branch_push},
        ),
        (
          'push_candidate',
          dict(
              git_branch='branch',
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          False, {UnpushableReasons.no_tag,
                  UnpushableReasons.no_branch_pattern},
        ),
        (
          'pushable',
          dict(
              tag='tagged',
              exit_code=0,
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          True, {PushableReasons.tag_push,
                 PushableReasons.good_exit},
        ),
        (
          'pushable',
          dict(
              git_branch='branch',
              result=JobResult.success.value,
              project=Project(
                  target_registry=AuthenticatedRegistry(),
                  branch_pattern=re.compile('branch'),
              ),
          ),
          True, {PushableReasons.branch_push,
                 PushableReasons.result_success},
        ),
        (
          'pushable',
          dict(
              exit_code=0,
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          False, {UnpushableReasons.no_tag, UnpushableReasons.no_branch},
        ),
        (
          'pushable',
          dict(
              tag='tagged',
              result=JobResult.fail.value,
              project=Project(
                  target_registry=AuthenticatedRegistry(),
              ),
          ),
          False, {UnpushableReasons.not_good_state},
        ),
        (
          'pushable',
          dict(tag='tagged'),
          False, {UnpushableReasons.no_project},
        ),
    ])
    def test_methods(self, method, kwargs, exp_bool, exp_reasons):
        job = Job(**kwargs)

        assert getattr(job, method) == exp_bool

        full_result = getattr(job, '_%s_full' % method)
        assert full_result[0] == exp_bool
        assert full_result[1] == exp_reasons
