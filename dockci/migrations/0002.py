"""
Migrate config to docker hosts list
"""
import os
import sys
import yaml


filename = os.path.join('data', 'configs.yaml')
try:
    with open(filename) as handle:
        data = yaml.load(handle)
except FileNotFoundError:
    # This is fine; will fail for new installs
    sys.exit(0)

host = data.pop('docker_host')
data['docker_hosts'] = [host]

with open(filename, 'w') as handle:
    yaml.dump(data, handle, default_flow_style=False)
