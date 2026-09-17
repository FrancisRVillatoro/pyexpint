#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from scipy.sparse import diags

from pyexpint import (
    AdaptiveOptions, ETD34Options, KROGSTAD, KiopsBackend, LejaBackend,
    SemilinearProblem, solve_adaptive, solve_etd34,
)


def make_problem(n=256, T=1.0, nu=0.12):
    Lx = 2*np.pi
    dx = Lx/n
    x = dx*np.arange(n)
    A = diags([np.ones(n-1), -2*np.ones(n), np.ones(n-1)], [-1,0,1], shape=(n,n), format="lil")
    A[0,n-1] = 1.0
    A[n-1,0] = 1.0
    A = nu*A.tocsr()/dx**2

    def exact(t):
        return 0.2*np.exp(-t)*np.sin(x)

    def nonlinear(t,u):
        ue = exact(t)
        forcing = -ue - A@ue - ue*ue
        return u*u + forcing

    bounds = (-4*nu/dx**2, 0.0)
    return SemilinearProblem(A, nonlinear, exact(0.0), (0.0,T), exact_solution=exact), bounds


def backend_factory(name, bounds, tol):
    if name == "kiops":
        return KiopsBackend(tol=tol, m_init=10, m_min=6, m_max=64)
    if name == "leja":
        return LejaBackend(tol=tol, spectral_bounds=bounds, max_degree=120, target_width=10.0)
    raise KeyError(name)


def run():
    problem, bounds = make_problem()
    exact = problem.exact_solution(problem.t_span[1])
    rows = []
    for bname in ("kiops","leja"):
        for rtol in (1e-4, 1e-6):
            # Step doubling baseline.
            b = backend_factory(bname, bounds, rtol*0.01)
            opts = AdaptiveOptions(
                rtol=rtol, atol=rtol*1e-3, h0=0.2, h_max=0.5,
                action_rtol_fraction=0.01,
            )
            t0=time.perf_counter(); sol=solve_adaptive(problem,KROGSTAD,b,options=opts); wall=time.perf_counter()-t0
            st=sol.stats["backend_stats"]
            rows.append({
                "backend":bname,"rtol":rtol,"controller":"step-doubling",
                "wall_seconds":wall,"error_inf":float(np.max(np.abs(sol.y[-1]-exact))),
                "accepted":sol.stats["accepted_steps"],"rejected":sol.stats["rejected_steps"],
                "nonlinear_evals":sol.stats["nonlinear_evals_estimate"],
                "matvecs":st.get("matvecs",0),
            })

            for controller in ("accuracy","cost"):
                b = backend_factory(bname, bounds, rtol*0.01)
                eopts = ETD34Options(
                    rtol=rtol, atol=rtol*1e-3, h0=0.2, h_max=0.5,
                    action_rtol_fraction=0.01, controller=controller,
                    cost_metric="matvecs",
                )
                t0=time.perf_counter(); sol=solve_etd34(problem,b,options=eopts); wall=time.perf_counter()-t0
                st=sol.stats["backend_stats"]
                rows.append({
                    "backend":bname,"rtol":rtol,"controller":f"embedded-{controller}",
                    "wall_seconds":wall,"error_inf":float(np.max(np.abs(sol.y[-1]-exact))),
                    "accepted":sol.stats["accepted_steps"],"rejected":sol.stats["rejected_steps"],
                    "nonlinear_evals":sol.stats["nonlinear_evals_estimate"],
                    "matvecs":st.get("matvecs",0),
                    "cost_limited_steps":sol.stats["cost_limited_steps"],
                })

    out={"problem":"periodic manufactured reaction-diffusion","n":problem.y0.size,"cases":rows}
    Path("phase7_embedded_vs_doubling.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out


if __name__=="__main__":
    out=run()
    for r in out["cases"]:
        print(r["backend"],r["rtol"],r["controller"],
              f"err={r['error_inf']:.2e}",f"t={r['wall_seconds']:.4f}",
              f"mv={r['matvecs']}",f"N={r['nonlinear_evals']}",
              f"a/r={r['accepted']}/{r['rejected']}")
