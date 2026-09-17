#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from scipy.sparse.linalg import LinearOperator

from pyexpint import ALL_METHODS, DiagonalBackend, KiopsBackend, LejaBackend, SemilinearProblem, solve_fixed


def run():
    n=32
    lam=np.linspace(-4.0,-0.1,n)
    op=LinearOperator((n,n),matvec=lambda x:lam*x,dtype=float)
    y0=.05+.01*np.sin(np.linspace(0,np.pi,n))
    f=lambda t,y:.1*y*y
    T,h=.35,.05
    pd=SemilinearProblem(lam,f,y0,(0,T))
    po=SemilinearProblem(op,f,y0,(0,T))
    out={"n":n,"T":T,"h":h,"backends":{}}
    factories={
        "kiops":lambda:KiopsBackend(tol=2e-10,m_init=8,m_min=6,m_max=36),
        "leja":lambda:LejaBackend(tol=2e-10,spectral_bounds=(lam.min(),lam.max()),max_degree=100,target_width=8),
    }
    for label,factory in factories.items():
        t0=time.perf_counter(); rows=[]; total_mv=0
        for method in ALL_METHODS:
            ref=solve_fixed(pd,method,h,DiagonalBackend()).y[-1]
            b=factory(); sol=solve_fixed(po,method,h,b)
            err=float(np.max(np.abs(sol.y[-1]-ref)))
            st=sol.stats.get("backend_stats",{})
            total_mv += st.get("matvecs",0)
            rows.append({"method":method.name,"error":err,"matvecs":st.get("matvecs",0)})
        out["backends"][label]={
            "wall_seconds":time.perf_counter()-t0,
            "max_error":max(r["error"] for r in rows),
            "total_matvecs":total_mv,
            "methods":rows,
        }
    return out

if __name__ == "__main__":
    result=run(); path=Path("phase5_modern_backend_catalogue.json")
    path.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(path)
    for k,v in result["backends"].items(): print(k,v["wall_seconds"],v["max_error"],v["total_matvecs"])
