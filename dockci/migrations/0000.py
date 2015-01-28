"""
Create the basic data dir structure
"""
import os


def make_dir(directory):
    """
    Make a directory path if it doesn't exist
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

make_dir('data/builds')
make_dir('data/jobs')
