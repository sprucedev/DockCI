#!/bin/bash
set -e
set -x

npm install
node_modules/bower/bin/bower --allow-root install
