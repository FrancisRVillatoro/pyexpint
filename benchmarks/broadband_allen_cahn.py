#!/usr/bin/env python3
"""Adaptive work and accuracy on a broadband problem without manufactured forcing.

One-dimensional Allen-Cahn equation u_t = eps u_xx + u - u^3 on the periodic
interval [0, 1) with eps = 2.5e-4, second differences on n = 1024 points, a seeded
random smooth field (modes 1 to 6, seed 7) passed through tanh(4 u) as initial
state, so that six fronts of width about sqrt(eps) form at once and persist, and
T = 1.  The output records the number of fronts and the number of Fourier modes
that carry 99.99 % of the energy at t = 0 and at t = T.  The nonlinear term depends on the state only, so every
estimator sees it.  The reference is a fixed-step HochOst4 solution with
h = 1/4096 and KIOPS-type actions at tolerance 1e-13, whose accuracy is
established by comparison with h = 1/2048.  ETD34 is run with
the KIOPS-type and real-Leja realizations and the generic step-doubling
controller with Krogstad and KIOPS-type actions, at relative tolerances from
1e-4 to 1e-9.  Wall times are medians of repeated solves on the machine recorded
in the output and are local evidence only.

Usage: python benchmarks/broadband_allen_cahn.py OUT.json [REPEATS] [REFERENCE_STEPS]
(the reference uses REFERENCE_STEPS, default 4096, and REFERENCE_STEPS/2 for its check)
"""
import json
import platform
import sys
import time

import numpy as np
import scipy.sparse as sp
from scipy.fft import rfft

import pyexpint
from pyexpint import (ETD34Options, AdaptiveOptions, HOCHOST4, KROGSTAD, KiopsBackend, LejaBackend,
                      SemilinearProblem, solve_adaptive, solve_etd34, solve_fixed)

N, EPS, T, SEED, MODES = 1024, 2.5e-4, 1.0, 7, 6
RTOLS = (1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9)


def make_problem():
    dx = 1.0 / N
    x = np.arange(N) * dx
    L = (EPS / dx**2) * sp.diags([np.ones(N - 1), -2.0 * np.ones(N), np.ones(N - 1), [1.0], [1.0]],
                                 [-1, 0, 1, N - 1, -(N - 1)], format="csr")
    rng = np.random.default_rng(SEED)
    coefficients = []   # (cos coefficient, sin coefficient) of mode k, drawn in this order
    field = np.zeros(N)
    for k in range(1, MODES + 1):
        a, b = rng.standard_normal() / k, rng.standard_normal() / k
        coefficients.append((float(a), float(b)))
        field += a * np.cos(2 * np.pi * k * x) + b * np.sin(2 * np.pi * k * x)
    u0 = np.tanh(4.0 * field / np.max(np.abs(field)))
    rho = 4.0 * EPS / dx**2
    problem = SemilinearProblem(L, lambda t, u: u - u**3, u0, (0.0, T))
    construction = {"seed": SEED, "modes": MODES, "coefficients": coefficients,
                    "rule": "u0 = tanh(4 f / max|f|), f = sum_k a_k cos(2 pi k x) + b_k sin(2 pi k x), x = j/N"}
    return problem, (-rho, 0.0), construction


def modes_for_energy(u, fraction=0.9999):
    energy = np.abs(rfft(u))**2
    energy[0] = 0.0
    cumulative = np.cumsum(energy) / energy.sum()
    return int(np.searchsorted(cumulative, fraction))


def fronts(u):
    return int(np.sum(np.diff(np.sign(np.r_[u, u[0]])) != 0))


def timed(fn, repeats):
    times, out = [], None
    for _ in range(repeats):
        t0 = time.perf_counter(); out = fn(); times.append(time.perf_counter() - t0)
    return out, times


