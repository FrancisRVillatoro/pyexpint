#!/usr/bin/env python3
from __future__ import annotations
import json,time
from pathlib import Path
import numpy as np
from pyexpint import AdaptiveOptions, KiopsBackend, LejaBackend, get_method, solve_adaptive
from benchmarks.work_precision_phase6 import periodic_problem


def run():
    A,p,bounds=periodic_problem(n=128,T=1.0)
    exact=p.exact_solution(1.0)
    rows=[]; rtol=1e-6; m=get_method('Krogstad')
    for bname,factory in [
        ('kiops',lambda:KiopsBackend(tol=1e-9,m_init=10,m_min=6,m_max=64)),
        ('leja',lambda:LejaBackend(tol=1e-9,spectral_bounds=bounds,max_degree=120,target_width=10.0)),
    ]:
        for frac in (1.0,0.1,0.03,0.01,0.003):
            b=factory(); opts=AdaptiveOptions(rtol=rtol,atol=1e-9,h0=.25,h_max=.4,action_rtol_fraction=frac)
            t0=time.perf_counter(); sol=solve_adaptive(p,m,b,options=opts); dt=time.perf_counter()-t0
            st=sol.stats['backend_stats']
            rows.append({
                'backend':bname,'rtol':rtol,'action_fraction':frac,
                'action_tolerance':sol.stats['action_tolerance'],
                'error_inf':float(np.max(np.abs(sol.y[-1]-exact))),
                'wall_seconds':dt,'accepted_steps':sol.stats['accepted_steps'],
                'rejected_steps':sol.stats['rejected_steps'],'matvecs':st.get('matvecs'),
            })
    out={'problem':'periodic manufactured diffusion n=128 T=1','method':'Krogstad','rows':rows}
    Path('phase6_action_tolerance.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    return out

if __name__=='__main__':
    o=run()
    for r in o['rows']:
        print(r)
