#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 CAMPAIGN_ID [--yes]" >&2
  exit 2
fi
CAMPAIGN_ID="$1"
CONFIRM="${2:-}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"

RUN_DIR="$PYEXPINT_FSCRATCH_ROOT/runs/$CAMPAIGN_ID"
HOME_CAMPAIGN="$PYEXPINT_HOME_ROOT/results/campaigns/$CAMPAIGN_ID"

test -f "$HOME_CAMPAIGN/COLLECTED_OK" || {
  echo "No COLLECTED_OK marker in HOME. Refusing cleanup." >&2
  exit 3
}
test -d "$RUN_DIR" || { echo "Run dir already absent: $RUN_DIR"; exit 0; }

if [[ "$CONFIRM" != "--yes" ]]; then
  echo "DRY RUN. Would remove:"
  echo "  $RUN_DIR"
  echo
  echo "Re-run with --yes after verifying HOME artifacts."
  exit 0
fi

rm -rf --one-file-system "$RUN_DIR"
rm -f "$PYEXPINT_HOME_ROOT/state/${CAMPAIGN_ID}.jobid"
echo "REMOVED $RUN_DIR"
