#!/usr/bin/env python3
from __future__ import annotations
import json, platform, statistics, time, os, sys
from pathlib import Path
import numpy as np
import scipy
from scipy.sparse import diags, eye, kron

from pyexpint import (
    AutoBackend, ETD34Options, KiopsBackend, LejaBackend,
    ScipyKiopsBackend, SemilinearProblem, solve_etd34,
)
from pyexpint.metrics import estimated_backend_workspace_bytes


def make_problem(n=64, T=0.5, nu=0.02):
    Lx = 2*np.pi
    dx = Lx/n
    x = dx*np.arange(n)
    X,Y = np.meshgrid(x,x,indexing='ij')
    D = diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],shape=(n,n),format='lil')
    D[0,n-1]=1.0; D[n-1,0]=1.0
    D = D.tocsr()/dx**2
    I = eye(n,format='csr')
    A = nu*(kron(I,D,format='csr') + kron(D,I,format='csr'))
    shape=(n,n)
    def exact(t):
        return (0.2*np.exp(-t)*np.sin(X)*np.sin(Y)).reshape(-1)
    def nonlinear(t,u):
        ue=exact(t)
        forcing = -ue - A@ue - ue*ue
        return u*u + forcing
    bounds=(-8*nu/dx**2,0.0)
    p=SemilinearProblem(A,nonlinear,exact(0.0),(0.0,T),exact_solution=exact)
    return A,p,bounds


def backend_factory(name,tol,bounds):
    if name=='kiops':
        return KiopsBackend(tol=tol,m_init=10,m_min=6,m_max=64)
    if name=='leja':
        return LejaBackend(tol=tol,spectral_bounds=bounds,max_degree=140,target_width=10.0)
    if name=='hybrid':
        return ScipyKiopsBackend(tol=tol)
    if name=='auto':
        return AutoBackend(tol=tol,leja_min_size=512,leja_width_threshold=200.0,leja_target_width=10.0)
    raise KeyError(name)


def qstats(xs):
    xs=sorted(float(x) for x in xs)
    med=float(statistics.median(xs))
    q1=float(np.quantile(xs,0.25,method='linear'))
    q3=float(np.quantile(xs,0.75,method='linear'))
    return med,q1,q3


def workspace(name,stats):
    if name=='auto':
        last=stats.get('last_selected')
        sub=stats.get('selected_backend_stats',{})
        return estimated_backend_workspace_bytes(last or '',sub)
    if name=='hybrid':
        return estimated_backend_workspace_bytes('kiops',stats)
    return estimated_backend_workspace_bytes(name,stats)


def run_case(n,rtol,bname,repeats=3):
    _,p,bounds=make_problem(n=n)
    exact=p.exact_solution(p.t_span[1])
    action_tol=max(1e-13,min(1e-5,0.01*rtol))
    opts=ETD34Options(rtol=rtol,atol=rtol*1e-3,h0=0.1,h_max=0.2,action_rtol_fraction=0.01)

    # warmup excluded
    b=backend_factory(bname,action_tol,bounds)
    solve_etd34(p,b,options=opts)

    times=[]; errs=[]; matvecs=[]; nevals=[]; accepted=[]; rejected=[]; workspaces=[]; selections=[]
    for _ in range(repeats):
        b=backend_factory(bname,action_tol,bounds)
        tic=time.perf_counter(); sol=solve_etd34(p,b,options=opts); wall=time.perf_counter()-tic
        st=sol.stats['backend_stats']
        times.append(wall)
        errs.append(float(np.max(np.abs(sol.y[-1]-exact))))
        matvecs.append(int(st.get('matvecs',0) or 0))
        nevals.append(int(sol.stats['nonlinear_evals_estimate']))
        accepted.append(int(sol.stats['accepted_steps']))
        rejected.append(int(sol.stats['rejected_steps']))
        workspaces.append(workspace(bname,st))
        selections.append(st.get('selection_counts'))
    med,q1,q3=qstats(times)
    return {
        'n_side':n,'dimension':n*n,'rtol':rtol,'backend':bname,'repeats':repeats,
        'wall_median_s':med,'wall_q1_s':q1,'wall_q3_s':q3,'wall_iqr_s':q3-q1,
        'wall_runs_s':times,
        'error_inf_median':float(statistics.median(errs)),
        'matvecs_median':float(statistics.median(matvecs)),
        'nonlinear_evals_median':float(statistics.median(nevals)),
        'accepted_steps_median':float(statistics.median(accepted)),
        'rejected_steps_median':float(statistics.median(rejected)),
        'workspace_bytes_estimate':next((x for x in workspaces if x is not None),None),
        'selection_counts':next((x for x in selections if x is not None),None),
    }


def main():
    cases=[]
    design=[]
    for n in (32,64,128):
        design.append((n,1e-5))
    design.append((64,1e-7))
    for n,rtol in design:
        for b in ('kiops','leja','hybrid','auto'):
            print('running',n,rtol,b,flush=True)
            cases.append(run_case(n,rtol,b,repeats=3))
    out={
        'description':'PyEXPINT pre-release controlled 2D reaction-diffusion benchmark',
        'problem':'u_t = nu Delta u + N(t,u), periodic 2D manufactured solution 0.2 exp(-t) sin(x) sin(y)',
        'T':0.5,'nu':0.02,
        'environment':{
            'python':sys.version.split()[0], 'numpy':np.__version__, 'scipy':scipy.__version__,
            'platform':platform.platform(), 'machine':platform.machine(), 'processor':platform.processor(),
            'cpu_count':os.cpu_count(),
        },
        'timing_protocol':'one warm-up + 3 measured repetitions; report median and IQR',
        'cases':cases,
    }
    Path('prerelease_2d.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    for r in cases:
        print(f"N={r['dimension']:5d} tol={r['rtol']:.0e} {r['backend']:6s} med={r['wall_median_s']:.4f}s IQR={r['wall_iqr_s']:.4f} err={r['error_inf_median']:.2e} mv={r['matvecs_median']:.0f}")

if __name__=='__main__': main()
