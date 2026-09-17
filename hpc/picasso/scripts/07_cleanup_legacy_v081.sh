#!/usr/bin/env bash
set -euo pipefail
CONFIRM="${1:-}"
ROOT="${PYEXPINT_HOME_ROOT:-$HOME/pyexpint_toms}"

shopt -s nullglob
DIRS=(
  "$HOME"/PyEXPINT_Picasso_DevBundle_v0.8.1-dev
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1a
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1b
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1c
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1d
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1e
)
FILES=(
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1*.tar.gz
  "$HOME"/PyEXPINT_Picasso_Hotfix_v0.8.1*.sha256
  "$HOME"/PyEXPINT_Picasso_DevBundle_v0.8.1-dev.tar.gz
  "$HOME"/PyEXPINT_Picasso_DevBundle_v0.8.1-dev.sha256
)

# Require the compact pre-v0.8.2 source snapshot produced by bootstrap_install.sh.
SNAPS=("$ROOT"/snapshots/pre_v0.8.2_repo_*.tar.gz)
if (( ${#SNAPS[@]} == 0 )); then
  echo "Refusing cleanup: no pre_v0.8.2_repo snapshot found." >&2
  exit 3
fi

echo "Legacy unpacked directories present:"
for d in "${DIRS[@]}"; do [[ -e "$d" ]] && echo "  $d"; done

echo "Legacy installer files in HOME:"
for f in "${FILES[@]}"; do [[ -e "$f" ]] && echo "  $f"; done

if [[ "$CONFIRM" != "--yes" ]]; then
  echo
  echo "DRY RUN only. Re-run with --yes after inspecting the paths above."
  exit 0
fi

mkdir -p "$ROOT/snapshots" "$ROOT/manifests"
STAMP="$(date +%Y%m%dT%H%M%S)"
PRESENT=()
for f in "${FILES[@]}"; do [[ -f "$f" ]] && PRESENT+=("$f"); done
if (( ${#PRESENT[@]} > 0 )); then
  ARCH="$ROOT/snapshots/legacy_v081_installers_${STAMP}.tar.gz"
  # All listed files live directly under HOME.
  NAMES=(); for f in "${PRESENT[@]}"; do NAMES+=("$(basename "$f")"); done
  tar -czf "$ARCH" -C "$HOME" "${NAMES[@]}"
  SHA="$(sha256sum "$ARCH")"
  echo "$SHA" >> "$ROOT/manifests/legacy_cleanup.log"
  rm -f "${PRESENT[@]}"
  echo "Archived legacy installers: $ARCH"
fi

for d in "${DIRS[@]}"; do
  [[ -d "$d" ]] && rm -rf --one-file-system "$d"
done

echo "Legacy v0.8.1 unpacked directories removed."
