[![Build Status](https://travis-ci.org/RickyCook/DockCI.svg)](https://travis-ci.org/RickyCook/DockCI)[![Requirements Status](https://requires.io/github/RickyCook/DockCI/requirements.svg?branch=master)](https://requires.io/github/RickyCook/DockCI/requirements/?branch=master)

# DockCI
DOCKCI IS STILL VERY ALPHA!!! It's certainly not feature complete, nor even the
MVP (and really really hastily written). At the moment, it's less MVP and more
TUVP: Totally un-viable product.

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

If you want to have a talk about ideas, project priorities, etc feel free to
drop me an email at mail[at]thatpanda.com.