def run(repeats=5, reference_steps=4096):
    problem, bounds, construction = make_problem()
    ref = solve_fixed(problem, HOCHOST4, T / reference_steps, KiopsBackend(tol=1e-13)).y[-1]
    ref_coarse = solve_fixed(problem, HOCHOST4, T / (reference_steps // 2), KiopsBackend(tol=1e-13)).y[-1]
    reference = {"steps": reference_steps, "method": "HochOst4", "backend": "KiopsBackend(tol=1e-13)",
                 "difference_to_half_steps": float(np.max(np.abs(ref - ref_coarse))),
                 "state": [float(v) for v in ref], "initial_state": [float(v) for v in problem.y0],
                 "max_abs": float(np.max(np.abs(ref))),
                 "fronts_at_0": fronts(problem.y0), "fronts_at_T": fronts(ref),
                 "modes_99_99_percent_energy_at_0": modes_for_energy(problem.y0),
                 "modes_99_99_percent_energy_at_T": modes_for_energy(ref)}
    rows = []
    for rtol in RTOLS:
        atol = 1e-3 * rtol
        options = {"rtol": rtol, "atol": atol, "h0": 0.01, "h_max": 0.2, "action_rtol_fraction": 0.01}
        configs = [
            ("etd34", "kiops", lambda: solve_etd34(problem, KiopsBackend(tol=1e-13), options=ETD34Options(rtol=rtol, atol=atol, h0=0.01, h_max=0.2, action_rtol_fraction=0.01))),
            ("etd34", "leja", lambda: solve_etd34(problem, LejaBackend(tol=1e-13, spectral_bounds=bounds), options=ETD34Options(rtol=rtol, atol=atol, h0=0.01, h_max=0.2, action_rtol_fraction=0.01))),
            ("step_doubling_krogstad", "kiops", lambda: solve_adaptive(problem, KROGSTAD, KiopsBackend(tol=1e-13), options=AdaptiveOptions(rtol=rtol, atol=atol, h0=0.01, h_max=0.2, action_rtol_fraction=0.01))),
        ]
        for controller, backend, fn in configs:
            sol, times = timed(fn, repeats)
            seconds = float(np.median(times))
            st = sol.stats
            rows.append({"controller": controller, "backend": backend, "rtol": rtol, "atol": atol, "options": options,
                         "action_tolerance": float(st.get("action_tolerance", float("nan"))),
                         "error_inf": float(np.max(np.abs(sol.y[-1] - ref))),
                         "matvecs": int(st["backend_stats"]["matvecs"]),
                         "nonlinear_evals": int(st.get("nonlinear_evals", st.get("nonlinear_evals_estimate", -1))),
                         "accepted": int(st["accepted_steps"]), "rejected": int(st["rejected_steps"]),
                         "accepted_h": [float(v) for v in np.diff(sol.t)],
                         "wall_runs_s": [float(v) for v in times], "wall_median_s": seconds})
            print(f"{controller:24s} {backend:6s} rtol {rtol:.0e}: error {rows[-1]['error_inf']:.2e} matvecs {rows[-1]['matvecs']:6d} "
                  f"N-evals {rows[-1]['nonlinear_evals']:5d} acc/rej {rows[-1]['accepted']}/{rows[-1]['rejected']} {seconds:.3f} s", flush=True)
    import os, subprocess
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        commit = "unknown"
    try:
        cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), platform.processor())
    except Exception:
        cpu = platform.processor()
    env = {"python": platform.python_version(), "numpy": np.__version__, "scipy": __import__("scipy").__version__,
           "pyexpint_commit": commit, "platform": platform.platform(), "processor": cpu, "repeats": repeats,
           "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
           "timer": "time.perf_counter around each solve; median of the repeats reported, all repeats archived"}
    return {"problem": "Allen-Cahn 1-D periodic, eps 2.5e-4, n 1024, tanh of random modes 1-6 (seed 7), T 1",
            "parameters": {"N": N, "eps": EPS, "T": T, "seed": SEED, "modes": MODES, "construction": construction},
            "reference": reference, "environment": env, "rows": rows}


if __name__ == "__main__":
    out = run(int(sys.argv[2]) if len(sys.argv) > 2 else 5, int(sys.argv[3]) if len(sys.argv) > 3 else 4096)
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(out, indent=1))
    print("reference:", {k: v for k, v in out["reference"].items() if k not in ("state", "initial_state")})
