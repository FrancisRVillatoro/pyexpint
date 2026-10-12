#!/usr/bin/env bash
# PyEXPINT, block C1 (real-Leja backend).  WSL only, from inside the repository:
#
#     conda activate pyx-audit
#     bash tools/c1_leja.sh
#
# It makes no commits, touches no branch or tag, publishes nothing and does not use Picasso.
#   0) Preflight: branch, v0.9.0 base, files, environment, origin of the imported package.
#   A) Leja regressions on the corrected branch (must pass).
#   B) The same regressions on v0.9.0 (must fail: evidence that they detect the defect).
#   C) Full test suite on the corrected branch.
#   D) Full test suite on v0.9.0, as the baseline used to classify failures in C.
# Full logs go to ~/pyexpint_audit/c1_<timestamp>/; only SUMMARY.txt is printed.

set -u
export GIT_PAGER=cat PAGER=cat
export PYTHONNOUSERSITE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1

V090_COMMIT="${V090_COMMIT:-4bba03b89e97f7a83525bbfdea228e1ed8d9d033}"
BRANCH_EXPECTED="${BRANCH_EXPECTED:-toms-revision}"
PY="${PYTHON:-python}"
LEJA_FILE="src/pyexpint/backends/leja.py"
LEJA_TESTS=(tests/test_leja_edge_cases.py tests/test_leja_c1_phi.py)
ALLOWED=("$LEJA_FILE" "${LEJA_TESTS[@]}" tools/c1_leja.sh)
PYTEST=("$PY" -m pytest -q -p no:cacheprovider)

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: run this script from inside the pyexpint repository."
    exit 2
}
cd "$ROOT" || exit 2

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$HOME/pyexpint_audit/c1_$STAMP"
mkdir -p "$OUT"
PROBLEMS=()
WARNINGS=()

# Summarize a JUnit file: print one line, write <xml>.counts and <xml>.fail
junit_summary() {
    "$PY" - "$1" <<'PY'
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
try:
    root = ET.parse(path).getroot()
except Exception as exc:
    open(path + ".counts", "w").write("0 0 1 0\n")
    open(path + ".fail", "w").write(f"<no results: {exc.__class__.__name__}>\n")
    print("no results (pytest did not write its report)")
    sys.exit(0)
suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
n = f = e = s = 0
failing = []
for suite in suites:
    for case in suite.iter("testcase"):
        n += 1
        kinds = [child.tag for child in case]
        cid = f'{case.get("classname", "")}::{case.get("name", "")}'
        if "failure" in kinds:
            f += 1
            failing.append(cid)
        elif "error" in kinds:
            e += 1
            failing.append(cid)
        elif "skipped" in kinds:
            s += 1
open(path + ".counts", "w").write(f"{n - f - e - s} {f} {e} {s}\n")
open(path + ".fail", "w").write("".join(x + "\n" for x in failing))
print(f"{n - f - e - s} passed, {f} failed, {e} errors, {s} skipped")
PY
}

failures_of() {  # failures + errors recorded in a .counts file
    awk '{print $2 + $3}' "$1.counts" 2>/dev/null || echo 999
}

passes_of() {
    awk '{print $1}' "$1.counts" 2>/dev/null || echo 0
}

# ---------------------------------------------------------------- 0) preflight
BRANCH="$(git branch --show-current)"
HEAD_SHA="$(git rev-parse HEAD)"
TAG_SHA="$(git rev-parse -q --verify 'v0.9.0^{commit}' 2>/dev/null || echo none)"
{
    echo "ROOT=$ROOT"
    echo "BRANCH=$BRANCH"
    echo "HEAD=$HEAD_SHA"
    echo "V090=$TAG_SHA"
    echo
    echo "Tracked changes with respect to v0.9.0:"
    git diff --name-status "$V090_COMMIT" 2>&1
    echo
    echo "Untracked:"
    git ls-files --others --exclude-standard
    echo
    echo "sha256:"
    sha256sum "$LEJA_FILE" "${LEJA_TESTS[@]}" 2>&1
} > "$OUT/preflight.txt"

[ "$BRANCH" = "$BRANCH_EXPECTED" ] || PROBLEMS+=("branch '$BRANCH' (expected '$BRANCH_EXPECTED')")
[ "$TAG_SHA" = "$V090_COMMIT" ] || PROBLEMS+=("tag v0.9.0 points to $TAG_SHA")
git merge-base --is-ancestor "$V090_COMMIT" HEAD 2>/dev/null || PROBLEMS+=("HEAD does not descend from v0.9.0")
for f in "$LEJA_FILE" "${LEJA_TESTS[@]}"; do
    [ -f "$f" ] || PROBLEMS+=("missing $f")
