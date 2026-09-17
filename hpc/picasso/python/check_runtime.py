#!/usr/bin/env python3
from __future__ import annotations

"""Canonical Picasso runtime check for PyEXPINT.

This helper is called by login validation, staging, and Slurm compute jobs so
all three use exactly the same version rules and smoke tests.
"""

import argparse
import os
import re
import sys
from pathlib import Path


def version_tuple(text: str, n: int = 3) -> tuple[int, ...]:
    nums = [int(x) for x in re.findall(r"\d+", str(text))[:n]]
    return tuple(nums + [0] * (n - len(nums)))


def require_version(label: str, found: str, minimum: str) -> None:
    if version_tuple(found) < version_tuple(minimum):
        raise SystemExit(f"ERROR: {label} >={minimum} required; found {found}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="Path to source directory containing pyexpint package")
    ap.add_argument("--smoke", action="store_true", help="Run GMRES and expm_multiply smoke tests")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    min_python = os.getenv("PYEXPINT_MIN_PYTHON", "3.11")
    min_numpy = os.getenv("PYEXPINT_MIN_NUMPY", "1.24")
    min_scipy = os.getenv("PYEXPINT_MIN_SCIPY", "1.10")

    require_version("Python", sys.version.split()[0], min_python)

    try:
        import numpy as np
        import scipy
    except Exception as exc:
        raise SystemExit(f"ERROR: NumPy/SciPy import failed: {type(exc).__name__}: {exc}") from exc

    require_version("NumPy", np.__version__, min_numpy)
    require_version("SciPy", scipy.__version__, min_scipy)

    if args.source:
        source = str(Path(args.source).resolve())
        if source not in sys.path:
            sys.path.insert(0, source)

    try:
        import pyexpint
    except Exception as exc:
        raise SystemExit(f"ERROR: PyEXPINT import failed: {type(exc).__name__}: {exc}") from exc

    if args.smoke:
        from scipy.sparse import eye
        from pyexpint.backends._scipy_compat import gmres_compat

        x, info = gmres_compat(
            eye(4, format="csr"),
            np.ones(4),
            rtol=1e-10,
            atol=0.0,
            restart=4,
        )
        if info != 0 or not np.all(np.isfinite(x)):
            raise SystemExit(f"ERROR: GMRES compatibility smoke failed: info={info}")

        from pyexpint import ScipyKiopsBackend

        ctx = ScipyKiopsBackend(tol=1e-10).bind(-eye(4, format="csr"), 0.1)
        y = ctx.phi_action(0, 1.0, np.ones(4))
        if not np.all(np.isfinite(y)):
            raise SystemExit("ERROR: scipy expm_multiply smoke failed")

    if not args.quiet:
        print(f"python {sys.version.split()[0]}")
        print(f"numpy {np.__version__}")
        print(f"scipy {scipy.__version__}")
        print(f"pyexpint import OK {getattr(pyexpint, '__file__', 'unknown')}")
        if args.smoke:
            print("SciPy compatibility smoke OK")
        print(
            "runtime requirements OK "
            f"(Python>={min_python}, NumPy>={min_numpy}, SciPy>={min_scipy})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
