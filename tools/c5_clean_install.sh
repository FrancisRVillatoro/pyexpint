#!/usr/bin/env bash
# PyEXPINT, block C5: build the distributions and test them in clean environments.
# WSL only, from inside the repository, with the audited Python active:
#
#     conda activate pyx-audit
#     bash tools/c5_clean_install.sh
#
# Nothing is committed or published.  Temporary environments are deleted at the end.
#   1) Build sdist and wheel in an isolated build environment.
#   2) Inspect the sdist (files, compiled files, tests and examples present).
#   3) Wheel in a new virtual environment with the audited NumPy, SciPy and pytest:
#      import origin, full test suite against the installed package, every example.
#   4) Sdist in another new virtual environment: build from source, import, example.
# Logs go to ~/pyexpint_audit/c5_<timestamp>/; only SUMMARY.txt is printed.

set -u
export GIT_PAGER=cat PAGER=cat PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
unset PYTHONPATH
PY="${PYTHON:-python}"
PINS=(numpy==1.24.3 scipy==1.10.1 pytest==7.1.2)

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: run this script from inside the pyexpint repository."; exit 2; }
cd "$ROOT" || exit 2
OUT="$HOME/pyexpint_audit/c5_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM
PROBLEMS=()
[ -z "$(git status --porcelain --untracked-files=no)" ] || PROBLEMS+=("uncommitted changes to tracked files")
"$PY" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 11))' || PROBLEMS+=("python is not 3.11")

# 1) build from the committed tree (git archive), so untracked files never enter the
#    distributions and the build leaves no artifacts in the repository
mkdir -p "$TMP/tree" && git archive --format=tar HEAD | tar -x -C "$TMP/tree"
"$PY" -m venv "$TMP/build" > "$OUT/build.log" 2>&1 \
  && "$TMP/build/bin/python" -m pip install -q build >> "$OUT/build.log" 2>&1 \
  && (cd "$TMP/tree" && "$TMP/build/bin/python" -m build --outdir "$TMP/dist" .) >> "$OUT/build.log" 2>&1
SDIST="$(ls "$TMP"/dist/*.tar.gz 2>/dev/null | head -1)"
WHEEL="$(ls "$TMP"/dist/*.whl 2>/dev/null | head -1)"
if [ -z "$SDIST" ] || [ -z "$WHEEL" ]; then
    PROBLEMS+=("build failed (see build.log)")
    DIST_LINE="build failed"
else
    cp "$SDIST" "$WHEEL" "$OUT/"
    NFILES="$(tar tzf "$SDIST" | grep -vc '/$')"
    NPYC="$(tar tzf "$SDIST" | grep -c -E '\.py[cod]$|__pycache__')"
    NTESTS="$(tar tzf "$SDIST" | grep -c -E '/tests/test_[^/]*\.py$')"
    NEX="$(tar tzf "$SDIST" | grep -c -E '/examples/[^/]*\.py$')"
    [ "$NPYC" -eq 0 ] || PROBLEMS+=("sdist contains compiled files")
    DIST_LINE="$(basename "$SDIST") ($(du -k "$SDIST" | cut -f1) KB, $NFILES files, $NTESTS test modules, $NEX examples, $NPYC compiled), $(basename "$WHEEL") ($(du -k "$WHEEL" | cut -f1) KB)"
fi

# 3) wheel environment
WHEEL_LINE="not run"; SUITE_LINE="not run"; EX_LINE="not run"; NOEX_LINE="not run"
if [ -n "$WHEEL" ]; then
    "$PY" -m venv "$TMP/wheel" > "$OUT/wheel_env.log" 2>&1 \
      && "$TMP/wheel/bin/python" -m pip install -q "${PINS[@]}" "$WHEEL" >> "$OUT/wheel_env.log" 2>&1 \
      || PROBLEMS+=("wheel installation failed (see wheel_env.log)")
    WP="$TMP/wheel/bin/python"
    WHEEL_LINE="$("$WP" - 2>&1 <<'PY'
import os, platform, sys
import numpy, pytest, scipy, pyexpint
inside = os.path.realpath(pyexpint.__file__).startswith(os.path.realpath(sys.prefix))
where = "the environment" if inside else "WRONG PLACE " + pyexpint.__file__
print(f"Python {platform.python_version()}, NumPy {numpy.__version__}, SciPy {scipy.__version__}, "
      f"pytest {pytest.__version__}; pyexpint imported from {where}")
PY
)"
    case "$WHEEL_LINE" in *"from the environment") ;; *) PROBLEMS+=("wheel environment check failed") ;; esac
    "$WP" -m pytest -q -p no:cacheprovider --junitxml="$OUT/suite_wheel.xml" tests > "$OUT/suite_wheel.log" 2>&1
    SUITE_LINE="$(tail -1 "$OUT/suite_wheel.log")"
    case "$SUITE_LINE" in *passed*) case "$SUITE_LINE" in *failed*|*error*) PROBLEMS+=("test suite against the wheel is not green") ;; esac ;; *) PROBLEMS+=("test suite against the wheel did not run") ;; esac
    NOK=0; NALL=0
    for ex in examples/*.py; do
        NALL=$((NALL + 1))
        if (cd "$TMP" && "$WP" "$ROOT/$ex") > "$OUT/example_$(basename "$ex" .py).log" 2>&1; then NOK=$((NOK + 1)); else PROBLEMS+=("example $(basename "$ex") failed"); fi
    done
    EX_LINE="$NOK/$NALL examples ran from outside the repository"
    NOEX_LINE="$(tr '\n' ' ' < "$OUT/example_no_exact_history.log" 2>/dev/null)"
fi

# 4) sdist environment
SDIST_LINE="not run"
if [ -n "$SDIST" ]; then
    if "$PY" -m venv "$TMP/sdist" > "$OUT/sdist_env.log" 2>&1 \
       && "$TMP/sdist/bin/python" -m pip install -q numpy==1.24.3 scipy==1.10.1 "$SDIST" >> "$OUT/sdist_env.log" 2>&1 \
       && (cd "$TMP" && "$TMP/sdist/bin/python" "$ROOT/examples/no_exact_history.py") > "$OUT/sdist_example.log" 2>&1; then
        SDIST_LINE="built from source, installed and ran the example"
    else
        SDIST_LINE="FAILED (see sdist_env.log and sdist_example.log)"
        PROBLEMS+=("sdist build or installation failed")
    fi
fi

VERDICT="OK"; [ "${#PROBLEMS[@]}" -eq 0 ] || VERDICT="NOT OK"
{
    echo "C5 clean install | $(date '+%Y-%m-%d %H:%M') | WSL"
    echo "Distributions: $DIST_LINE"
    echo "Wheel environment: $WHEEL_LINE"
    echo "Full suite against the installed wheel: $SUITE_LINE"
    echo "Examples: $EX_LINE"
    echo "Example without exact history: $NOEX_LINE"
    echo "Sdist: $SDIST_LINE"
    for p in "${PROBLEMS[@]}"; do echo "PROBLEM: $p"; done
    echo "VERDICT C5: $VERDICT"
    echo "Logs: $OUT"
} > "$OUT/SUMMARY.txt"
cat "$OUT/SUMMARY.txt"
[ "$VERDICT" = "OK" ]
