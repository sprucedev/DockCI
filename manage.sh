#!/bin/bash
function collectstatic {
    mkdir -p dockci/static/lib/css
    mkdir -p dockci/static/lib/fonts
    mkdir -p dockci/static/lib/js
    ./manage_collectstatic.sh; exit $?
}
function pythondeps {
    python3 -m virtualenv -p $(which python3) python_env
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
    export PYTHONPATH = $(pwd)
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
function shell {
    /bin/bash
}

case $1 in
    collectstatic) collectstatic ;;
    pythondeps) pythondeps ;;
    ci) ci ;;
    shell) shell ;;
    *)
        echo "Unknown command '$1'" >&2
        exit 1
esac
