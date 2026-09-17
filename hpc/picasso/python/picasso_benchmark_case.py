#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, subprocess, sys, time
from pathlib import Path

import numpy as np
import scipy
from scipy.sparse import diags, eye, kron

from pyexpint import (
    AutoBackend, ETD34Options, KiopsBackend, LejaBackend, ScipyKiopsBackend,
    SemilinearProblem, solve_etd34,
)

def make_problem(n, T=0.5, nu=0.02):
    Lx = 2*np.pi
    dx = Lx/n
    x = dx*np.arange(n)
    X, Y = np.meshgrid(x, x, indexing="ij")
    D = diags([np.ones(n-1), -2*np.ones(n), np.ones(n-1)],
              [-1,0,1], shape=(n,n), format="lil")
    D[0,n-1] = 1.0
    D[n-1,0] = 1.0
    D = D.tocsr()/dx**2
    I = eye(n, format="csr")
    A = nu*(kron(I,D,format="csr") + kron(D,I,format="csr"))

    def exact(t):
        return (0.2*np.exp(-t)*np.sin(X)*np.sin(Y)).reshape(-1)

    def nonlinear(t, u):
        ue = exact(t)
        return u*u + (-ue - A@ue - ue*ue)

    bounds = (-8*nu/dx**2, 0.0)
    return SemilinearProblem(A, nonlinear, exact(0.0), (0.0,T),
                             exact_solution=exact), bounds

def make_backend(name, tol, bounds):
    if name == "kiops":
        return KiopsBackend(tol=tol, m_init=10, m_min=6, m_max=64)
    if name == "leja":
        return LejaBackend(tol=tol, spectral_bounds=bounds,
                           max_degree=160, target_width=10.0)
    if name == "hybrid":
        return ScipyKiopsBackend(tol=tol)
    if name == "auto":
        return AutoBackend(tol=tol, leja_min_size=512,
                           leja_width_threshold=200.0, leja_target_width=10.0)
    raise ValueError(name)

def median_iqr(xs):
    a = np.asarray(xs, float)
    med = float(np.median(a))
    q1 = float(np.quantile(a, .25))
    q3 = float(np.quantile(a, .75))
    return med, q1, q3

def safe_cmd(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"UNAVAILABLE: {type(exc).__name__}: {exc}"

def cpu_model():
    text = safe_cmd(["lscpu"])
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            return line.split(":",1)[1].strip()
    return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--rtol", type=float, required=True)
    ap.add_argument("--backend", choices=["kiops","leja","hybrid","auto"], required=True)
    ap.add_argument("--repeats", type=int, default=7)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    problem, bounds = make_problem(args.n)
    exact = problem.exact_solution(problem.t_span[1])
    atol = args.rtol*1e-3
    action_tol = max(1e-13, min(1e-5, .01*args.rtol))
    opts = ETD34Options(rtol=args.rtol, atol=atol, h0=.1, h_max=.2,
                        action_rtol_fraction=.01)

    # One unmeasured warm-up.
    solve_etd34(problem, make_backend(args.backend, action_tol, bounds), options=opts)

    times, errs, mvs, nevals, accepted, rejected = [], [], [], [], [], []
    stats_last = {}
    for _ in range(args.repeats):
        b = make_backend(args.backend, action_tol, bounds)
        t0 = time.perf_counter()
        sol = solve_etd34(problem, b, options=opts)
        times.append(time.perf_counter() - t0)
        stats_last = sol.stats["backend_stats"]
        errs.append(float(np.max(np.abs(sol.y[-1] - exact))))
        mvs.append(stats_last.get("matvecs", 0))
        nevals.append(sol.stats["nonlinear_evals_estimate"])
        accepted.append(sol.stats["accepted_steps"])
        rejected.append(sol.stats["rejected_steps"])

    med, q1, q3 = median_iqr(times)
    out = {
        "schema_version": 2,
        "campaign_id": os.getenv("PYEXPINT_CAMPAIGN_ID"),
        "source_manifest_sha256": os.getenv("PYEXPINT_SOURCE_MANIFEST_SHA256"),
        "runtime_mode": os.getenv("PYEXPINT_RUNTIME", "source"),
        "n_side": args.n,
        "dimension": args.n**2,
        "rtol": args.rtol,
        "backend": args.backend,
        "repeats": args.repeats,
        "wall_runs_s": times,
        "wall_median_s": med,
        "wall_q1_s": q1,
        "wall_q3_s": q3,
        "wall_iqr_s": q3-q1,
        "error_inf_median": float(np.median(errs)),
        "matvecs_median": float(np.median(mvs)),
        "nonlinear_evals_median": float(np.median(nevals)),
        "accepted_steps_median": float(np.median(accepted)),
        "rejected_steps_median": float(np.median(rejected)),
        "backend_stats_last": stats_last,
        "slurm": {
            "job_id": os.getenv("SLURM_JOB_ID"),
            "array_job_id": os.getenv("SLURM_ARRAY_JOB_ID"),
            "array_task_id": os.getenv("SLURM_ARRAY_TASK_ID"),
            "job_nodelist": os.getenv("SLURM_JOB_NODELIST"),
            "job_partition": os.getenv("SLURM_JOB_PARTITION"),
            "cpus_per_task": os.getenv("SLURM_CPUS_PER_TASK"),
        },
        "environment": {
            "hostname": platform.node(),
            "cpu_model": cpu_model(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "OMP_NUM_THREADS": os.getenv("OMP_NUM_THREADS"),
            "MKL_NUM_THREADS": os.getenv("MKL_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.getenv("OPENBLAS_NUM_THREADS"),
            "NUMEXPR_NUM_THREADS": os.getenv("NUMEXPR_NUM_THREADS"),
        },
    }

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fn = outdir / f"task{int(os.getenv('SLURM_ARRAY_TASK_ID','-1')):02d}_n{args.n}_tol{args.rtol:.0e}_{args.backend}.json"
    fn.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(fn)

if __name__ == "__main__":
    main()
