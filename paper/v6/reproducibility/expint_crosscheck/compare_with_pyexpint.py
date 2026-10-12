#!/usr/bin/env python3
"""Compare PyEXPINT with the original EXPINT (2005) schemes run by crosscheck_expint.m.

Usage:  python compare_with_pyexpint.py RESULTS_DIR
Reads expint_values.csv and mgl45_coeffs.csv from RESULTS_DIR, runs the same two
problems with PyEXPINT (scalar problem with DiagonalBackend and exact startup; dense
2 x 2 problem with DenseBackend and the default HochOst4 startup) and writes
crosscheck_report.txt.  Exit status 0 when every PyEXPINT method either agrees with
the original scheme to 1e-12 or is one of the five documented reconciliations.
"""
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from pyexpint import ALL_METHODS, DenseBackend, DiagonalBackend, SemilinearProblem, get_method, solve_fixed  # noqa: E402

CORRECTED = {"etd2rk", "etd2cf3", "etd5rkf", "ablawson2"}   # one-line corrections of the 2005 files
REGENERATED = {"modgenlawson45"}                            # output coefficients regenerated from the published construction
TOL = 1e-12


def main(results):
    results = Path(results)
    ex = {}
    for r in csv.DictReader(open(results / "expint_values.csv")):
        ex[(r["scheme"], r["problem"])] = np.array([float(r["y1"]), float(r["y2"])])
    exact = lambda t: np.array([1.0 / (1.0 + 1.5 * np.exp(t))])
    PS = SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, np.array([0.4]), (0.0, 1.6), exact_solution=exact)
    PM = SemilinearProblem(np.array([[-1.0, 0.3], [0.2, -2.0]]), lambda t, y: y * y, np.array([0.4, 0.3]), (0.0, 1.6))
    lines, ok = [], True
    agree, reconciled = [], []
    worst_s = worst_m = 0.0
    for m in ALL_METHODS:
        key = m.name.lower()
        if (key, "S") not in ex:
            lines.append(f"{m.name}: no EXPINT scheme file"); ok = False
            continue
        ys = solve_fixed(PS, m, 0.1, DiagonalBackend()).y[-1]
        ym = solve_fixed(PM, m, 0.1, DenseBackend()).y[-1]
        ds = abs(ys[0] - ex[(key, "S")][0]) / abs(ex[(key, "S")][0])
        dm = float(np.max(np.abs(ym - ex[(key, "M")])) / np.max(np.abs(ex[(key, "M")])))
        if ds < TOL and dm < TOL:
            agree.append(m.name); worst_s, worst_m = max(worst_s, ds), max(worst_m, dm)
            continue
        if key in CORRECTED:
            cs = abs(ys[0] - ex[(key + "_corrected", "S")][0]) / abs(ex[(key + "_corrected", "S")][0])
            cm = float(np.max(np.abs(ym - ex[(key + "_corrected", "M")])) / np.max(np.abs(ex[(key + "_corrected", "M")])))
            status = "OK" if cs < TOL and cm < TOL else "UNEXPECTED"
            ok &= status == "OK"
            reconciled.append(f"{m.name}: differs from the 2005 file (scalar {ds:.1e}, matrix {dm:.1e}); "
                              f"agrees with its one-line correction (scalar {cs:.1e}, matrix {cm:.1e}) {status}")
        elif key in REGENERATED:
            reconciled.append(f"{m.name}: differs from the 2005 file (scalar {ds:.1e}, matrix {dm:.1e}); "
                              "output coefficients regenerated from the published construction")
        else:
            lines.append(f"{m.name}: UNDOCUMENTED difference from the 2005 file (scalar {ds:.1e}, matrix {dm:.1e})"); ok = False
    coeff_lines = []
    ref = {(r["matrix"], int(r["i"]), int(r["j"])): float(r["value"]) for r in csv.DictReader(open(results / "mgl45_coeffs.csv"))}
    ctx = DiagonalBackend().bind(np.array([-0.3]), 1.0)
    mgl = get_method("ModGenLawson45")
    for tag in ("U", "V", "A", "B"):
        for i, row in enumerate(getattr(mgl, tag), 1):
            for j, x in enumerate(row, 1):
                v = None if x is None else (float(x) if np.isscalar(x) else float(np.real(x.apply(ctx, np.array([1.0]))[0])))
                r = ref.get((tag, i, j))
                if (v or 0.0) != (r or 0.0) and abs((v or 0.0) - (r or 0.0)) > 1e-12 * max(1.0, abs(r or 0.0)):
                    coeff_lines.append(f"  {tag}[{i},{j}]  PyEXPINT {v if v is not None else 0.0:+.15f}  EXPINT 2005 {r if r is not None else 0.0:+.15f}")
    report = [
        f"PyEXPINT methods compared with the original EXPINT schemes: {len(agree) + len(reconciled) + len(lines)}",
        f"agree to {TOL:g} on both problems: {len(agree)} (largest relative difference: scalar {worst_s:.1e}, matrix {worst_m:.1e})",
        *reconciled,
        *lines,
        "ModGenLawson45 coefficient functions at z = -0.3 that differ:",
        *coeff_lines,
        f"RESULT: {'OK' if ok else 'NOT OK'}",
    ]
    (results / "crosscheck_report.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results"))
