# Picasso pilot validation campaign 2155558

## Status

Campaign: `cpu2d_intel_v081e_20260831a`  
Slurm array parent: `2155558`  
Source-manifest SHA-256:
`d9979af1260faf41c75ee23b74d8ab8c901403a31a7d8676e9cb43216b80d8d4`

The campaign produced 24/24 expected JSON result files. The independent JSON
audit reported `PROBLEMS=0` and `PILOT_JSON_AUDIT_PASS=1`. No non-empty
stderr file and no `Traceback`, `ERROR`, `FAILED`, or `Exception` marker was
found in the Slurm logs. Per-array-task `sacct` queries confirmed `COMPLETED
0:0` for sampled tasks and were archived for all 24 tasks.

## Numerical consistency

For each `(N, rtol)` all four backends produced essentially the same final
error and the same nonlinear-evaluation count. The controller used 13 nonlinear
evaluations at `rtol=1e-5` and 29 at `rtol=1e-7`.

Representative error levels were approximately:

- `1.4--1.5e-7` for `rtol=1e-5`;
- `7.0e-9` for `rtol=1e-7`.

`Auto` matched Leja in matvec count and final error in all six cases, showing
that the current rule selected Leja throughout this problem class on the pilot.

## Work-count observation

Hybrid used fewer matrix-vector products than KIOPS in all six cases, whereas
Leja used substantially more, especially at the largest dimension. Therefore
matvec count alone is not a wall-clock proxy across engines with different
orthogonalization/interpolation costs.

## Why the pilot timings are not publication timings

Slurm placed multiple backend tasks from the same comparison concurrently on
the same physical nodes (`sd017` and `sd059`). This creates possible cache and
memory-bandwidth contention. The pilot wall times are therefore retained for
validation and qualitative crossover diagnosis only.

The final TOMS timing protocol uses one job, one Intel core and 12 balanced
sequential blocks. See `TOMS_TIMING_PROTOCOL.md`.
