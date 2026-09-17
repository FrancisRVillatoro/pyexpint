# PyEXPINT — pre-release TOMS benchmark candidate

PyEXPINT is an independent, from-scratch modernization of the mathematical
framework of EXPINT for exponential general linear integrators.

**Development version:** `0.8.1.dev0`

## Current status

- complete 47-method historical EXPINT catalogue;
- verified classical/stiff/weak order metadata;
- one generic explicit EGLM execution engine;
- dense, diagonal, sparse and `LinearOperator` operation;
- full-Arnoldi, KIOPS-style, real-Leja and SciPy+KIOPS backends;
- automatic fusion of compatible phi actions;
- fixed-step integration for the historical catalogue;
- generic reference step-doubling adaptivity for one-step methods;
- embedded Krogstad ETD34 adaptive solver with FSAL;
- coupled temporal/matrix-action tolerances;
- calibrated/automatic backend dispatch;
- work, matvec and algorithmic-workspace diagnostics;
- stiff-order/order-reduction, 1-D and 2-D benchmark suites;
- pre-release CPU/HPC benchmark protocol and Picasso Slurm campaign.

## Validation

```text
119 passed
```

The current benchmark candidate also passes source compilation and editable offline installation.

## Key pre-release documents

- `PRERELEASE_TOMS_REPORT.md`
- `TOMS_CLAIMS_MATRIX.md`
- `TOMS_MANUSCRIPT_BLUEPRINT.md`
- `BENCHMARK_PROTOCOL_TOMS.md`
- `RELEASE_CHECKLIST.md`
- `API_STABILITY_PHASE7.md`
- `external/pinned_comparators.json`
- `hpc/README_PICASSO.md`

## Local 2-D benchmark

`benchmarks/prerelease_2d.py` reproduces the development 2-D reaction-diffusion
benchmark.  The stored result is `prerelease_2d.json`.

These timings are diagnostic, not the final paper timing table.  The final paper
uses the controlled protocol in `BENCHMARK_PROTOCOL_TOMS.md` and the Picasso campaign.

## Picasso campaign

From the unpacked repository:

```bash
mkdir -p logs results/picasso
sbatch hpc/picasso_prerelease_array.slurm
```

After completion:

```bash
python3 hpc/aggregate_picasso_results.py
```

## Licensing status

The historical EXPINT package available to this project contains no explicit source
license. PyEXPINT is therefore being developed independently from published mathematical
formulas and documentation while clarification from the original authors/rightsholder is
pending.

This snapshot uses `LicenseRef-Provisional` and should **not** yet be published as a formal
public release.


## Picasso v0.8.2 timing workflow

See `docs/picasso/TOMS_TIMING_PROTOCOL.md`.
