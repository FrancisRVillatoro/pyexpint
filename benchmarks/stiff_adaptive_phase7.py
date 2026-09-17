#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stiff_order_hochbruck_ostermann import make_problem

from pyexpint import (
    AdaptiveOptions, DiagonalBackend, ETD34Options, KROGSTAD,
    solve_adaptive, solve_etd34,
)


def run():
    rows=[]
    for variant in (1,2):
        p,to_phys,exact_phys=make_problem(n=100,variant=variant)
        for tol in (1e-4,1e-6):
            tic=time.perf_counter()
            emb=solve_etd34(
                p,DiagonalBackend(),
                options=ETD34Options(rtol=tol,atol=tol*1e-3,h0=0.1,h_max=0.25),
            )
            tw=time.perf_counter()-tic
            rows.append({
                "variant":variant,"rtol":tol,"controller":"embedded-ETD34",
                "error_inf":float(np.max(np.abs(to_phys(emb.y[-1])-exact_phys(1.0)))),
                "wall_seconds":tw,
                "accepted":emb.stats["accepted_steps"],"rejected":emb.stats["rejected_steps"],
                "nonlinear_evals":emb.stats["nonlinear_evals_estimate"],
            })

            tic=time.perf_counter()
            dbl=solve_adaptive(
                p,KROGSTAD,DiagonalBackend(),
                options=AdaptiveOptions(rtol=tol,atol=tol*1e-3,h0=0.1,h_max=0.25),
            )
            tw=time.perf_counter()-tic
            rows.append({
                "variant":variant,"rtol":tol,"controller":"step-doubling",
                "error_inf":float(np.max(np.abs(to_phys(dbl.y[-1])-exact_phys(1.0)))),
                "wall_seconds":tw,
                "accepted":dbl.stats["accepted_steps"],"rejected":dbl.stats["rejected_steps"],
                "nonlinear_evals":dbl.stats["nonlinear_evals_estimate"],
            })
    out={"description":"Adaptive Krogstad comparison on Hochbruck-Ostermann 2005 problems","n":100,"cases":rows}
    Path("phase7_stiff_adaptive.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out

if __name__=="__main__":
    out=run()
    for r in out["cases"]:
        print(r["variant"],r["rtol"],r["controller"],f"err={r['error_inf']:.2e}",
              f"N={r['nonlinear_evals']}",f"steps={r['accepted']}/{r['rejected']}")
