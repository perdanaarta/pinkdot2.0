#!/usr/bin/bash
 
set -e

home="$(dirname "$0")/.."

source $home/.env
source $home/.venv/bin/activate

python="python$PYTHON_VERSION"

$python $home/src/main.py