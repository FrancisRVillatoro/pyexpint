#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"

echo "HOME_ROOT=$PYEXPINT_HOME_ROOT"
echo "FSCRATCH_ROOT=$PYEXPINT_FSCRATCH_ROOT"
echo "RUNTIME=$PYEXPINT_RUNTIME"
echo "PARTITION=$PYEXPINT_PARTITION"
echo "CONSTRAINT=$PYEXPINT_CONSTRAINT"
echo "MODULE=$PYEXPINT_PYTHON_MODULE"
echo "PYTHON_COMMAND=$PYEXPINT_PYTHON"

test -d "$PYEXPINT_HOME_ROOT"
mkdir -p "$PYEXPINT_FSCRATCH_ROOT/runs"
test -w "$PYEXPINT_FSCRATCH_ROOT"

module purge
module load "$PYEXPINT_PYTHON_MODULE"

echo "PYTHON_PATH=$(command -v "$PYEXPINT_PYTHON")"
echo

PYTHONPATH="$PYEXPINT_HOME_ROOT/repo/src${PYTHONPATH:+:$PYTHONPATH}" \
"$PYEXPINT_PYTHON" "$HERE/python/check_runtime.py" \
  --source "$PYEXPINT_HOME_ROOT/repo/src" \
  --smoke

echo
echo "Quota snapshot:"
quota 2>/dev/null || true
echo
echo "Environment check OK. No benchmark was executed on the login node."
