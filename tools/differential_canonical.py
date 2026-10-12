"""Differential check of the canonical timing configurations (no timing).

Re-runs the 24 configurations of hpc/picasso/python/toms_timing_balanced.py once
with the current source and compares the deterministic outputs (matrix-vector
products, nonlinear evaluations, accepted and rejected steps, final error) with
the archived medians of the three Picasso replicas in reproducibility/toms.
Counters must agree exactly.  Final errors must agree within the action
tolerance times the solution scale: the final error is a difference of nearly
equal quantities, and rounding in the inner products of the Krylov backends
depends on the BLAS build, so a different machine changes it at that level
while the step sequences and work counters stay identical.
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from pyexpint import ETD34Options, solve_etd34

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "toms_timing_balanced", ROOT / "hpc" / "picasso" / "python" / "toms_timing_balanced.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

FIELDS = (("matvecs", "matvecs_median"), ("nonlinear_evals", "nonlinear_evals_median"),
          ("accepted_steps", "accepted_steps_median"), ("rejected_steps", "rejected_steps_median"))


def run(n, rtol, backend_name):
    problem, bounds, exact = harness.make_problem(n)
    action_tol = max(1e-13, min(1e-5, 0.01 * rtol))
    opts = ETD34Options(rtol=rtol, atol=rtol * 1e-3, h0=0.1, h_max=0.2, action_rtol_fraction=0.01)
    sol = solve_etd34(problem, harness.make_backend(backend_name, action_tol, bounds), options=opts)
    st = sol.stats
    return {
        "matvecs": int(st["backend_stats"].get("matvecs", 0)),
        "nonlinear_evals": int(st["nonlinear_evals_estimate"]),
        "nonlinear_evals_exact": int(st.get("nonlinear_evals", -1)),
        "accepted_steps": int(st["accepted_steps"]),
        "rejected_steps": int(st["rejected_steps"]),
        "error_inf": float(np.max(np.abs(sol.y[-1] - exact))),
        "error_tolerance": float(st["action_tolerance"] * np.max(np.abs(exact))),
        "work_sum": float(sum(st["work_per_attempt"]) + sum(st.get("work_per_failed_attempt", []))),
        "accepted_h": [float(x) for x in np.diff(sol.t)],
    }


def main(out_json=None):
    rows, mismatches, worst = [], 0, 0.0
    for n in (64, 128, 256):
        for rtol in (1e-5, 1e-7):
            for b in ("kiops", "leja", "hybrid", "auto"):
                cur = run(n, rtol, b)
                tag = f"case_n{n}_tol{rtol:.0e}".replace("e-0", "e-0") + f"_{b}.json"
                for rep in ("rep1", "rep2", "rep3"):
                    arch = json.loads((ROOT / "reproducibility" / "toms" / rep / "raw" / tag).read_text())
                    bad = [k for k, ak in FIELDS if cur[k] != int(round(arch[ak]))]
                    diff = abs(cur["error_inf"] - arch["error_inf_median"])
                    worst = max(worst, diff / cur["error_tolerance"])
                    if diff > cur["error_tolerance"]:
                        bad.append(f"error_inf (diff {diff:.1e} > {cur['error_tolerance']:.1e})")
                    mismatches += bool(bad)
                    rows.append({"case": tag, "replica": rep, "current": cur,
                                 "archived": {ak: arch[ak] for _, ak in FIELDS} | {"error_inf_median": arch["error_inf_median"]},
                                 "mismatch": bad})
                print(f"n={n:3d} rtol={rtol:.0e} {b:6s} mv={cur['matvecs']:5d} N={cur['nonlinear_evals']:3d} "
                      f"(exact {cur['nonlinear_evals_exact']:3d}) acc/rej={cur['accepted_steps']}/{cur['rejected_steps']} "
                      f"err={cur['error_inf']:.6e} work_sum={cur['work_sum']:.0f} "
                      f"{'OK' if not any(r['mismatch'] for r in rows[-3:]) else 'MISMATCH ' + str([r['mismatch'] for r in rows[-3:]])}")
    print(f"configurations x replicas compared: {len(rows)}; mismatches: {mismatches}; "
          f"largest error difference / tolerance: {worst:.1e}")
    if out_json:
        Path(out_json).write_text(json.dumps({"rows": rows, "mismatches": mismatches}, indent=1))
    return mismatches


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1] if len(sys.argv) > 1 else None) else 0)
