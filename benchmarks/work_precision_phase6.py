#!/usr/bin/env python3
from __future__ import annotations

import json, time
from pathlib import Path
import numpy as np
from scipy.sparse import diags

from pyexpint import (
    AdaptiveOptions, CalibratedAutoBackend, KiopsBackend, LejaBackend,
    SelectorCalibration, SemilinearProblem, estimated_backend_workspace_bytes,
    get_method, solve_adaptive,
)


def periodic_problem(n=128,T=1.0):
    Lx=2*np.pi; dx=Lx/n; x=dx*np.arange(n)
    A=diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],shape=(n,n),format='lil')
    A[0,n-1]=1; A[n-1,0]=1; A=0.05*(A.tocsr())/dx**2
    def exact(t): return 0.2*np.exp(-t)*np.sin(x)
    def nonlinear(t,u):
        ue=exact(t); forcing=(-ue) - A@ue - ue*ue
        return u*u + forcing
    return A, SemilinearProblem(A,nonlinear,exact(0.0),(0.0,T),exact_solution=exact), (-0.2/dx**2,0.0)


def dirichlet_problem(n=128,T=1.0):
    dx=1/(n+1); x=np.arange(1,n+1)*dx
    A=0.0005*diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],format='csr')/dx**2
    def exact(t): return x*(1-x)*np.exp(t)
    def nonlinear(t,u):
        ue=exact(t); phi=ue - A@ue - 1/(1+ue*ue)
        return 1/(1+u*u)+phi
    return A, SemilinearProblem(A,nonlinear,exact(0.0),(0.0,T),exact_solution=exact), (-0.002/dx**2,0.0)


def workspace(name,st):
    if name.startswith('auto'):
        last=st.get('last_selected')
        sub=st.get(f'{last}_stats', st.get('selected_backend_stats',{})) if last else {}
        return estimated_backend_workspace_bytes(last or '', sub)
    return estimated_backend_workspace_bytes(name, st)


def run():
    cal=SelectorCalibration.from_json('phase6_selector_calibration_model.json')
    cases=[]
    for problem_name,maker in [('periodic',periodic_problem),('dirichlet',dirichlet_problem)]:
        A,p,bounds=maker()
        exact=p.exact_solution(p.t_span[1])
        for method_name in ('Krogstad','HochOst4'):
            m=get_method(method_name)
            for rtol in (1e-4,1e-7):
                factories={
                    'kiops':lambda:KiopsBackend(tol=1e-9,m_init=10,m_min=6,m_max=64),
                    'leja':lambda:LejaBackend(tol=1e-9,spectral_bounds=bounds,max_degree=120,target_width=10.0),
                    'auto-calibrated':lambda:CalibratedAutoBackend(cal,tol=1e-9,leja_target_width=10.0),
                }
                for bname,factory in factories.items():
                    backend=factory()
                    opts=AdaptiveOptions(rtol=rtol,atol=rtol*1e-3,h0=0.25,h_max=0.4,action_rtol_fraction=0.01)
                    t0=time.perf_counter(); sol=solve_adaptive(p,m,backend,options=opts); wall=time.perf_counter()-t0
                    err=float(np.max(np.abs(sol.y[-1]-exact)))
                    st=sol.stats['backend_stats']
                    cases.append({
                        'problem':problem_name,'n':p.y0.size,'method':method_name,'backend':bname,
                        'rtol':rtol,'error_inf':err,'wall_seconds':wall,
                        'accepted_steps':sol.stats['accepted_steps'],'rejected_steps':sol.stats['rejected_steps'],
                        'nonlinear_evals':sol.stats['nonlinear_evals_estimate'],
                        'matvecs':st.get('matvecs',st.get('selected_backend_stats',{}).get('matvecs')),
                        'workspace_bytes_estimate':workspace(bname,st),
                        'action_tolerance':sol.stats['action_tolerance'],
                        'selection_counts':st.get('selection_counts'),
                    })
    out={'description':'Phase-6 adaptive work-precision-workspace benchmark','cases':cases}
    Path('phase6_work_precision.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    return out

if __name__=='__main__':
    o=run();
    for r in o['cases']:
        print(r['problem'],r['method'],r['backend'],r['rtol'],f"err={r['error_inf']:.2e}",f"t={r['wall_seconds']:.3f}",f"mv={r['matvecs']}",r['selection_counts'])
