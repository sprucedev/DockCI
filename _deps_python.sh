#!/bin/bash
set -e
set -x

: ${WHEELS_ONLY:=0}  # 0 is only use wheels

function env_create {
    python3 -m virtualenv -p $(which python3) python_env
}
function env_install_reqs {
    [[ -e python_env ]] || env_create
    if [[ $WHEELS_ONLY -eq 0 ]]; then
        python_env/bin/pip install --use-wheel --no-index --find-links=wheelhouse -r "$1"
    else
        python_env/bin/pip install -r "$1"
    fi
}
function pythondeps {
    env_install_reqs requirements.txt
    env_install_reqs test-requirements.txt
}

pythondeps
