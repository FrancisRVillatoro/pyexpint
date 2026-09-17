#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.sparse import diags, eye, kron

from pyexpint import (
    AutoBackend,
    ETD34Options,
    KiopsBackend,
    LejaBackend,
    ScipyKiopsBackend,
    SemilinearProblem,
    solve_etd34,
)

BACKENDS = ("kiops", "leja", "hybrid", "auto")
DEFAULT_N_SIDES = (64, 128, 256)
DEFAULT_RTOLS = (1e-5, 1e-7)
PROTOCOL_ID = "balanced-cyclic-6case-4backend-v1"


def safe_cmd(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"UNAVAILABLE: {type(exc).__name__}: {exc}"


def cpu_model():
    for line in safe_cmd(["lscpu"]).splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def cpu_affinity():
    try:
        return sorted(os.sched_getaffinity(0))
    except Exception:
        return []


def json_safe(value):
    """Convert backend statistics to strict JSON-compatible objects.

    Unknown object types are rejected rather than silently stringified so
    benchmark output cannot lose scientific information unnoticed.
    """
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    raise TypeError(
        f"backend statistic is not JSON serializable: "
        f"{type(value).__name__}: {value!r}"
    )


def make_problem(n, T=0.5, nu=0.02):
    Lx = 2 * np.pi
    dx = Lx / n
    x = dx * np.arange(n)
    X, Y = np.meshgrid(x, x, indexing="ij")
    D = diags(
        [np.ones(n - 1), -2 * np.ones(n), np.ones(n - 1)],
        [-1, 0, 1],
        shape=(n, n),
        format="lil",
    )
    D[0, n - 1] = 1.0
    D[n - 1, 0] = 1.0
    D = D.tocsr() / dx**2
    I = eye(n, format="csr")
    A = nu * (kron(I, D, format="csr") + kron(D, I, format="csr"))

    def exact(t):
        return (0.2 * np.exp(-t) * np.sin(X) * np.sin(Y)).reshape(-1)

    def nonlinear(t, u):
        ue = exact(t)
        return u * u + (-ue - A @ ue - ue * ue)

    bounds = (-8 * nu / dx**2, 0.0)
    problem = SemilinearProblem(
        A, nonlinear, exact(0.0), (0.0, T), exact_solution=exact
    )
    return problem, bounds, exact(T)


def make_backend(name, tol, bounds):
    if name == "kiops":
        return KiopsBackend(tol=tol, m_init=10, m_min=6, m_max=64)
    if name == "leja":
        return LejaBackend(
            tol=tol, spectral_bounds=bounds, max_degree=80, target_width=10.0
        )
    if name == "hybrid":
        return ScipyKiopsBackend(tol=tol)
    if name == "auto":
        return AutoBackend(
            tol=tol,
            leja_min_size=512,
            leja_width_threshold=200.0,
            leja_target_width=10.0,
        )
    raise ValueError(name)


def solve_once(problem, exact, bounds, backend_name, rtol):
    atol = rtol * 1e-3
    action_tol = max(1e-13, min(1e-5, 0.01 * rtol))
    opts = ETD34Options(
        rtol=rtol, atol=atol, h0=0.1, h_max=0.2, action_rtol_fraction=0.01
    )
    backend = make_backend(backend_name, action_tol, bounds)
    gc.collect()
    try:
        loadavg_before = list(os.getloadavg())
    except Exception:
        loadavg_before = []
    cpu0 = time.process_time_ns()
    t0 = time.perf_counter_ns()
    sol = solve_etd34(problem, backend, options=opts)
    elapsed_s = (time.perf_counter_ns() - t0) * 1e-9
    cpu_s = (time.process_time_ns() - cpu0) * 1e-9
    stats = json_safe(sol.stats["backend_stats"])
    return {
        "wall_s": float(elapsed_s),
        "cpu_time_s": float(cpu_s),
        "loadavg_before": loadavg_before,
        "error_inf": float(np.max(np.abs(sol.y[-1] - exact))),
        "matvecs": int(stats.get("matvecs", 0)),
        "nonlinear_evals": int(sol.stats["nonlinear_evals_estimate"]),
        "accepted_steps": int(sol.stats["accepted_steps"]),
        "rejected_steps": int(sol.stats["rejected_steps"]),
        "last_selected": stats.get("last_selected"),
        "selection_counts": stats.get("selection_counts"),
        "backend_stats": stats,
    }


def med_iqr(xs):
    a = np.asarray(xs, dtype=float)
    q1, med, q3 = np.quantile(a, [0.25, 0.5, 0.75])
    return float(med), float(q1), float(q3)


def rotate(seq, k):
    k %= len(seq)
    return tuple(seq[k:] + seq[:k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--metadata-dir", required=True)
    ap.add_argument("--blocks", type=int, default=12)
    ap.add_argument("--n-sides", nargs="+", type=int, default=list(DEFAULT_N_SIDES))
    ap.add_argument("--rtols", nargs="+", type=float, default=list(DEFAULT_RTOLS))
    args = ap.parse_args()

    if args.blocks < 1:
        raise SystemExit("--blocks must be >=1")

    outdir = Path(args.outdir)
    metadir = Path(args.metadata_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    metadir.mkdir(parents=True, exist_ok=True)

    cases = [(n, rtol) for n in args.n_sides for rtol in args.rtols]
    if len(cases) != 6 and args.blocks == 12:
        # Custom small test runs are allowed; only the publication default is 6 cases.
        pass

    env = {
        "hostname": platform.node(),
        "cpu_model": cpu_model(),
        "cpu_affinity": cpu_affinity(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "OMP_NUM_THREADS": os.getenv("OMP_NUM_THREADS"),
        "MKL_NUM_THREADS": os.getenv("MKL_NUM_THREADS"),
        "OPENBLAS_NUM_THREADS": os.getenv("OPENBLAS_NUM_THREADS"),
        "NUMEXPR_NUM_THREADS": os.getenv("NUMEXPR_NUM_THREADS"),
    }
    slurm = {
        "job_id": os.getenv("SLURM_JOB_ID"),
        "job_nodelist": os.getenv("SLURM_JOB_NODELIST"),
        "job_partition": os.getenv("SLURM_JOB_PARTITION"),
        "cpus_per_task": os.getenv("SLURM_CPUS_PER_TASK"),
    }

    # Build each problem exactly once; setup is intentionally outside timings.
    cache = {}
    for n, rtol in cases:
        key = (n, rtol)
        problem, bounds, exact = make_problem(n)
        cache[key] = (problem, bounds, exact)

    # One untimed warm-up per configuration.
    warmups = []
    for n, rtol in cases:
        problem, bounds, exact = cache[(n, rtol)]
        for backend in BACKENDS:
            result = solve_once(problem, exact, bounds, backend, rtol)
            warmups.append({"n_side": n, "rtol": rtol, "backend": backend,
                            "error_inf": result["error_inf"]})

    records = {(n, rtol, b): [] for n, rtol in cases for b in BACKENDS}
    schedule = []

    # Cyclic balance: for the default 6 cases / 4 backends and 12 blocks,
    # every case occupies each case position twice and every backend occupies
    # each backend position three times.
    for block in range(args.blocks):
        case_order = rotate(list(cases), block)
        backend_order = rotate(list(BACKENDS), block)
        schedule.append({
            "block": block,
            "case_order": [{"n_side": n, "rtol": r} for n, r in case_order],
            "backend_order": list(backend_order),
        })
        for case_pos, (n, rtol) in enumerate(case_order):
            problem, bounds, exact = cache[(n, rtol)]
            for backend_pos, backend in enumerate(backend_order):
                result = solve_once(problem, exact, bounds, backend, rtol)
                result.update({
                    "block": block,
                    "case_position": case_pos,
                    "backend_position": backend_pos,
                })
                records[(n, rtol, backend)].append(result)

    common = {
        "schema_version": 3,
        "campaign_id": os.getenv("PYEXPINT_CAMPAIGN_ID"),
        "source_manifest_sha256": os.getenv("PYEXPINT_SOURCE_MANIFEST_SHA256"),
        "runtime_mode": os.getenv("PYEXPINT_RUNTIME", "source"),
        "protocol_id": PROTOCOL_ID,
        "blocks": args.blocks,
        "warmups_per_configuration": 1,
        "measurement_scope": "solve_etd34 only; problem construction and gc.collect outside timer",
        "slurm": slurm,
        "environment": env,
    }

    for (n, rtol, backend), runs in records.items():
        walls = [x["wall_s"] for x in runs]
        errs = [x["error_inf"] for x in runs]
        cpus = [x["cpu_time_s"] for x in runs]
        mvs = [x["matvecs"] for x in runs]
        nevals = [x["nonlinear_evals"] for x in runs]
        accepted = [x["accepted_steps"] for x in runs]
        rejected = [x["rejected_steps"] for x in runs]
        med, q1, q3 = med_iqr(walls)
        selected = [x["last_selected"] for x in runs]
        payload = dict(common)
        payload.update({
            "n_side": n,
            "dimension": n * n,
            "rtol": rtol,
            "backend": backend,
            "repeats": len(runs),
            "wall_runs_s": walls,
            "wall_median_s": med,
            "wall_q1_s": q1,
            "wall_q3_s": q3,
            "wall_iqr_s": q3 - q1,
            "cpu_time_median_s": float(np.median(cpus)),
            "error_inf_median": float(np.median(errs)),
            "matvecs_median": float(np.median(mvs)),
            "nonlinear_evals_median": float(np.median(nevals)),
            "accepted_steps_median": float(np.median(accepted)),
            "rejected_steps_median": float(np.median(rejected)),
            "block_ids": [x["block"] for x in runs],
            "case_positions": [x["case_position"] for x in runs],
            "backend_positions": [x["backend_position"] for x in runs],
            "last_selected_runs": selected,
            "runs": runs,
        })
        fn = outdir / f"case_n{n}_tol{rtol:.0e}_{backend}.json"
        fn.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    protocol = dict(common)
    protocol.update({
        "cases": [{"n_side": n, "dimension": n*n, "rtol": r} for n, r in cases],
        "backends": list(BACKENDS),
        "schedule": schedule,
        "warmup_results": warmups,
        "expected_result_files": len(records),
    })
    pfile = metadir / "toms_timing_protocol.json"
    pfile.write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    print(f"TOMS_TIMING_PROTOCOL={PROTOCOL_ID}")
    print(f"BLOCKS={args.blocks}")
    print(f"RESULT_FILES={len(records)}")
    print(f"PROTOCOL_FILE={pfile}")
    print("TOMS_TIMING_FINISHED=1")


if __name__ == "__main__":
    main()
