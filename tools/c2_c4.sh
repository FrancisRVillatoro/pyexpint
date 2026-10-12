#!/usr/bin/env bash
# PyEXPINT, blocks C2-C4.  WSL only, from inside the repository:
#
#     conda activate pyx-audit
#     bash tools/c2_c4.sh
#
# It makes no commits, touches no branch or tag, publishes nothing and does not use Picasso.
#   0) Preflight: branch, C1 commit as ancestor, files, environment, origin of the import.
#   A) C2-C4 tests on the current branch (must pass).
#   B) The same tests on the C1 commit (must fail: evidence that they detect the defects).
#   C) Full test suite on the current branch.
#   D) Full test suite on the C1 commit, as the baseline used to classify failures in C.
#   E) Differential check of the 24 canonical timing configurations against the archived
#      Picasso counters (3 replicas, no timing).
#   F) End-to-end order study with numerical startup.
# Full logs go to ~/pyexpint_audit/c2c4_<timestamp>/; only SUMMARY.txt is printed.

set -u
export GIT_PAGER=cat PAGER=cat
export PYTHONNOUSERSITE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1

C1_COMMIT="${C1_COMMIT:-9886d6703cb701dcb107375b4e57247dc241eb6e}"
BRANCH_EXPECTED="${BRANCH_EXPECTED:-toms-revision}"
PY="${PYTHON:-python}"
NEW_TESTS=(tests/test_c2_work_accounting.py tests/test_c3_adaptive_contract.py tests/test_c4_cloning_and_startup.py)
PYTEST=("$PY" -m pytest -q -p no:cacheprovider)

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: run this script from inside the pyexpint repository."
    exit 2
}
cd "$ROOT" || exit 2

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$HOME/pyexpint_audit/c2c4_$STAMP"
mkdir -p "$OUT"
PROBLEMS=()

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

failures_of() { awk '{print $2 + $3}' "$1.counts" 2>/dev/null || echo 999; }
passes_of() { awk '{print $1}' "$1.counts" 2>/dev/null || echo 0; }

# ---------------------------------------------------------------- 0) preflight
BRANCH="$(git branch --show-current)"
HEAD_SHA="$(git rev-parse HEAD)"
{
    echo "ROOT=$ROOT"; echo "BRANCH=$BRANCH"; echo "HEAD=$HEAD_SHA"; echo "C1=$C1_COMMIT"
    echo; echo "Commits since C1:"; git log --oneline "$C1_COMMIT..HEAD" 2>&1
    echo; echo "Uncommitted changes:"; git status --short
} > "$OUT/preflight.txt"
[ "$BRANCH" = "$BRANCH_EXPECTED" ] || PROBLEMS+=("branch '$BRANCH' (expected '$BRANCH_EXPECTED')")
git merge-base --is-ancestor "$C1_COMMIT" HEAD 2>/dev/null || PROBLEMS+=("HEAD does not descend from the C1 commit")
for f in "${NEW_TESTS[@]}" tools/differential_canonical.py tools/c4_startup_order.py; do
    [ -f "$f" ] || PROBLEMS+=("missing $f")
done
[ -z "$(git status --porcelain --untracked-files=no)" ] || PROBLEMS+=("uncommitted changes to tracked files")

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
echo "$ENV_LINE" > "$OUT/env.txt"

