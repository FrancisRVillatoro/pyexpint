#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--jobid", default="")
    ap.add_argument("--expected-cases", type=int, required=True)
    args = ap.parse_args()
    if args.expected_cases < 1:
        raise SystemExit("--expected-cases must be >=1")

    run, out = Path(args.run_dir), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted((run/"results"/"raw").glob("*.json"))
    rows = [json.loads(p.read_text()) for p in files]
    rows.sort(key=lambda x: (x["dimension"], x["rtol"], x["backend"]))

    summary = {
        "schema_version": 2,
        "campaign_id": rows[0]["campaign_id"] if rows else run.name,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "jobid": args.jobid,
        "n_cases": len(rows),
        "expected_cases": args.expected_cases,
        "complete": len(rows) == args.expected_cases,
        "source_manifest_sha256": rows[0].get("source_manifest_sha256") if rows else None,
        "protocol_id": rows[0].get("protocol_id") if rows else None,
        "cases": rows,
    }
    (out/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fields = ["dimension","n_side","rtol","backend","wall_median_s","wall_iqr_s","cpu_time_median_s",
              "error_inf_median","matvecs_median","nonlinear_evals_median",
              "accepted_steps_median","rejected_steps_median"]
    with open(out/"summary.csv","w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k) for k in fields})

    manifest = {
        "campaign_id": summary["campaign_id"],
        "jobid": args.jobid,
        "n_cases": len(rows),
        "expected_cases": args.expected_cases,
        "complete": summary["complete"],
        "raw_files": [{"name":p.name,"sha256":sha256(p)} for p in files],
    }
    (out/"campaign_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

    print(f"campaign={summary['campaign_id']} cases={len(rows)}/{args.expected_cases} complete={summary['complete']}")
    for r in rows:
        print(f"N={r['dimension']:6d} tol={r['rtol']:.0e} {r['backend']:6s} "
              f"med={r['wall_median_s']:.4f}s IQR={r['wall_iqr_s']:.4f} "
              f"err={r['error_inf_median']:.2e}")
    if not summary["complete"]:
        raise SystemExit(f"incomplete campaign: found {len(rows)}, expected {args.expected_cases}")

if __name__ == "__main__":
    main()
