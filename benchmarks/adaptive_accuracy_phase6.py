#!/usr/bin/env python3
from __future__ import annotations
import json,time
from pathlib import Path
import numpy as np
from pyexpint import AdaptiveOptions, DiagonalBackend, SemilinearProblem, get_method, solve_adaptive


def exact(t): return np.array([1.0/(1.0+4.0*np.exp(t))])

def run():
    p=SemilinearProblem(np.array([-1.0]),lambda t,y:y*y,np.array([0.2]),(0.0,2.0),exact_solution=exact)
    rows=[]
    for name in ('ETD2RK','ETD4RK','Krogstad','HochOst4'):
        m=get_method(name)
        for rtol in (1e-3,1e-5,1e-7):
            o=AdaptiveOptions(rtol=rtol,atol=rtol*1e-3,h0=.3,h_max=.6)
            t0=time.perf_counter(); sol=solve_adaptive(p,m,DiagonalBackend(),options=o); dt=time.perf_counter()-t0
            rows.append({
                'method':name,'rtol':rtol,'error_inf':float(np.max(np.abs(sol.y[-1]-exact(2.0)))),
                'accepted_steps':sol.stats['accepted_steps'],'rejected_steps':sol.stats['rejected_steps'],
                'nonlinear_evals':sol.stats['nonlinear_evals_estimate'],'wall_seconds':dt,
            })
    out={'problem':"y'=-y+y^2, y(0)=0.2, T=2",'rows':rows}
    Path('phase6_adaptive_accuracy.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    return out

if __name__=='__main__':
    o=run();
    for r in o['rows']: print(r)
