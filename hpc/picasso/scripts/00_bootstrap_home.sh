#!/usr/bin/env bash
set -euo pipefail

ROOT="${PYEXPINT_HOME_ROOT:-$HOME/pyexpint_toms}"
mkdir -p \
  "$ROOT/incoming" \
  "$ROOT/repo" \
  "$ROOT/snapshots" \
  "$ROOT/ops" \
  "$ROOT/docs" \
  "$ROOT/external/snapshots" \
  "$ROOT/containers/defs" \
  "$ROOT/containers/images" \
  "$ROOT/containers/manifests" \
  "$ROOT/results/campaigns" \
  "$ROOT/manifests" \
  "$ROOT/state"

echo "Created persistent PyEXPINT root:"
echo "  $ROOT"
echo
echo "HOME is persistent. Do not run benchmarks here."
