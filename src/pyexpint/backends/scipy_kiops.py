from __future__ import annotations

"""Hybrid SciPy/KIOPS backend.

Pure exponential actions are delegated to scipy.sparse.linalg.expm_multiply;
phi_{k>=1}, mixed phi combinations, and shifted solves use the independent
KIOPS-style backend.  This exploits a mature optimized kernel without forcing
PyEXPINT methods to know which matrix-function engine is used.
"""

import time
import numpy as np
from scipy.sparse.linalg import expm_multiply

from .base import Backend
from .kiops import KiopsBackend


class _ScipyKiopsContext:
    def __init__(self, backend: "ScipyKiopsBackend", operator, h: float):
        self.backend=backend; self.operator=operator; self.h=float(h)
        self.fallback=backend.kiops.bind(operator,h)

    def _expm(self, scale, v):
        self.backend._stats['scipy_expm_calls'] += 1
        t0=time.perf_counter()
        out=expm_multiply(float(scale)*self.h*self.operator, np.asarray(v))
        self.backend._stats['scipy_expm_seconds'] += time.perf_counter()-t0
        return np.real_if_close(out)

    def phi_action(self,k,scale,v):
        if int(k)==0:
            return self._expm(scale,v)
        return self.fallback.phi_action(k,scale,v)

    def phi_combination_action(self,terms,v):
        terms=[t for t in terms if t.alpha != 0]
        if terms and all(int(t.k)==0 for t in terms):
            scales={float(t.scale) for t in terms}
            if len(scales)==1:
                alpha=sum(float(t.alpha) for t in terms)
                return alpha*self._expm(next(iter(scales)),v)
        return self.fallback.phi_combination_action(terms,v)

    def sum_operator_actions(self,exprs,vectors):
        from ..expressions import PhiCombination, ZeroExpr
        scale=None; rhs=None
        for expr,vec in zip(exprs,vectors):
            if isinstance(expr,ZeroExpr):
                continue
            if not isinstance(expr,PhiCombination) or any(int(t.k)!=0 for t in expr.terms):
                return self.fallback.sum_operator_actions(exprs,vectors)
            scales={float(t.scale) for t in expr.terms}
            if len(scales)!=1:
                return self.fallback.sum_operator_actions(exprs,vectors)
            s=next(iter(scales))
            if scale is None: scale=s
            if s != scale:
                return self.fallback.sum_operator_actions(exprs,vectors)
            coeff=sum(float(t.alpha) for t in expr.terms)
            term=coeff*np.asarray(vec)
            rhs=term if rhs is None else rhs+term
        if rhs is None:
            return np.zeros_like(vectors[0])
        self.backend._stats['scipy_fused_sum_actions'] += 1
        return self._expm(scale,rhs)

    def phi_linear_combination_action(self,vectors_by_k,*,scale=1.0):
        clean={int(k):np.asarray(v) for k,v in vectors_by_k.items() if np.linalg.norm(v)!=0}
        if clean and set(clean)=={0}:
            return self._expm(scale,clean[0])
        return self.fallback.phi_linear_combination_action(vectors_by_k,scale=scale)

    def shifted_solve_action(self,alpha,v):
        return self.fallback.shifted_solve_action(alpha,v)


class ScipyKiopsBackend(Backend):
    name='scipy-kiops'

    def __init__(self,*,tol=1e-10,m_init=12,m_min=8,m_max=64,orth_len=2,delta=1.4):
        self.tol=float(tol)
        self.kiops=KiopsBackend(tol=tol,m_init=m_init,m_min=m_min,m_max=m_max,orth_len=orth_len,delta=delta)
        self.reset_stats()

    def reset_stats(self):
        self.kiops.reset_stats()
        self._stats={'scipy_expm_calls':0,'scipy_fused_sum_actions':0,'scipy_expm_seconds':0.0}

    def bind(self,linear_operator,h):
        return _ScipyKiopsContext(self,linear_operator,h)

    def stats(self):
        ks=self.kiops.stats(); out=dict(ks); out.update(self._stats)
        out['matvecs']=ks.get('matvecs',0)  # SciPy internal matvec count is intentionally unavailable.
        out['tolerance']=self.tol
        return out
