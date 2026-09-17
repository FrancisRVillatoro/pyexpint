#!/usr/bin/env python3
"""Reproduce the Phase-4 47-method catalogue validation."""
import json, math, time
from pathlib import Path
import numpy as np
from scipy.sparse.linalg import LinearOperator
from pyexpint import ALL_METHODS, DiagonalBackend, KrylovBackend, SemilinearProblem, solve_fixed

def exact_riccati(t):
    return np.array([1.0/(1.0+1.5*np.exp(t))])

def main():
    T=1.6; hs=np.array([0.2,0.1,0.05,0.025])
    p=SemilinearProblem(np.array([-1.0]),lambda t,y:y*y,np.array([0.4]),(0.0,T),exact_solution=exact_riccati)
    order=[]
    for method in ALL_METHODS:
        errors=[]
        for h in hs:
            sol=solve_fixed(p,method,float(h),DiagonalBackend())
            errors.append(float(abs(sol.y[-1,0]-exact_riccati(T)[0])))
        slopes=[]
        for i in range(len(hs)-1):
            if errors[i]>0 and errors[i+1]>0 and errors[i+1]<errors[i]:
                slopes.append(math.log(errors[i]/errors[i+1],2.0))
            else: slopes.append(None)
        clean=[s for i,s in enumerate(slopes) if s is not None and errors[i]>5e-14 and errors[i+1]>5e-14]
        order.append({'method':method.name,'classical_order':method.classical_order,'stiff_order':method.stiff_order,
                      'errors':errors,'pairwise_slopes':slopes,'best_clean_slope':max(clean) if clean else None})
    n=64; lam=np.linspace(-2.0,-0.05,n); op=LinearOperator((n,n),matvec=lambda x:lam*x,dtype=float)
    y0=0.04+0.01*np.sin(np.linspace(0,np.pi,n)); Tm=.35; h=.05
    pd=SemilinearProblem(lam,lambda t,y:0.12*y*y,y0,(0,Tm))
    po=SemilinearProblem(op,lambda t,y:0.12*y*y,y0,(0,Tm))
    mx=[]
    for method in ALL_METHODS:
        ref=solve_fixed(pd,method,h,DiagonalBackend())
        kb=KrylovBackend(tol=2e-11,min_dim=6,max_dim=32,check_every=3)
        tic=time.perf_counter(); got=solve_fixed(po,method,h,kb); elapsed=time.perf_counter()-tic
        st=got.stats.get('backend_stats',{})
        mx.append({'method':method.name,'max_abs_error_vs_diagonal':float(np.max(np.abs(got.y[-1]-ref.y[-1]))),
                   'matvecs':st.get('matvecs',0),'krylov_projections':st.get('krylov_projections',0),
                   'augmented_krylov_projections':st.get('augmented_krylov_projections',0),
                   'wall_seconds':elapsed,'main_steps':got.stats.get('main_steps'),'startup_steps':got.stats.get('startup_steps')})
    result={'order_benchmark':{'problem':"y'=-y+y^2, y0=0.4, T=1.6",'hs':hs.tolist(),'methods':order},
            'matrix_free_catalogue':{'n':n,'T':Tm,'h':h,'methods':mx}}
    out=Path('phase4_validation.json'); out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Wrote',out); print('max matrix-free error:',max(r['max_abs_error_vs_diagonal'] for r in mx))
if __name__=='__main__': main()
