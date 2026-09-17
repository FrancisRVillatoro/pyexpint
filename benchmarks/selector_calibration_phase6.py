#!/usr/bin/env python3
from __future__ import annotations

import json, platform, time
from pathlib import Path
import numpy as np
from scipy.sparse import diags

from pyexpint import (
    KiopsBackend, LejaBackend, SemilinearProblem, get_method, solve_fixed,
    fit_threshold_selector,
)


def make_case(n, sigma, h):
    A = sigma * diags([np.ones(n-1), -2*np.ones(n), np.ones(n-1)], [-1,0,1], format='csr')
    x=np.linspace(0,1,n+2)[1:-1]
    y0=0.08*np.sin(np.pi*x)
    return A, SemilinearProblem(A, lambda t,y: 0.15*y*y, y0, (0.0,h))


def median_solve(problem, method, backend_factory, h, reps=2):
    vals=[]; last=None
    for _ in range(reps):
        b=backend_factory()
        t0=time.perf_counter(); last=solve_fixed(problem,method,h,b); vals.append(time.perf_counter()-t0)
    return float(np.median(vals)), last


def run():
    h=0.05
    rows=[]
    for method_name in ('Krogstad','HochOst4'):
        m=get_method(method_name)
        for n in (128,256,512,1024,2048):
            for sigma in (25.0,100.0,300.0):
                A,p=make_case(n,sigma,h)
                kt,ks=median_solve(p,m,lambda:KiopsBackend(tol=1e-9,m_init=10,m_min=6,m_max=64),h)
                lt,ls=median_solve(p,m,lambda:LejaBackend(tol=1e-9,spectral_bounds=(-4*sigma,0.0),max_degree=120,target_width=10.0),h)
                diff=float(np.max(np.abs(ks.y[-1]-ls.y[-1])))
                rows.append({
                    'method':method_name,'n':n,'sigma':sigma,'h':h,
                    'scaled_spectral_width':4*sigma*h,
                    'kiops_seconds':kt,'leja_seconds':lt,
                    'fastest':'kiops' if kt<=lt else 'leja',
                    'max_abs_difference':diff,
                })
    label=f"{platform.system()}-{platform.machine()}-Python{platform.python_version()}"
    cal=fit_threshold_selector(rows,machine_label=label)
    out={'machine_label':label,'cases':rows,'calibration':cal.to_dict()}
    Path('phase6_selector_calibration.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    Path('phase6_selector_calibration_model.json').write_text(json.dumps(cal.to_dict(),indent=2),encoding='utf-8')
    return out

if __name__=='__main__':
    o=run(); print(json.dumps(o['calibration'],indent=2))
