#!/usr/bin/env python3
from __future__ import annotations
import json,time
from pathlib import Path
import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import expm_multiply
from pyexpint import KiopsBackend, LejaBackend


def medtime(fn,reps=3):
    ts=[]; out=None
    for _ in range(reps):
        t=time.perf_counter(); out=fn(); ts.append(time.perf_counter()-t)
    return float(np.median(ts)),out


def run():
    rows=[]; rng=np.random.default_rng(1234)
    for n in (256,1024):
        sigma=100.0; h=.05
        A=sigma*diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],format='csr')
        v=rng.standard_normal(n)
        st,ref=medtime(lambda:expm_multiply(h*A,v))
        for name,factory in [
            ('kiops',lambda:KiopsBackend(tol=1e-10,m_init=10,m_min=6,m_max=64)),
            ('leja',lambda:LejaBackend(tol=1e-10,spectral_bounds=(-4*sigma,0),max_degree=120,target_width=10.0)),
        ]:
            def action():
                b=factory(); return b.bind(A,h).phi_action(0,1.0,v)
            dt,out=medtime(action)
            rows.append({'n':n,'backend':name,'seconds':dt,'scipy_seconds':st,'max_abs_error_vs_scipy':float(np.max(np.abs(out-ref)))})
    o={'scipy_version':__import__('scipy').__version__,'operation':'exp(hA)v','rows':rows}
    Path('phase6_scipy_exp_action.json').write_text(json.dumps(o,indent=2),encoding='utf-8'); return o

if __name__=='__main__':
    o=run(); [print(r) for r in o['rows']]
