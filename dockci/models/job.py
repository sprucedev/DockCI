"""
DockCI - CI, but with that all important Docker twist
"""

import os
import os.path

from dockci.util import is_yaml_file
from dockci.yaml_model import LoadOnAccess, Model, OnAccess


def all_jobs():
    """
    Get the list of jobs
    """
    try:
        for filename in os.listdir(os.path.join(*Job.data_dir_path())):
            full_path = Job.data_dir_path() + [filename]
            if is_yaml_file(os.path.join(*full_path)):
                job = Job(filename[:-5])
                yield job

    except FileNotFoundError:
        return


class Job(Model):  # pylint:disable=too-few-public-methods
    """
    A job, representing a container to be built
    """
    def __init__(self, slug=None):
        super(Job, self).__init__()
        self.slug = slug

    def _all_builds(self):
        """
        Get all the builds associated with this job
        """
        from dockci.models.build import Build

        try:
            my_data_dir_path = Build.data_dir_path()
            my_data_dir_path.append(self.slug)
            builds = []

            for filename in os.listdir(os.path.join(*my_data_dir_path)):
                full_path = Build.data_dir_path() + [self.slug, filename]
                if is_yaml_file(os.path.join(*full_path)):
                    builds.append(Build(job=self,
                                        slug=filename[:-5]))

            return builds

        except FileNotFoundError:
            return []

    slug = None
    repo = LoadOnAccess(default=lambda _: '')
    name = LoadOnAccess(default=lambda _: '')
    github_secret = LoadOnAccess(default=lambda _: None)
    builds = OnAccess(_all_builds)
