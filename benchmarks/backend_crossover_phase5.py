#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from scipy.sparse import diags

from pyexpint import (
    AutoBackend, KiopsBackend, KrylovBackend, LejaBackend,
    SemilinearProblem, get_method, solve_fixed,
)


def make_case(n, sigma, h=0.05):
    A = sigma * diags(
        [np.ones(n-1), -2*np.ones(n), np.ones(n-1)],
        [-1,0,1], format="csr"
    )
    x = np.linspace(0,1,n+2)[1:-1]
    y0 = 0.1*np.sin(np.pi*x)
    p = SemilinearProblem(A, lambda t,y: 0.2*y*y, y0, (0.0, 0.1))
    return A, p


def timed_solve(problem, method, backend, h, reps=2):
    times=[]; last=None
    for _ in range(reps):
        t0=time.perf_counter()
        last=solve_fixed(problem,method,h,backend)
        times.append(time.perf_counter()-t0)
    return float(np.median(times)), last


def run():
    method=get_method("Krogstad")
    cases=[]
    for n in (256,1024,4096):
        for sigma in (50.0,200.0):
            h=0.05
            A,p=make_case(n,sigma,h)
            candidates=[
                ("arnoldi", KrylovBackend(tol=1e-9,min_dim=6,max_dim=64,check_every=3)),
                ("kiops", KiopsBackend(tol=1e-9,m_init=10,m_min=6,m_max=64)),
                ("leja", LejaBackend(tol=1e-9,spectral_bounds=(-4*sigma,0.0),max_degree=120,target_width=10.0)),
                ("auto", AutoBackend(tol=1e-9,leja_min_size=512,leja_width_threshold=200.0)),
            ]
            rows=[]
            sols={}
            for name,b in candidates:
                dt,sol=timed_solve(p,method,b,h,reps=2)
                sols[name]=sol.y[-1]
                st=sol.stats.get("backend_stats",{})
                rows.append({
                    "backend":name,
                    "median_seconds":dt,
                    "matvecs":st.get("matvecs", st.get("selected_backend_stats",{}).get("matvecs")),
                    "selection_counts":st.get("selection_counts"),
                    "mean_krylov_dim":st.get("mean_krylov_dim", st.get("selected_backend_stats",{}).get("mean_krylov_dim")),
                    "mean_degree":st.get("mean_degree", st.get("selected_backend_stats",{}).get("mean_degree")),
                })
            ref=sols["kiops"]
            for row in rows:
                row["max_abs_difference_vs_kiops"] = float(np.max(np.abs(sols[row["backend"]]-ref)))
            fastest=min(rows,key=lambda r:r["median_seconds"])["backend"]
            cases.append({
                "n":n,"sigma":sigma,"h":h,
                "scaled_spectral_width":4*sigma*h,
                "fastest":fastest,
                "rows":rows,
            })
    return {"method":"Krogstad","cases":cases}


if __name__ == "__main__":
    result=run()
    path=Path("phase5_backend_crossover.json")
    path.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(path)
    for c in result["cases"]:
        print(c["n"],c["scaled_spectral_width"],c["fastest"],[(r["backend"],round(r["median_seconds"],5)) for r in c["rows"]])
