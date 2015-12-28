#!/bin/bash
set -e

THIS_DIR="$(cd "$(dirname "$0")"; pwd)"
source "$THIS_DIR/python_env/bin/activate"

if [[ -x "$THIS_DIR/pre-entry.sh" ]]; then
  echo "Sourcing pre-entry script" >&2
  source "$THIS_DIR/pre-entry.sh"
else
  echo "Skipping pre-entry script" >&2
fi

python "$THIS_DIR/manage.py" "$@"
