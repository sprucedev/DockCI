"""
Migrate version to tag in build models
"""
import os
import shutil
import yaml


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
        build_file_path = os.path.join('data', 'builds', job_dir, build_file)

        with open(build_file_path) as handle:
            build_dict = yaml.load(handle)

        try:
            version = build_dict.pop('version')
            if version:
                build_dict['tag'] = version

            with open(build_file_path, 'w') as handle:
                yaml.dump(build_dict, handle, default_flow_style=False)

        except KeyError:
            pass
