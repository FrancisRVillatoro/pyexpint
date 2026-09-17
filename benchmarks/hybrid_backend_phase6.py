#!/usr/bin/env python3
from __future__ import annotations
import json,time
from pathlib import Path
import numpy as np
from scipy.sparse import diags
from pyexpint import KiopsBackend, LejaBackend, ScipyKiopsBackend, SemilinearProblem, get_method, solve_fixed


def medsolve(p,m,bf,h,reps=3):
    ts=[]; sol=None
    for _ in range(reps):
        b=bf(); t=time.perf_counter(); sol=solve_fixed(p,m,h,b); ts.append(time.perf_counter()-t)
    return float(np.median(ts)),sol

def run():
    rows=[]; h=.05
    for n in (256,1024):
      sigma=100.; A=sigma*diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],format='csr')
      x=np.linspace(0,1,n+2)[1:-1]; y0=.1*np.sin(np.pi*x); p=SemilinearProblem(A,lambda t,y:.2*y*y,y0,(0,.1))
      for mn in ('Krogstad','HochOst4'):
        m=get_method(mn); sols={}
        for bn,bf in [
          ('kiops',lambda:KiopsBackend(tol=1e-9,m_init=10,m_min=6,m_max=64)),
          ('leja',lambda:LejaBackend(tol=1e-9,spectral_bounds=(-4*sigma,0),max_degree=120,target_width=10.0)),
          ('scipy-kiops',lambda:ScipyKiopsBackend(tol=1e-9,m_init=10,m_min=6,m_max=64)),
        ]:
          dt,sol=medsolve(p,m,bf,h); sols[bn]=sol.y[-1]
          st=sol.stats['backend_stats']; rows.append({'n':n,'method':mn,'backend':bn,'seconds':dt,'matvecs_counted':st.get('matvecs'),'scipy_expm_calls':st.get('scipy_expm_calls',0)})
        ref=sols['kiops']
        for r in rows[-3:]: r['max_abs_difference_vs_kiops']=float(np.max(np.abs(sols[r['backend']]-ref)))
    o={'rows':rows}; Path('phase6_hybrid_backend.json').write_text(json.dumps(o,indent=2),encoding='utf-8'); return o
if __name__=='__main__':
 o=run(); [print(r) for r in o['rows']]
