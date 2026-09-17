#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/picasso.env"
SIF="$PYEXPINT_HOME_ROOT/containers/images/$PYEXPINT_SIF_NAME"
test -f "$SIF" || { echo "Missing $SIF" >&2; exit 2; }
sha256sum "$SIF"
"$PYEXPINT_APPTAINER" inspect "$SIF" | head -80
