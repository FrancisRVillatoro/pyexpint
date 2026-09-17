#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "Usage: $0 CAMPAIGN_ID" >&2; exit 2; fi
CAMPAIGN_ID="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"
RUN_DIR="$PYEXPINT_FSCRATCH_ROOT/runs/$CAMPAIGN_ID"
source "$RUN_DIR/campaign.env"
test ! -e "$RUN_DIR/metadata/jobid.txt" || { echo "Job already recorded." >&2; exit 3; }
cd "$RUN_DIR"
JOBID_RAW=$(sbatch --parsable \
  --job-name=pyx_smoke \
  --partition="$PYEXPINT_PARTITION" \
  --constraint="$PYEXPINT_CONSTRAINT" \
  --nodes=1 --ntasks=1 --cpus-per-task=1 \
  --mem=4G --time=00:30:00 --array=0 \
  --output="$RUN_DIR/logs/pyexpint_%A_%a.out" \
  --error="$RUN_DIR/logs/pyexpint_%A_%a.err" \
  --export="ALL,PYEXPINT_CAMPAIGN_ID=$CAMPAIGN_ID,PYEXPINT_RUN_DIR=$RUN_DIR,PYEXPINT_RUNTIME=$PYEXPINT_RUNTIME,PYEXPINT_SOURCE_MANIFEST_SHA256=$PYEXPINT_SOURCE_MANIFEST_SHA256,PYEXPINT_PYTHON_MODULE=$PYEXPINT_PYTHON_MODULE,PYEXPINT_PYTHON=$PYEXPINT_PYTHON,PYEXPINT_MIN_PYTHON=$PYEXPINT_MIN_PYTHON,PYEXPINT_MIN_NUMPY=$PYEXPINT_MIN_NUMPY,PYEXPINT_MIN_SCIPY=$PYEXPINT_MIN_SCIPY" \
  "$RUN_DIR/slurm/prerelease_cpu_array.slurm")
JOBID="${JOBID_RAW%%;*}"
echo "$JOBID" > "$RUN_DIR/metadata/jobid.txt"
echo "1" > "$RUN_DIR/metadata/expected_cases.txt"
echo "array" > "$RUN_DIR/metadata/job_kind.txt"
echo "$JOBID" > "$PYEXPINT_HOME_ROOT/state/${CAMPAIGN_ID}.jobid"
date -Is > "$RUN_DIR/metadata/submitted_at.txt"
echo "SMOKE_SUBMITTED campaign=$CAMPAIGN_ID jobid=$JOBID expected_cases=1"
