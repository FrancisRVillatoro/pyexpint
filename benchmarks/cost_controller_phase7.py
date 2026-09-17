#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from scipy.sparse import diags

from pyexpint import ETD34Options, KiopsBackend, SemilinearProblem, solve_etd34


def make_problem(n=512, T=2.0, nu=0.2):
    Lx=2*np.pi; dx=Lx/n; x=dx*np.arange(n)
    A=diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],shape=(n,n),format="lil")
    A[0,n-1]=1.0; A[n-1,0]=1.0
    A=nu*A.tocsr()/dx**2
    def exact(t): return 0.2*np.exp(-t)*np.sin(x)
    def nonlinear(t,u):
        ue=exact(t)
        return u*u + (-ue - A@ue - ue*ue)
    return SemilinearProblem(A,nonlinear,exact(0.0),(0.0,T),exact_solution=exact)


def run():
    p=make_problem()
    exact=p.exact_solution(p.t_span[1])
    rows=[]
    for rtol in (1e-4,1e-6):
        for controller in ("accuracy","cost"):
            backend=KiopsBackend(tol=rtol*0.01,m_init=10,m_min=6,m_max=64)
            opts=ETD34Options(
                rtol=rtol,atol=rtol*1e-3,h0=0.5,h_max=1.5,
                action_rtol_fraction=0.01,controller=controller,cost_metric="matvecs",
            )
            tic=time.perf_counter(); sol=solve_etd34(p,backend,options=opts); wall=time.perf_counter()-tic
            rows.append({
                "rtol":rtol,"controller":controller,
                "error_inf":float(np.max(np.abs(sol.y[-1]-exact))),
                "wall_seconds":wall,
                "matvecs":sol.stats["backend_stats"].get("matvecs",0),
                "accepted_steps":sol.stats["accepted_steps"],
                "rejected_steps":sol.stats["rejected_steps"],
                "nonlinear_evals":sol.stats["nonlinear_evals_estimate"],
                "cost_limited_steps":sol.stats["cost_limited_steps"],
                "step_sizes":sol.stats["step_sizes"],
            })
    out={"description":"Phase-7 cost-aware ETD34 stress benchmark","n":p.y0.size,"T":p.t_span[1],"cases":rows}
    Path("phase7_cost_controller.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out


if __name__=="__main__":
    out=run()
    for r in out["cases"]:
        print(r["rtol"],r["controller"],f"err={r['error_inf']:.2e}",
              f"wall={r['wall_seconds']:.3f}",f"mv={r['matvecs']}",
              f"steps={r['accepted_steps']}/{r['rejected_steps']}",
              f"costlim={r['cost_limited_steps']}")
