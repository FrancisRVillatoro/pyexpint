#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path
import numpy as np

BACKENDS = ("kiops", "leja", "hybrid", "auto")


def qstats(xs):
    a = np.asarray(xs, float)
    q1, med, q3 = np.quantile(a, [0.25, 0.5, 0.75])
    return float(med), float(q1), float(q3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    raw, out = Path(args.raw_dir), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    data = {}
    for p in raw.glob("case_*.json"):
        d = json.loads(p.read_text())
        data[(d["n_side"], d["rtol"], d["backend"])] = d

    cases = sorted({(n, r) for n, r, _ in data})
    rows, paired = [], []
    for n, rtol in cases:
        base = data[(n, rtol, "kiops")]
        base_by_block = dict(zip(base["block_ids"], base["wall_runs_s"]))
        for b in BACKENDS:
            d = data[(n, rtol, b)]
            iqr_pct = 100*d["wall_iqr_s"]/d["wall_median_s"]
            rows.append({
                "n_side": n, "dimension": n*n, "rtol": rtol, "backend": b,
                "median_s": d["wall_median_s"], "iqr_s": d["wall_iqr_s"],
                "iqr_pct": iqr_pct, "cpu_time_median_s": d.get("cpu_time_median_s"), "error_inf": d["error_inf_median"],
                "matvecs": d["matvecs_median"],
                "nonlinear_evals": d["nonlinear_evals_median"],
                "auto_last_selected": ";".join(str(x) for x in d.get("last_selected_runs", [])),
            })
            if b != "kiops":
                d_by_block = dict(zip(d["block_ids"], d["wall_runs_s"]))
                blocks = sorted(set(base_by_block) & set(d_by_block))
                ratios = [d_by_block[k]/base_by_block[k] for k in blocks]
                med, q1, q3 = qstats(ratios)
                paired.append({
                    "n_side": n, "dimension": n*n, "rtol": rtol,
                    "backend": b, "baseline": "kiops", "n_pairs": len(ratios),
                    "paired_ratio_median": med, "paired_ratio_q1": q1,
                    "paired_ratio_q3": q3, "paired_ratio_iqr": q3-q1,
                })

    with open(out/"toms_timing_summary.csv", "w", newline="") as f:
        fields = list(rows[0]) if rows else []
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    with open(out/"toms_paired_speedups.csv", "w", newline="") as f:
        fields = list(paired[0]) if paired else []
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(paired)

    report = {"cases": rows, "paired_vs_kiops": paired}
    (out/"toms_timing_analysis.json").write_text(json.dumps(report, indent=2))

    for p in paired:
        print(f"N={p['dimension']:6d} tol={p['rtol']:.0e} {p['backend']:6s}/kiops "
              f"paired median={p['paired_ratio_median']:.3f} "
              f"IQR=[{p['paired_ratio_q1']:.3f},{p['paired_ratio_q3']:.3f}]")
    print("TOMS_TIMING_ANALYSIS_FINISHED=1")

if __name__ == "__main__": main()
