[![Build Status](https://travis-ci.org/RickyCook/DockCI.svg)](https://travis-ci.org/RickyCook/DockCI)[![Requirements Status](https://requires.io/github/RickyCook/DockCI/requirements.svg?branch=master)](https://requires.io/github/RickyCook/DockCI/requirements/?branch=master)

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
 - Docker 1.15
 - Python 3.4 (may work with 3.x, but untested)

## System setup

### Ubuntu

- Ubuntu Trusty64 (DockCi and Docker on same machine)

### Install pre reqs
```sh
$ apt-get install git
$ apt-get install docker.io
$ apt-get install python-virtualenv
```

As bower doesn't like npm and node installed as root, you will need to install it via
https://gist.github.com/isaacs/579814#file-node-and-npm-in-30-seconds-sh

### Add your user to the docker group
```sh
$ usermod -G docker dockci_user
```

### Run DockCI
```sh
git clone https://github.com/RickyCook/DockCI.git
cd DockCI
make deps
source python_env/bin/activate
make run
```

## Contributing
If you want to help DockCI see the light of day, pull requests are certainly
accepted! You can probably find something that you can work on on the Trello
project board: https://trello.com/b/zaFPjsli . These are listed in highest to
lowest priority.

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