done

UNEXPECTED=()
while IFS= read -r f; do
    [ -z "$f" ] && continue
    ok=0
    for a in "${ALLOWED[@]}"; do [ "$f" = "$a" ] && ok=1; done
    [ "$ok" -eq 1 ] || UNEXPECTED+=("$f")
done < <( { git diff --name-only "$V090_COMMIT"; git ls-files --others --exclude-standard; } | sort -u )
[ "${#UNEXPECTED[@]}" -eq 0 ] || WARNINGS+=("unexpected changes with respect to v0.9.0: ${UNEXPECTED[*]}")

LEJA_STAT="$(git diff --shortstat "$V090_COMMIT" -- "$LEJA_FILE" | sed 's/^ *//')"
[ -n "$LEJA_STAT" ] || PROBLEMS+=("leja.py is identical to v0.9.0: the patch is not applied")

ENV_LINE="$("$PY" - <<'PY' 2> "$OUT/env_error.txt"
import platform, sys
import numpy, scipy, pytest
want = {"numpy": "1.24.3", "scipy": "1.10.1", "pytest": "7.1.2"}
have = {"numpy": numpy.__version__, "scipy": scipy.__version__, "pytest": pytest.__version__}
bad = [f"{k} {have[k]} (expected {v})" for k, v in want.items() if have[k] != v]
if sys.version_info[:2] != (3, 11):
    bad.insert(0, f"Python {platform.python_version()} (expected 3.11.x)")
status = "audited" if not bad else "NOT AUDITED: " + "; ".join(bad)
print(f"Python {platform.python_version()}, NumPy {have['numpy']}, SciPy {have['scipy']}, "
      f"pytest {have['pytest']}; {status}")
PY
)"
[ -n "$ENV_LINE" ] || ENV_LINE="environment could not be read (see env_error.txt)"
case "$ENV_LINE" in *"; audited") ;; *) PROBLEMS+=("environment is not the audited one") ;; esac
{
    echo "$ENV_LINE"
    echo
    "$PY" -c "import numpy; numpy.show_config()" 2>&1
} > "$OUT/env.txt"

