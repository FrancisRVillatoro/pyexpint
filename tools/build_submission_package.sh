#!/usr/bin/env bash
# PyEXPINT: assemble the private submission package for review (nothing is published).
#
#     bash tools/build_submission_package.sh /path/to/manuscript.zip
#
# Produces ~/pyexpint_submission_<timestamp>.zip containing
#   software/   git archive of the committed tree (HEAD), with the commit id
#   manuscript/ the manuscript zip given as argument
#   evidence/   the latest logs of every check in ~/pyexpint_audit (C1, C2-C4,
#               cheap experiments, C5 clean install), the EXPINT cross-check
#               outputs archived in the repository, and the environment record
#   MANIFEST.sha256  SHA-256 of every file in the package
set -u
MANUSCRIPT="${1:?usage: build_submission_package.sh MANUSCRIPT_ZIP}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "run inside the repository"; exit 2; }
cd "$ROOT" || exit 2
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "ERROR: uncommitted changes to tracked files"; exit 2; }
STAMP="$(date +%Y%m%d_%H%M%S)"
PKG="$HOME/pyexpint_submission_$STAMP"
mkdir -p "$PKG/software" "$PKG/manuscript" "$PKG/evidence"
HEAD_ID="$(git rev-parse HEAD)"
git archive --format=tar HEAD | tar -x -C "$PKG/software"
{ echo "commit: $HEAD_ID"; echo "branch: $(git rev-parse --abbrev-ref HEAD)"; echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)";
  echo "version (pyproject): $(grep -m1 '^version' pyproject.toml)"; } > "$PKG/software/SNAPSHOT.txt"
cp "$MANUSCRIPT" "$PKG/manuscript/"
for prefix in c1_ c2c4_ cheap_ c5_; do
    latest="$(ls -d "$HOME"/pyexpint_audit/${prefix}* 2>/dev/null | sort | tail -1)"
    [ -n "$latest" ] && cp -r "$latest" "$PKG/evidence/"
done
cp -r tools/expint_crosscheck/results_* "$PKG/evidence/" 2>/dev/null
python - > "$PKG/evidence/ENVIRONMENT.txt" <<'PY'
import platform, numpy, scipy
print(f"Python {platform.python_version()}; NumPy {numpy.__version__}; SciPy {scipy.__version__}; {platform.platform()}")
PY
(cd "$PKG" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256)
python -c "import shutil, sys; shutil.make_archive(sys.argv[1], 'zip', sys.argv[2], sys.argv[3])" \
    "$HOME/pyexpint_submission_$STAMP" "$HOME" "pyexpint_submission_$STAMP"
echo "package: $HOME/pyexpint_submission_$STAMP.zip ($(wc -l < "$PKG/MANIFEST.sha256") files)"
sha256sum "$HOME/pyexpint_submission_$STAMP.zip"