IMPORT_PATH="$(PYTHONPATH="$ROOT/src" "$PY" -c 'import os, pyexpint; print(os.path.realpath(pyexpint.__file__))' 2>&1)"
echo "IMPORT_BRANCH=$IMPORT_PATH" >> "$OUT/preflight.txt"
case "$IMPORT_PATH" in "$(realpath "$ROOT/src")"/*) ;; *) PROBLEMS+=("pyexpint is not imported from $ROOT/src") ;; esac

# ---------------------------------------------------------------- A, C, E, F on the branch
PYTHONPATH="$ROOT/src" "${PYTEST[@]}" --junitxml="$OUT/A_new_branch.xml" "${NEW_TESTS[@]}" > "$OUT/A_new_branch.log" 2>&1
A_SUM="$(junit_summary "$OUT/A_new_branch.xml")"
PYTHONPATH="$ROOT/src" "${PYTEST[@]}" --junitxml="$OUT/C_suite_branch.xml" tests > "$OUT/C_suite_branch.log" 2>&1
C_SUM="$(junit_summary "$OUT/C_suite_branch.xml")"
PYTHONPATH="$ROOT/src" "$PY" tools/differential_canonical.py "$OUT/E_differential.json" > "$OUT/E_differential.log" 2>&1
E_RC=$?
E_SUM="$(tail -1 "$OUT/E_differential.log")"
[ "$E_RC" -eq 0 ] || PROBLEMS+=("E: canonical counters differ from the archived Picasso records")
PYTHONPATH="$ROOT/src" "$PY" tools/c4_startup_order.py "$OUT/F_startup_order.json" > "$OUT/F_startup_order.log" 2>&1
F_SUM="$("$PY" - "$OUT/F_startup_order.json" <<'PY' 2>&1
import json, sys
rows = json.load(open(sys.argv[1]))["rows"]
hi = [r for r in rows if r["classical_order"] >= 6]
s = [r["slopes_default_startup"][-1] for r in hi]
q = [r["ratio_default_over_exact_finest"] for r in hi]
print(f"order 6-7 methods with HochOst4 startup: last slopes {min(s):.2f}-{max(s):.2f}, "
      f"error ratio to exact history {min(q):.0f}-{max(q):.0f}")
PY
)"

# ---------------------------------------------------------------- B and D on the C1 commit
WT_PARENT="$(mktemp -d)"
WT="$WT_PARENT/c1"
cleanup() {
    git worktree remove --force "$WT" > /dev/null 2>&1
    rm -rf "$WT_PARENT"
    git worktree prune > /dev/null 2>&1
}
trap cleanup EXIT INT TERM
B_SUM="not run"
D_SUM="not run"
if git worktree add --detach "$WT" "$C1_COMMIT" > "$OUT/worktree.log" 2>&1; then
    (cd "$WT" && PYTHONPATH="$WT/src" "${PYTEST[@]}" --junitxml="$OUT/D_suite_c1.xml" tests > "$OUT/D_suite_c1.log" 2>&1)
    D_SUM="$(junit_summary "$OUT/D_suite_c1.xml")"
    cp "${NEW_TESTS[@]}" "$WT/tests/"
    (cd "$WT" && PYTHONPATH="$WT/src" "${PYTEST[@]}" --junitxml="$OUT/B_new_c1.xml" "${NEW_TESTS[@]}" > "$OUT/B_new_c1.log" 2>&1)
    B_SUM="$(junit_summary "$OUT/B_new_c1.xml")"
    git worktree remove --force "$WT" >> "$OUT/worktree.log" 2>&1
else
    PROBLEMS+=("temporary C1 worktree could not be created (see worktree.log)")
fi
rm -rf "$WT_PARENT"
git worktree prune >> "$OUT/worktree.log" 2>&1

NEW_FAILS=0
if [ -f "$OUT/C_suite_branch.xml.fail" ]; then
    comm -23 <(sort -u "$OUT/C_suite_branch.xml.fail") <(sort -u "$OUT/D_suite_c1.xml.fail" 2>/dev/null) > "$OUT/new_failures.txt"
    NEW_FAILS="$(grep -c . "$OUT/new_failures.txt")"
fi

# ---------------------------------------------------------------- verdict
[ "$(failures_of "$OUT/A_new_branch.xml")" -eq 0 ] && [ "$(passes_of "$OUT/A_new_branch.xml")" -gt 0 ] \
    || PROBLEMS+=("A: the C2-C4 tests do not pass on the branch")
[ "$(failures_of "$OUT/C_suite_branch.xml")" -eq 0 ] && [ "$(passes_of "$OUT/C_suite_branch.xml")" -gt 0 ] \
    || PROBLEMS+=("C: the full suite is not green on the branch")
if [ -f "$OUT/B_new_c1.xml.counts" ]; then
    [ "$(failures_of "$OUT/B_new_c1.xml")" -gt 0 ] || PROBLEMS+=("B: the new tests do not detect the defects at C1")
fi
VERDICT="OK"
[ "${#PROBLEMS[@]}" -eq 0 ] || VERDICT="NOT OK"

{
    echo "C2-C4 | $(date '+%Y-%m-%d %H:%M') | WSL"
    echo "Branch $BRANCH | HEAD ${HEAD_SHA:0:12} | C1 ${C1_COMMIT:0:12}"
    echo "Environment: $ENV_LINE"
    echo "A  C2-C4 tests, branch:       $A_SUM"
    echo "B  C2-C4 tests, C1 commit:    $B_SUM   (must fail)"
    echo "C  full suite, branch:        $C_SUM"
    echo "D  full suite, C1 commit:     $D_SUM"
    echo "Failures in C absent from D:  $NEW_FAILS"
    echo "E  canonical counters:        $E_SUM"
    echo "F  startup study:             $F_SUM"
    for p in "${PROBLEMS[@]}"; do echo "PROBLEM: $p"; done
    echo "VERDICT C2-C4: $VERDICT"
    echo "Logs: $OUT"
} > "$OUT/SUMMARY.txt"
cat "$OUT/SUMMARY.txt"
[ "$VERDICT" = "OK" ]