IMPORT_PATH="$(PYTHONPATH="$ROOT/src" "$PY" -c 'import os, pyexpint; print(os.path.realpath(pyexpint.__file__))' 2>&1)"
echo "IMPORT_BRANCH=$IMPORT_PATH" >> "$OUT/preflight.txt"
case "$IMPORT_PATH" in
    "$(realpath "$ROOT/src")"/*) ;;
    *) PROBLEMS+=("pyexpint is not imported from $ROOT/src") ;;
esac

# Dump of the Leja API (signatures needed for combination regressions in later blocks)
PYTHONPATH="$ROOT/src" "$PY" - > "$OUT/api_leja.txt" 2>&1 <<'PY'
import inspect
import numpy as np
from scipy.sparse.linalg import aslinearoperator
from pyexpint import LejaBackend

backend = LejaBackend(tol=1e-12, spectral_bounds=(-1.0, 0.0), max_degree=80)
bound = backend.bind(aslinearoperator(np.diag([-1.0, 0.0])), 1.0)
for obj in (backend, bound):
    for name in sorted(dir(obj)):
        if name.startswith("__") or (name.startswith("_") and name != "_function_action"):
            continue
        member = getattr(obj, name)
        if callable(member):
            try:
                sig = str(inspect.signature(member))
            except (TypeError, ValueError):
                sig = "(?)"
            print(f"{type(obj).__name__}.{name}{sig}")
PY

# ---------------------------------------------------------------- A and C, branch
PYTHONPATH="$ROOT/src" "${PYTEST[@]}" --junitxml="$OUT/A_leja_branch.xml" "${LEJA_TESTS[@]}" \
    > "$OUT/A_leja_branch.log" 2>&1
A_SUM="$(junit_summary "$OUT/A_leja_branch.xml")"

PYTHONPATH="$ROOT/src" "${PYTEST[@]}" --junitxml="$OUT/C_suite_branch.xml" tests \
    > "$OUT/C_suite_branch.log" 2>&1
C_SUM="$(junit_summary "$OUT/C_suite_branch.xml")"

# ---------------------------------------------------------------- B and D, v0.9.0
WT_PARENT="$(mktemp -d)"
WT="$WT_PARENT/v090"
B_SUM="not run"
D_SUM="not run"
if git worktree add --detach "$WT" "$V090_COMMIT" > "$OUT/worktree.log" 2>&1; then
    WT_IMPORT="$(cd "$WT" && PYTHONPATH="$WT/src" "$PY" -c 'import os, pyexpint; print(os.path.realpath(pyexpint.__file__))' 2>&1)"
    echo "IMPORT_V090=$WT_IMPORT" >> "$OUT/preflight.txt"
    case "$WT_IMPORT" in
        "$(realpath "$WT/src")"/*) ;;
        *) PROBLEMS+=("in v0.9.0, pyexpint is not imported from the worktree") ;;
    esac
    (cd "$WT" && PYTHONPATH="$WT/src" "${PYTEST[@]}" --junitxml="$OUT/D_suite_v090.xml" tests \
        > "$OUT/D_suite_v090.log" 2>&1)
    D_SUM="$(junit_summary "$OUT/D_suite_v090.xml")"
    cp "${LEJA_TESTS[@]}" "$WT/tests/"
    (cd "$WT" && PYTHONPATH="$WT/src" "${PYTEST[@]}" --junitxml="$OUT/B_leja_v090.xml" "${LEJA_TESTS[@]}" \
        > "$OUT/B_leja_v090.log" 2>&1)
    B_SUM="$(junit_summary "$OUT/B_leja_v090.xml")"
    git worktree remove --force "$WT" >> "$OUT/worktree.log" 2>&1
else
    PROBLEMS+=("temporary v0.9.0 worktree could not be created (see worktree.log)")
fi
rm -rf "$WT_PARENT"
git worktree prune >> "$OUT/worktree.log" 2>&1

# Failures in C that were not already failures in D (new Leja tests count as new)
NEW_FAILS=0
if [ -f "$OUT/C_suite_branch.xml.fail" ]; then
    if [ -f "$OUT/D_suite_v090.xml.fail" ]; then
        comm -23 <(sort -u "$OUT/C_suite_branch.xml.fail") <(sort -u "$OUT/D_suite_v090.xml.fail") \
            > "$OUT/new_failures.txt"
    else
        sort -u "$OUT/C_suite_branch.xml.fail" > "$OUT/new_failures.txt"
    fi
    NEW_FAILS="$(grep -c . "$OUT/new_failures.txt")"
fi

# ---------------------------------------------------------------- verdict
[ "$(failures_of "$OUT/A_leja_branch.xml")" -eq 0 ] && [ "$(passes_of "$OUT/A_leja_branch.xml")" -gt 0 ] \
    || PROBLEMS+=("A: the Leja regressions do not pass on the branch")
[ "$(failures_of "$OUT/C_suite_branch.xml")" -eq 0 ] && [ "$(passes_of "$OUT/C_suite_branch.xml")" -gt 0 ] \
    || PROBLEMS+=("C: the full suite is not green on the branch")
if [ -f "$OUT/B_leja_v090.xml.counts" ]; then
    [ "$(failures_of "$OUT/B_leja_v090.xml")" -gt 0 ] \
        || PROBLEMS+=("B: the regressions do not detect the defect in v0.9.0")
fi

VERDICT="OK"
[ "${#PROBLEMS[@]}" -eq 0 ] || VERDICT="NOT OK"

{
    echo "C1 Leja | $(date '+%Y-%m-%d %H:%M') | WSL"
    echo "Branch $BRANCH | HEAD ${HEAD_SHA:0:12} | base v0.9.0 ${TAG_SHA:0:12}"
    echo "leja.py vs v0.9.0: ${LEJA_STAT:-no changes}"
    echo "Environment: $ENV_LINE"
    echo "A  Leja regressions, branch:  $A_SUM"
    echo "B  Leja regressions, v0.9.0:  $B_SUM   (must fail)"
    echo "C  full suite, branch:        $C_SUM"
    echo "D  full suite, v0.9.0:        $D_SUM"
    echo "Failures in C absent from D:  $NEW_FAILS"
    for w in "${WARNINGS[@]}"; do echo "WARNING: $w"; done
    for p in "${PROBLEMS[@]}"; do echo "PROBLEM: $p"; done
    echo "VERDICT C1: $VERDICT"
    echo "Logs: $OUT"
} > "$OUT/SUMMARY.txt"

cat "$OUT/SUMMARY.txt"
[ "$VERDICT" = "OK" ]
