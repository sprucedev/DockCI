#!/bin/bash
case $1 in
    collectstatic) collectstatic ;;
    pythondeps) pythondeps ;;
    ci) ci ;;
    *)
        echo "Unknown command '$1'" >&2
        exit 1
esac

function collectstatic {
    mkdir -p dockci/static/lib/css
    mkdir -p dockci/static/lib/fonts
    mkdir -p dockci/static/lib/js
    ./_collect_static.sh; exit $?
}
function pythondeps {
    python3.4 -m virtualenv -p $(shell which python3.4) python_env
    python_env/bin/pip install -r requirements.txt
}
function testdeps {
    pythondeps
    python_env/bin/pip install -r test-requirements.txt
}
function styletest {
    python_env/bin/pep8 dockci
    python_env/bin/pylint --rcfile pylint.conf dockci
}
function unittest {
    export PYTHONPATH = $(shell pwd)
    python_env/bin/py.test -vv tests
}
function tests {
    styletest
    unittest
}
function ci {
    testdeps
    tests
}
