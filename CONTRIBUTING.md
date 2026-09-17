# Contributing to PyEXPINT

Contributions should preserve numerical correctness, reproducibility, and the
public API compatibility policy documented in `API_STABILITY.md`.

## Development setup

PyEXPINT requires Python 3.11 or newer with NumPy and SciPy.

Install the package and test dependencies in a suitable environment and run:

    python -m pytest

before submitting changes.

## Numerical changes

Changes to integrators, method coefficients, matrix-function backends, adaptive
controllers, or work metrics should include regression tests.

Method metadata must distinguish classical order, stiff order, and
weak/conditional stiff order when relevant.

## Public API

Stable names listed in `API_STABILITY.md` should not be removed or changed
incompatibly without a deprecation cycle.

## Benchmarks

Wall-clock performance is hardware-dependent. Benchmark contributions should
retain raw measurements, environment metadata, algorithmic work metrics, and
the exact code version used.

## Third-party code

Do not copy or vendor external comparator source into PyEXPINT without an
explicit licensing review.

External software used for comparison should be kept separate and pinned by
version or commit.
