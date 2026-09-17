#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 CAMPAIGN_ID" >&2
  exit 2
fi
CAMPAIGN_ID="$1"

# Never allow an empty/unsafe campaign ID.  This prevents RUN_DIR from becoming
# the shared .../runs/ directory itself.
if [[ -z "$CAMPAIGN_ID" ]]; then
  echo "ERROR: CAMPAIGN_ID is empty." >&2
  echo "Example: cpu2d_intel_v081a_20260829a" >&2
  exit 2
fi
if [[ ! "$CAMPAIGN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{2,80}$ ]]; then
  echo "ERROR: invalid CAMPAIGN_ID: $CAMPAIGN_ID" >&2
  echo "Allowed: letters, digits, dot, underscore, hyphen; length 3..81." >&2
  exit 2
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"

HOME_ROOT="$PYEXPINT_HOME_ROOT"
RUNS_ROOT="$PYEXPINT_FSCRATCH_ROOT/runs"
RUN_DIR="$RUNS_ROOT/$CAMPAIGN_ID"

mkdir -p "$RUNS_ROOT"

# Belt-and-suspenders safety check.
if [[ "$RUN_DIR" == "$RUNS_ROOT" || "$RUN_DIR" == "$RUNS_ROOT/" ]]; then
  echo "ERROR: refusing unsafe RUN_DIR=$RUN_DIR" >&2
  exit 2
fi

if [[ -e "$RUN_DIR" ]]; then
  echo "Refusing to overwrite existing run: $RUN_DIR" >&2
  exit 3
fi
if [[ ! -f "$HOME_ROOT/repo/pyproject.toml" ]]; then
  echo "Missing active source tree: $HOME_ROOT/repo" >&2
  exit 4
fi

# Use exactly the same configured interpreter and the same canonical runtime
# checker used by login validation and Slurm jobs.
module purge
module load "$PYEXPINT_PYTHON_MODULE"

PYTHONPATH="$HOME_ROOT/repo/src${PYTHONPATH:+:$PYTHONPATH}" \
"$PYEXPINT_PYTHON" "$HOME_ROOT/ops/python/check_runtime.py" \
  --source "$HOME_ROOT/repo/src" \
  --smoke

mkdir -p "$RUN_DIR"/{code,ops/python,slurm,logs,results/raw,metadata,tmp}

rsync -a --delete \
  --exclude '.git/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
  --exclude '*.pyc' --exclude 'results/' \
  "$HOME_ROOT/repo/" "$RUN_DIR/code/"

rsync -a "$HOME_ROOT/ops/python/" "$RUN_DIR/ops/python/"
rsync -a "$HOME_ROOT/ops/slurm/" "$RUN_DIR/slurm/"

MANIFEST="$RUN_DIR/metadata/source_manifest.sha256"
SOURCE_SHA="$("$PYEXPINT_PYTHON" "$HOME_ROOT/ops/python/make_source_manifest.py" "$RUN_DIR/code" "$MANIFEST")"

cat > "$RUN_DIR/campaign.env" <<EOC
export PYEXPINT_CAMPAIGN_ID='$CAMPAIGN_ID'
export PYEXPINT_RUN_DIR='$RUN_DIR'
export PYEXPINT_HOME_ROOT='$HOME_ROOT'
export PYEXPINT_RUNTIME='$PYEXPINT_RUNTIME'
export PYEXPINT_SOURCE_MANIFEST_SHA256='$SOURCE_SHA'
export PYEXPINT_PYTHON_MODULE='$PYEXPINT_PYTHON_MODULE'
export PYEXPINT_PYTHON='$PYEXPINT_PYTHON'
export PYEXPINT_MIN_PYTHON='$PYEXPINT_MIN_PYTHON'
export PYEXPINT_MIN_NUMPY='$PYEXPINT_MIN_NUMPY'
export PYEXPINT_MIN_SCIPY='$PYEXPINT_MIN_SCIPY'
EOC

if [[ "$PYEXPINT_RUNTIME" == "sif" ]]; then
  SIF_HOME="$HOME_ROOT/containers/images/$PYEXPINT_SIF_NAME"
  test -f "$SIF_HOME" || { echo "Missing SIF: $SIF_HOME" >&2; exit 5; }
  mkdir -p "$PYEXPINT_FSCRATCH_ROOT/runtime"
  SIF_FS="$PYEXPINT_FSCRATCH_ROOT/runtime/$PYEXPINT_SIF_NAME"
  rsync -a "$SIF_HOME" "$SIF_FS"
  echo "export PYEXPINT_SIF_PATH='$SIF_FS'" >> "$RUN_DIR/campaign.env"
  echo "export PYEXPINT_APPTAINER='$PYEXPINT_APPTAINER'" >> "$RUN_DIR/campaign.env"
fi

cp "$RUN_DIR/campaign.env" "$RUN_DIR/metadata/campaign.env"
date -Is > "$RUN_DIR/metadata/staged_at.txt"

printf '%s\n' "$PYEXPINT_PYTHON_MODULE" > "$RUN_DIR/metadata/python_module.txt"
"$PYEXPINT_PYTHON" -V > "$RUN_DIR/metadata/python_version.txt" 2>&1

echo "STAGED"
echo "campaign : $CAMPAIGN_ID"
echo "run dir  : $RUN_DIR"
echo "runtime  : $PYEXPINT_RUNTIME"
echo "module   : $PYEXPINT_PYTHON_MODULE"
echo "src hash : $SOURCE_SHA"
echo
echo "Next: choose exactly one campaign role:"
echo "  smoke:       bash $HOME_ROOT/ops/scripts/03_submit_smoke.sh $CAMPAIGN_ID"
echo "  pilot array: bash $HOME_ROOT/ops/scripts/03_submit_pilot_array.sh $CAMPAIGN_ID"
echo "  TOMS timing: bash $HOME_ROOT/ops/scripts/03_submit_toms_timing.sh $CAMPAIGN_ID"
