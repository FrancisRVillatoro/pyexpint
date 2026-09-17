from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]

RUNNER_PATH = (
    ROOT
    / "hpc"
    / "picasso"
    / "python"
    / "toms_timing_balanced.py"
)

SLURM_PATH = (
    ROOT
    / "hpc"
    / "picasso"
    / "slurm"
    / "toms_timing_single.slurm"
)


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "pyexpint_toms_runner_contract_test",
        RUNNER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backend_stats_json_safe_preserves_nested_numeric_data():
    runner = load_runner()

    source = {
        "degree_sum": np.int64(123),
        "max_degree_used": np.int32(27),
        "mean_degree": np.float64(12.5),
        "selection_counts": {
            "leja": np.int64(4),
            "kiops": np.int64(2),
        },
        "selected_backend_stats": {
            "leja": {
                "degrees": np.array([10, 12, 15]),
            }
        },
    }

    out = runner.json_safe(source)

    assert out["degree_sum"] == 123
    assert out["max_degree_used"] == 27
    assert out["mean_degree"] == 12.5
    assert out["selected_backend_stats"]["leja"]["degrees"] == [
        10,
        12,
        15,
    ]

    json.dumps(out)


def test_solve_once_serializes_complete_backend_stats(monkeypatch):
    runner = load_runner()

    backend_stats = {
        "matvecs": np.int64(17),
        "polynomial_steps": np.int64(5),
        "degree_sum": np.int64(91),
        "max_degree_used": np.int64(23),
        "mean_degree": np.float64(18.2),
    }

    class FakeSolution:
        y = [np.array([1.0])]
        stats = {
            "backend_stats": backend_stats,
            "nonlinear_evals_estimate": 4,
            "accepted_steps": 3,
            "rejected_steps": 1,
        }

    monkeypatch.setattr(
        runner,
        "make_backend",
        lambda *args, **kwargs: object(),
    )

    monkeypatch.setattr(
        runner,
        "solve_etd34",
        lambda *args, **kwargs: FakeSolution(),
    )

    result = runner.solve_once(
        problem=object(),
        exact=np.array([1.0]),
        bounds=(-1.0, 0.0),
        backend_name="leja",
        rtol=1.0e-5,
    )

    assert result["matvecs"] == 17
    assert result["backend_stats"]["degree_sum"] == 91
    assert result["backend_stats"]["max_degree_used"] == 23
    assert result["backend_stats"]["mean_degree"] == 18.2

    json.dumps(result)


def test_toms_slurm_uses_explicit_failure_propagation():
    text = SLURM_PATH.read_text()

    assert "set -e" not in text
    assert "set -euo" not in text
    assert "errexit" not in text

    assert "RUNNER_RC=$?" in text
    assert "toms_runner_rc.txt" in text
    assert 'return "$RUNNER_RC"' in text

    assert "ANALYZE_RC=$?" in text
    assert "toms_analyze_rc.txt" in text
    assert 'return "$ANALYZE_RC"' in text

    assert 'main "$@"' in text


def test_toms_explicit_leja_and_auto_use_matching_leja_configuration():
    runner = load_runner()

    bounds = (-100.0, 0.0)
    tol = 1.0e-8

    explicit = runner.make_backend(
        "leja",
        tol,
        bounds,
    )

    auto = runner.make_backend(
        "auto",
        tol,
        bounds,
    )

    assert explicit.options.max_degree == 80
    assert auto.leja.options.max_degree == 80

    assert explicit.options.max_degree == auto.leja.options.max_degree
    assert explicit.options.target_width == auto.leja.options.target_width

    assert explicit.options.target_width == 10.0
    assert auto.leja.options.target_width == 10.0

    assert explicit.options.min_degree == auto.leja.options.min_degree
    assert explicit.options.candidate_count == auto.leja.options.candidate_count
