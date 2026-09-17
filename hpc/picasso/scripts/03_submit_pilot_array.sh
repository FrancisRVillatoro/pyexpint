#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 CAMPAIGN_ID" >&2
  exit 2
fi
CAMPAIGN_ID="$1"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"
RUN_DIR="$PYEXPINT_FSCRATCH_ROOT/runs/$CAMPAIGN_ID"
source "$RUN_DIR/campaign.env"

cd "$RUN_DIR"
ARRAY="0-23%${PYEXPINT_ARRAY_THROTTLE}"

JOBID=$(sbatch --parsable \
  --partition="$PYEXPINT_PARTITION" \
  --constraint="$PYEXPINT_CONSTRAINT" \
  --mem="$PYEXPINT_MEM" \
  --time="$PYEXPINT_TIME" \
  --array="$ARRAY" \
  --output="$RUN_DIR/logs/pyexpint_%A_%a.out" \
  --error="$RUN_DIR/logs/pyexpint_%A_%a.err" \
  --export="ALL,PYEXPINT_CAMPAIGN_ID=$CAMPAIGN_ID,PYEXPINT_RUN_DIR=$RUN_DIR,PYEXPINT_RUNTIME=$PYEXPINT_RUNTIME,PYEXPINT_SOURCE_MANIFEST_SHA256=$PYEXPINT_SOURCE_MANIFEST_SHA256,PYEXPINT_PYTHON_MODULE=$PYEXPINT_PYTHON_MODULE,PYEXPINT_PYTHON=$PYEXPINT_PYTHON,PYEXPINT_MIN_PYTHON=$PYEXPINT_MIN_PYTHON,PYEXPINT_MIN_NUMPY=$PYEXPINT_MIN_NUMPY,PYEXPINT_MIN_SCIPY=$PYEXPINT_MIN_SCIPY${PYEXPINT_SIF_PATH:+,PYEXPINT_SIF_PATH=$PYEXPINT_SIF_PATH}${PYEXPINT_APPTAINER:+,PYEXPINT_APPTAINER=$PYEXPINT_APPTAINER}" \
  "$RUN_DIR/slurm/prerelease_cpu_array.slurm")

echo "$JOBID" > "$RUN_DIR/metadata/jobid.txt"
echo "24" > "$RUN_DIR/metadata/expected_cases.txt"
echo "array" > "$RUN_DIR/metadata/job_kind.txt"
echo "$JOBID" > "$PYEXPINT_HOME_ROOT/state/${CAMPAIGN_ID}.jobid"
date -Is > "$RUN_DIR/metadata/submitted_at.txt"

echo "PILOT_ARRAY_SUBMITTED campaign=$CAMPAIGN_ID jobid=$JOBID"
echo
echo "Monitor:"
echo "  bash $PYEXPINT_HOME_ROOT/ops/scripts/04_status_campaign.sh $CAMPAIGN_ID"
