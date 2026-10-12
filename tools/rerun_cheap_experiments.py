#!/usr/bin/env python3
"""Re-run the inexpensive experiments of the paper with the current code (WSL).

1. Classical order (Fig. 2a) and 2. stiff order (Fig. 2b,c) are compared with the
   archived figure data in reproducibility/paper; final errors must agree within
   1e-12 times the solution scale.
3. Fusion ablation with full Arnoldi and with the KIOPS-type backend
   (benchmarks/fusion_ablation.py); unfused counts are compared with the archived
   ones, fused and unfused final states must agree to 1e-13 and fusion must never
   increase the count.
4. Generalized Lawson convergence (benchmarks/lawson_generic.py); every last slope
   must lie within 0.5 of the recorded classical order.
Outputs go to ~/pyexpint_audit/cheap_<timestamp>/; SUMMARY.txt is printed.
"""
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "src"))

import numpy  # noqa: E402
import pytest  # noqa: E402
import scipy  # noqa: E402

import pyexpint  # noqa: E402
from pyexpint import DiagonalBackend, SemilinearProblem, get_method, solve_fixed  # noqa: E402
import fusion_ablation  # noqa: E402
import lawson_generic  # noqa: E402
import stiff_order_hochbruck_ostermann as stiff  # noqa: E402

REF = ROOT / "reproducibility" / "paper"
OUT = Path.home() / "pyexpint_audit" / time.strftime("cheap_%Y%m%d_%H%M%S")
OUT.mkdir(parents=True, exist_ok=True)
problems, lines = [], []

want = {"numpy": "1.24.3", "scipy": "1.10.1", "pytest": "7.1.2"}
have = {"numpy": numpy.__version__, "scipy": scipy.__version__, "pytest": pytest.__version__}
bad = [f"{k} {have[k]} (expected {v})" for k, v in want.items() if have[k] != v]
if sys.version_info[:2] != (3, 11):
    bad.insert(0, f"Python {platform.python_version()} (expected 3.11.x)")
env = (f"Python {platform.python_version()}, NumPy {have['numpy']}, SciPy {have['scipy']}, pytest {have['pytest']}; "
       + ("audited" if not bad else "NOT AUDITED: " + "; ".join(bad)))
if bad:
    problems.append("environment is not the audited one")
if not Path(pyexpint.__file__).resolve().is_relative_to(ROOT / "src"):
    problems.append(f"pyexpint imported from {pyexpint.__file__}, not from {ROOT / 'src'}")

# 1. Classical order
arch = json.loads((REF / "classical_selected.json").read_text())
exact = lambda t: np.array([1.0 / (1.0 + 1.5 * np.exp(t))])
prob = SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, np.array([0.4]), (0.0, 1.6), exact_solution=exact)
tol1 = 1e-12 * abs(exact(1.6)[0])
worst1, n1 = 0.0, 0
for name, errs in arch["errors"].items():
    for h, e_arch in zip(arch["hs"], errs):
        e = abs(solve_fixed(prob, get_method(name), h, DiagonalBackend()).y[-1, 0] - exact(1.6)[0])
        worst1, n1 = max(worst1, abs(e - e_arch) / tol1), n1 + 1
if worst1 > 1:
    problems.append("1: classical errors differ from the archived figure data")
lines.append(f"1  classical order (Fig. 2a):  {n1} errors; largest difference / tolerance: {worst1:.1e}")

# 2. Stiff order
arch = json.loads((REF / "stiff_order.json").read_text())
res = stiff.run(list(arch["local"].keys()), n=arch["n"])
x = np.arange(1, arch["n"] + 1) / (arch["n"] + 1)
tol2 = 1e-12 * float(np.max(x * (1 - x) * np.e))
worst2, n2 = 0.0, 0
for variant, key in (("1", "local"), ("2", "nonlocal")):
    for row in res["problems"][variant]:
        for e, e_arch in zip(row["errors"], arch[key][row["method"]]):
            worst2, n2 = max(worst2, abs(e - e_arch) / tol2), n2 + 1
(OUT / "stiff_order.json").write_text(json.dumps(res, indent=1))
if worst2 > 1:
    problems.append("2: stiff-order errors differ from the archived figure data")
lines.append(f"2  stiff order (Fig. 2b,c):    {n2} errors; largest difference / tolerance: {worst2:.1e}")

# 3. Fusion ablation
fus = fusion_ablation.run()
(OUT / "fusion_ablation.json").write_text(json.dumps(fus, indent=1))
archived = {r["method"]: r for r in json.loads((REF / "fusion_archived.json").read_text())["rows"]}
rows = fus["rows"]
unfused_ok = all(r["arnoldi_matvecs_unfused"] == archived[r["method"]]["matvec_unfused"] for r in rows)
fused_same = [r["method"] for r in rows if r["arnoldi_matvecs_fused"] == archived[r["method"]]["matvec_fused"]]
fused_diff = [f"{r['method']} {r['arnoldi_matvecs_fused']} vs {archived[r['method']]['matvec_fused']}"
              for r in rows if r["method"] not in fused_same]
agree = max(max(r["arnoldi_final_state_rel_diff"], r["kiops_final_state_rel_diff"]) for r in rows)
never_more = all(r[f"{b}_matvecs_fused"] <= r[f"{b}_matvecs_unfused"] for r in rows for b in ("arnoldi", "kiops"))
red = {b: [100 * (1 - r[f"{b}_matvecs_fused"] / r[f"{b}_matvecs_unfused"]) for r in rows] for b in ("arnoldi", "kiops")}
if not unfused_ok:
    problems.append("3: unfused full-Arnoldi counts differ from the archived ones")
if agree > 1e-13 or not never_more:
    problems.append("3: fused and unfused paths disagree or fusion increased the work")
lines.append(f"3  fusion, full Arnoldi:       unfused 7/7 as archived; fused {len(fused_same)}/7 as archived"
             + (f" ({'; '.join(fused_diff)})" if fused_diff else "")
             + f"; reductions {min(red['arnoldi']):.1f}-{max(red['arnoldi']):.1f}%")
lines.append(f"   fusion, KIOPS-type:         reductions {min(red['kiops']):.1f}-{max(red['kiops']):.1f}%; "
             f"fused and unfused final states agree to {agree:.1e}")

# 4. Generalized Lawson convergence
law = lawson_generic.run()
(OUT / "lawson_generic.json").write_text(json.dumps(law, indent=1))
dev = max(abs(r["slopes"][-1] - r["classical_order"]) for r in law["rows"])
if not dev < 0.5:
    problems.append("4: a last slope deviates by 0.5 or more from the recorded order")
lines.append(f"4  generalized Lawson (new):   {len(law['rows'])} rows; largest |last slope - recorded order|: {dev:.2f}")

summary = [f"Cheap experiments | {time.strftime('%Y-%m-%d %H:%M')} | WSL", f"Environment: {env}", *lines,
           *(f"PROBLEM: {p}" for p in problems), f"VERDICT: {'OK' if not problems else 'NOT OK'}", f"Logs: {OUT}"]
(OUT / "SUMMARY.txt").write_text("\n".join(summary) + "\n")
print("\n".join(summary))
sys.exit(0 if not problems else 1)
