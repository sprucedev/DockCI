"""
Migrate jobs from UUID1 slugs to new time-based slugs
"""
import os
import shutil
import yaml


def new_build_slug(create_ts):
    """
    Create a new style build slug from a creation timestamp
    """
    return hex(int(create_ts.timestamp() * 10000))[2:]

job_dirs = (
    filename for filename in
    os.listdir(os.path.join('data', 'builds'))
    if os.path.isdir(os.path.join('data', 'builds', filename))
)
for job_dir in job_dirs:
    build_files = (
        filename for filename in
        os.listdir(os.path.join('data', 'builds', job_dir))
        if filename[-5:] == '.yaml'
    )
    for build_file in build_files:
        build_slug = build_file[:-5]
        root_path = ('data', 'builds', job_dir)

        output_dir = "%s_output" % build_slug
        build_file_path = os.path.join(*root_path + (build_file,))
        output_dir_path = os.path.join(*root_path + (output_dir,))

        with open(build_file_path) as handle:
            build_dict = yaml.load(handle)

        new_slug = new_build_slug(build_dict['create_ts'])
        print("Changing '%s' build slug '%s' to '%s'" % (
            job_dir, build_slug, new_slug
        ))

        new_build_file = '%s.yaml' % new_slug
        new_output_dir = '%s_output' % new_slug
        new_build_file_path = os.path.join(*root_path + (new_build_file,))
        new_output_dir_path = os.path.join(*root_path + (new_output_dir,))

        if os.path.exists(output_dir_path):
            shutil.move(output_dir_path, new_output_dir_path)

        shutil.move(build_file_path, new_build_file_path)
