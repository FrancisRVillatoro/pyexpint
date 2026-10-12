#!/usr/bin/env python3
"""Ablation of algebraic action fusion (fully specified problem).

Sparse unit tridiagonal operator tridiag(1, -2, 1) of dimension 256, reaction
N(u) = 0.08 u^2, u0 = 0.05 + 0.01 sin(s) with s uniform on [0, pi], T = 0.3,
h = 0.05.  Full Arnoldi (KrylovBackend, tol 1e-10, min_dim 6, max_dim 32,
check_every 3) is switched with its fuse_sums flag.  The KIOPS-type backend has
no switch; its unfused path is obtained by hiding sum_operator_actions from the
bound context, which makes the engine evaluate each action separately.
"""
import json
import sys

import numpy as np
import scipy.sparse as sp

from pyexpint import KiopsBackend, KrylovBackend, SemilinearProblem, get_method, solve_fixed

METHODS = ("ETD4RK", "Krogstad", "HochOst4", "PEC423", "EGLM433", "GenLawson43", "ModGenLawson43")


def make_problem(n=256):
    A = sp.diags([np.ones(n - 1), -2.0 * np.ones(n), np.ones(n - 1)], [-1, 0, 1], format="csr")
    u0 = 0.05 + 0.01 * np.sin(np.linspace(0.0, np.pi, n))
    return SemilinearProblem(A, lambda t, y: 0.08 * y * y, u0, (0.0, 0.3))


class _NoSumFusion:
    def __init__(self, ctx):
        self._ctx = ctx

    def __getattr__(self, name):
        if name == "sum_operator_actions":
            raise AttributeError(name)
        return getattr(self._ctx, name)


class UnfusedView:
    """Backend view whose bound contexts do not offer fused sums of actions."""

    def __init__(self, inner):
        self.inner = inner
        self.name = f"{inner.name}-unfused"

    def bind(self, linear_operator, h):
        return _NoSumFusion(self.inner.bind(linear_operator, h))

    def stats(self):
        return self.inner.stats()

    def reset_stats(self):
        self.inner.reset_stats()


def run():
    problem = make_problem()
    rows = []
    for name in METHODS:
        method = get_method(name)
        row = {"method": name}
        for label, make in (
            ("arnoldi", lambda fuse: KrylovBackend(tol=1e-10, min_dim=6, max_dim=32, check_every=3, fuse_sums=fuse)),
            ("kiops", lambda fuse: KiopsBackend(tol=1e-10) if fuse else UnfusedView(KiopsBackend(tol=1e-10))),
        ):
            finals = {}
            for fuse in (False, True):
                backend = make(fuse)
                sol = solve_fixed(problem, method, 0.05, backend)
                finals[fuse] = sol.y[-1]
                row[f"{label}_matvecs_{'fused' if fuse else 'unfused'}"] = int(backend.stats()["matvecs"])
            row[f"{label}_final_state_rel_diff"] = float(
                np.max(np.abs(finals[True] - finals[False])) / np.max(np.abs(finals[False])))
        rows.append(row)
    # Sensitivity of the full-Arnoldi counts to the initial state: the same seven
    # methods with three other initial profiles (archived so that the text can say
    # which counts depend on the state and which do not).
    s = np.linspace(0.0, np.pi, 256)
    alternatives = {"0.04 + 0.01 sin(s)": 0.04 + 0.01 * np.sin(s),
                    "sin(s)": np.sin(s),
                    "0.1 exp(-50 (x - 0.5)^2), x uniform on [0, 1]": 0.1 * np.exp(-50.0 * (np.linspace(0.0, 1.0, 256) - 0.5) ** 2)}
    sensitivity = []
    for label, u0 in alternatives.items():
        alt = SemilinearProblem(problem.linear_operator, lambda t, y: 0.08 * y * y, u0, (0.0, 0.3))
        for name in METHODS:
            counts = {}
            for fuse in (False, True):
                backend = KrylovBackend(tol=1e-10, min_dim=6, max_dim=32, check_every=3, fuse_sums=fuse)
                solve_fixed(alt, get_method(name), 0.05, backend)
                counts["fused" if fuse else "unfused"] = int(backend.stats()["matvecs"])
            sensitivity.append({"u0": label, "method": name, **counts})
    return {"n": 256, "T": 0.3, "h": 0.05, "reaction": "0.08 u^2",
            "u0": "0.05 + 0.01 sin(s), s uniform on [0, pi]", "action_tol": 1e-10, "rows": rows,
            "initial_state_sensitivity_arnoldi": sensitivity}


if __name__ == "__main__":
    out = run()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(out, indent=1))
    for r in out["rows"]:
        print(f"{r['method']:15s} arnoldi {r['arnoldi_matvecs_unfused']:5d} -> {r['arnoldi_matvecs_fused']:5d} "
              f"kiops {r['kiops_matvecs_unfused']:5d} -> {r['kiops_matvecs_fused']:5d}  "
              f"agreement {r['arnoldi_final_state_rel_diff']:.1e} / {r['kiops_final_state_rel_diff']:.1e}")
