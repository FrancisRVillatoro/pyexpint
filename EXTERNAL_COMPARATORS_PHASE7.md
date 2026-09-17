# External comparators — Phase 7

## `rkstiff` / ETD34

A current public implementation maintained by Patrick Whalen is available at
`whalenpt/rkstiff`.  The repository is MIT licensed and advertises ETD34 as an
adaptive fourth-order exponential time-differencing method with third-order
embedding based on Krogstad.

The current `rkstiff/etd34.py` implementation was inspected only as an external
reference. PyEXPINT does **not** vendor or import its source.

The source confirms the mathematical structure used independently in PyEXPINT:

- Krogstad stages 2--4;
- the Krogstad fourth-order candidate as stage 5;
- one additional nonlinear evaluation at that candidate;
- embedded error proportional to the Krogstad fourth weight multiplying
  `N(stage4)-N(stage5)`;
- FSAL reuse of the fifth nonlinear evaluation after an accepted step.

An optional runtime harness is provided:

```bash
python -m pip install rkstiff
PYTHONPATH=src python benchmarks/external_rkstiff_phase7.py
```

The external package is not installed in the present execution container and
network package installation is unavailable, so **no runtime speed/accuracy claim
against `rkstiff` is made in Phase 7**.

## Deka--Einkemmer cost-aware controller

PyEXPINT implements the published log-cost-gradient idea independently.
For accepted steps, computational cost per unit simulated time is estimated as

\[
c_n = \frac{i_n}{h_n},
\]

where \(i_n\) is either a matrix-vector-product proxy or measured wall time.
A finite difference in \((\log h,\log c)\) estimates the gradient and provides
a cost-minimizing proposal.  The next step is the minimum of the accuracy
proposal and the cost proposal.

The non-penalized parameter set reported with the published implementation is
used as the Phase-7 default. No third-party controller code is distributed.

## LeXInt / KIOPS

Phase 7 does not add new claims against LeXInt or the official MATLAB KIOPS
implementation. The Phase-5/6 provenance documents remain authoritative.

The final TOMS benchmark should run external software from pinned releases or
commits in isolated environments and record:

- exact version/commit;
- license;
- hardware/software environment;
- tolerances;
- matrix-vector counts;
- nonlinear evaluations;
- memory/workspace estimates;
- wall time.
