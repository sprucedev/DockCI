[![Build Status](https://demo.dock.ci/project/dockci.svg)](https://demo.dock.ci/projects/dockci)[![Requirements Status](https://requires.io/github/sprucedev/DockCI/requirements.svg?branch=master&style=flat-square)](https://requires.io/github/sprucedev/DockCI/requirements/?branch=master)[![Tickets in Release](https://badge.waffle.io/rickycook/dockci.svg?label=ready&title=This Release)](http://waffle.io/sprucedev/dockci)

# DockCI
DockCI is still alpha! It's certainly not feature complete.  It's heading towards MVP.

## What is DockCI?
DockCI aims to be one of the missing links in a full Docker CI/CD pipeline.
Currently, most people are testing and deploying containers via build tools
like Jenkins and Bamboo, but these tools were not made for your containerized
new world. The idea of build agents with all your build tools is outdated, the
idea of build steps in your CI config is outdated!

Builds are getting more and more complex, and the old way of approaching CI is
not keeping up. This is what DockCI aims to solve. DockCI's goals are:

1. Configured only via project git repo
1. Minimal custom CI interface
1. Allow effortless, on-demand provisioning of dependant services

Lofty goals! Some might say. But, the tools are already out there. All DockCI
does is pull together some ideas and technologies to help us out.

Sounds great, right? And it will be! But it's not ready yet! Soooooo read on ;D

## Requirements
 - Docker 1.6.0 (others may work)
 - Python 3.4 (may work with 3.x, but untested)
 - PostgreSQL
 - Redis
 - RabbitMQ

## Setup

### [Docker Toolbox](https://www.docker.com/toolbox)

Registry steps are optional. If you do not want to use a registry at all, you
may disable registry support in the config page when DockCI is running.

1. Install git
1. Install the [Docker Toolbox](https://www.docker.com/toolbox)
1. Create a new Docker machine (or reuse an existing one): `docker-machine create default`
   - For insecure private registry support, add `--engine-insecure-registry http://localhost:5000`
   - For VMWare Fusion, add `--driver vmwarefusion`
   - The full command for OSX is: `docker-machine create --driver vmwarefusion --engine-insecure-registry http://localhost:5000 default`
1. Source the new machine configuration: `eval "$(docker-machine env default)"`
1. Clone the DockCI repo: `git clone https://github.com/sprucedev/DockCI.git`
1. Change directory to the DockCI directory, and use compose to bring up the stack: `docker-compose up`
1. You can get the URL to your new installation with: `echo http://$(docker-machine ip default):5001`
1. You can reset all your data at any time with: `docker-compose rm`

### Notes for non-dev setups

- You can specify a Postgresql database with the `DOCKCI_DB_URI` environment variable
- You can specify a Redis host with the `REDIS_PORT_6379_ADDR` environment variable
- You can specify a RabbitMQ host with the `RABBITMQ_PORT_5672_TCP_ADDR` environment variable
- You can specify a RabbitMQ user/password for the front end (public), and back end (private) with the `RABBITMQ_ENV_FRONTEND_USER`, `RABBITMQ_ENV_FRONTEND_PASSWORD`, `RABBITMQ_ENV_BACKEND_USER` and `RABBITMQ_ENV_FRONTEND_PASSWORD` environment variables (the default for all is `guest`)
- The `manage.py` script is used to execute commands on the DockCI install
- **Example full run command:** `DOCKCI_DB_URI=postgres://dockciuser:dockcipass@localhost:5432/dbname ./manage.py run --db-migrate --timeout 15 --bind 0.0.0.0:5000`

## Contributing
If you want to help DockCI see the light of day, pull requests are certainly
accepted! You can probably find something that you can work on in the
[GitHub issues](https://github.com/sprucedev/DockCI/issues). There's also a
[waffle.io project board](https://waffle.io/rickycook/dockci) with issues
ranked (approximately) highest to lowest priority. Just choose something that
isn't already labeled as `in progress`, or already has someone assigned to it
([here's a filter](https://github.com/sprucedev/DockCI/issues?q=is%3Aopen+is%3Aissue+no%3Aassignee+-label%3A%22in+progress%22+)).

The main code base is also really hastily written, so anything that you'd like
to refactor, got nuts! It _really_ needs to be done!

All pull requests must completely pass PEP8 and 10/10 with the pylint config
given. You can check this with `make test` (that's what Travis does too). No
green CI, no merge!

Make sure you update the CHANGELOG.md with any changes you make, including the
pull request number so that we can easily track changes between versions.
You'll obviously need to create the pull request, then update the changelog to
add the PR number.

If you want to have a talk about ideas, project priorities, etc feel free to
drop me an email at mail[at]thatpanda.com.

## Useful issues filters
- [Ticket type unlabeled](https://github.com/sprucedev/DockCI/issues?q=is%3Aissue+is%3Aopen+-label%3Abug+-label%3Aenhancement+-label%3Atask)
- [Things to work on](https://github.com/sprucedev/DockCI/issues?q=is%3Aopen+is%3Aissue+no%3Aassignee+-label%3A%22in+progress%22+)
