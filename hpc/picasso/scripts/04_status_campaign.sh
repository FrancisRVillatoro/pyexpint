#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "Usage: $0 CAMPAIGN_ID" >&2; exit 2; fi
CAMPAIGN_ID="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"
RUN_DIR="$PYEXPINT_FSCRATCH_ROOT/runs/$CAMPAIGN_ID"
JOBFILE="$PYEXPINT_HOME_ROOT/state/${CAMPAIGN_ID}.jobid"
test -f "$JOBFILE" || { echo "No jobid file: $JOBFILE" >&2; exit 3; }
JOBID="$(cat "$JOBFILE")"
KIND="$(cat "$RUN_DIR/metadata/job_kind.txt" 2>/dev/null || echo unknown)"
EXPECTED="$(cat "$RUN_DIR/metadata/expected_cases.txt" 2>/dev/null || echo 0)"

echo "=== squeue matching $JOBID ==="
squeue -h -o '%i|%T|%M|%l|%N|%R' 2>/dev/null | awk -F'|' -v id="$JOBID" '$1==id || index($1,id "_")==1' || true

echo
echo "=== sacct ==="
if [[ "$KIND" == "array" && "$EXPECTED" =~ ^[1-9][0-9]*$ ]]; then
  for ((i=0;i<EXPECTED;i++)); do
    sacct -n -X -j "${JOBID}_${i}" --format=JobID,JobName%20,Partition,NodeList%12,State,Elapsed,AllocCPUS,MaxRSS,ExitCode -P 2>/dev/null || true
  done
else
  sacct -j "$JOBID" --format=JobID,JobName%20,Partition,NodeList%12,State,Elapsed,AllocCPUS,MaxRSS,ExitCode -P 2>/dev/null || true
fi

echo
echo "JOBID=$JOBID KIND=$KIND EXPECTED_CASES=$EXPECTED"
