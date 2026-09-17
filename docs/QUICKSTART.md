# PyEXPINT quickstart

PyEXPINT provides exponential integrators for semilinear initial-value problems

    y'(t) = L y(t) + N(t, y(t)).

## Installation from source

PyEXPINT requires Python 3.11 or newer together with NumPy and SciPy.

From a source checkout:

    python -m pip install .

For development and testing:

    python -m pip install -e ".[test]"

## Minimal example

    import numpy as np

    from pyexpint import DenseBackend, SemilinearProblem, get_method, solve_fixed

    L = np.diag([-1.0, -2.0])

    problem = SemilinearProblem(
        linear_operator=L,
        nonlinear=lambda t, y: np.zeros_like(y),
        y0=np.array([1.0, 1.0]),
        t_span=(0.0, 1.0),
    )

    solution = solve_fixed(
        problem,
        get_method("ETD2RK"),
        h=0.01,
        backend=DenseBackend(),
    )

    print(solution.t[-1])
    print(solution.y[-1])

For this linear example the exact final value is

    [exp(-1), exp(-2)].

## Method catalogue

List available methods with

    import pyexpint
    print(pyexpint.list_methods())

PyEXPINT currently contains the audited 47-method historical EXPINT catalogue.

## Backends

The principal backends are:

- `DenseBackend`
- `DiagonalBackend`
- `KrylovBackend`
- `KiopsBackend`
- `LejaBackend`
- `ScipyKiopsBackend`
- `AutoBackend`
- `CalibratedAutoBackend`

See `API_STABILITY.md` for the public API compatibility contract.

## Adaptive integration

PyEXPINT provides:

- `solve_adaptive` for reference step-doubling adaptivity;
- `solve_etd34` for embedded Krogstad ETD4(3) integration.

## Reproducibility

Canonical release-facing TOMS benchmark evidence is stored under

    reproducibility/toms/

Wall-clock timings are hardware-local observations, not universal backend rankings.
