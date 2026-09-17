#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "Usage: $0 CAMPAIGN_ID" >&2; exit 2; fi
CAMPAIGN_ID="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"
RUN_DIR="$PYEXPINT_FSCRATCH_ROOT/runs/$CAMPAIGN_ID"
JOBFILE="$PYEXPINT_HOME_ROOT/state/${CAMPAIGN_ID}.jobid"
test -d "$RUN_DIR" || { echo "Missing run dir: $RUN_DIR" >&2; exit 3; }
test -f "$JOBFILE" || { echo "Missing jobid file: $JOBFILE" >&2; exit 4; }
JOBID="$(cat "$JOBFILE")"
EXPECTED_FILE="$RUN_DIR/metadata/expected_cases.txt"
test -f "$EXPECTED_FILE" || { echo "Missing $EXPECTED_FILE" >&2; exit 7; }
EXPECTED_CASES="$(cat "$EXPECTED_FILE")"
[[ "$EXPECTED_CASES" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid expected cases" >&2; exit 8; }
KIND="$(cat "$RUN_DIR/metadata/job_kind.txt" 2>/dev/null || echo unknown)"

# Never address a Picasso array by parent id. Filter the global queue instead.
ACTIVE="$(squeue -h -o '%i|%T' 2>/dev/null | awk -F'|' -v id="$JOBID" '$1==id || index($1,id "_")==1 {print}' || true)"
if [[ -n "$ACTIVE" ]]; then
  echo "Job/campaign still active:" >&2; printf '%s\n' "$ACTIVE" >&2; exit 5
fi

TMP="$RUN_DIR/results/consolidated"
rm -rf "$TMP"; mkdir -p "$TMP"
module purge
module load "$PYEXPINT_PYTHON_MODULE"
"$PYEXPINT_PYTHON" "$PYEXPINT_HOME_ROOT/ops/python/aggregate_campaign.py" \
  --run-dir "$RUN_DIR" --out-dir "$TMP" --jobid "$JOBID" --expected-cases "$EXPECTED_CASES"

# Best-effort accounting, but correctly address array tasks individually.
: > "$RUN_DIR/metadata/sacct.tsv"
: > "$RUN_DIR/metadata/seff.txt"
if [[ "$KIND" == "array" ]]; then
  for ((i=0;i<EXPECTED_CASES;i++)); do
    echo "===== ${JOBID}_${i} =====" >> "$RUN_DIR/metadata/sacct.tsv"
    sacct -j "${JOBID}_${i}" --format=JobID,JobName%24,Partition,NodeList%30,State,Elapsed,AllocCPUS,MaxRSS,ExitCode -P >> "$RUN_DIR/metadata/sacct.tsv" 2>&1 || true
    echo "===== ${JOBID}_${i} =====" >> "$RUN_DIR/metadata/seff.txt"
    seff "${JOBID}_${i}" >> "$RUN_DIR/metadata/seff.txt" 2>&1 || true
  done
else
  sacct -j "$JOBID" --format=JobID,JobName%24,Partition,NodeList%30,State,Elapsed,AllocCPUS,MaxRSS,ExitCode -P > "$RUN_DIR/metadata/sacct.tsv" 2>&1 || true
  seff "$JOBID" > "$RUN_DIR/metadata/seff.txt" 2>&1 || true
fi
date -Is > "$RUN_DIR/metadata/collected_at.txt"

HOME_CAMPAIGN="$PYEXPINT_HOME_ROOT/results/campaigns/$CAMPAIGN_ID"
[[ ! -e "$HOME_CAMPAIGN" ]] || { echo "Refusing overwrite: $HOME_CAMPAIGN" >&2; exit 6; }
mkdir -p "$HOME_CAMPAIGN"/{summary,artifacts}
cp "$TMP/summary.json" "$HOME_CAMPAIGN/summary/"
cp "$TMP/summary.csv" "$HOME_CAMPAIGN/summary/"
cp "$TMP/campaign_manifest.json" "$HOME_CAMPAIGN/summary/"
cp "$RUN_DIR/campaign.env" "$HOME_CAMPAIGN/summary/"
cp "$RUN_DIR/metadata/source_manifest.sha256" "$HOME_CAMPAIGN/summary/"
cp "$RUN_DIR/metadata/sacct.tsv" "$HOME_CAMPAIGN/summary/"
cp "$RUN_DIR/metadata/seff.txt" "$HOME_CAMPAIGN/summary/"
if [[ -d "$RUN_DIR/results/analysis" ]]; then
  mkdir -p "$HOME_CAMPAIGN/summary/timing_analysis"
  cp -a "$RUN_DIR/results/analysis/." "$HOME_CAMPAIGN/summary/timing_analysis/"
fi

tar -czf "$HOME_CAMPAIGN/artifacts/raw_run_bundle.tar.gz" -C "$RUN_DIR" results/raw results/analysis logs metadata campaign.env slurm 2>/dev/null || \
  tar -czf "$HOME_CAMPAIGN/artifacts/raw_run_bundle.tar.gz" -C "$RUN_DIR" results/raw logs metadata campaign.env slurm
(
 cd "$HOME_CAMPAIGN"
 find summary artifacts -type f -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
)
cat > "$HOME_CAMPAIGN/README.md" <<EOF
# PyEXPINT campaign $CAMPAIGN_ID

Slurm job: $JOBID
Job kind: $KIND
Expected result cases: $EXPECTED_CASES

Persistent summaries are in summary/. Raw JSON, logs, metadata and exact Slurm
scripts are in artifacts/raw_run_bundle.tar.gz. Verify with MANIFEST.sha256.
EOF
touch "$HOME_CAMPAIGN/COLLECTED_OK"
touch "$RUN_DIR/metadata/COLLECTED_TO_HOME"
echo "COLLECTED campaign=$CAMPAIGN_ID cases=$EXPECTED_CASES/$EXPECTED_CASES"
echo "HOME campaign: $HOME_CAMPAIGN"
