# PyEXPINT TOMS benchmark evidence

This directory contains the canonical release-facing evidence for the
PyEXPINT backend timing experiment.

## Scope

The timing experiment demonstrates the reproducible benchmarking
infrastructure supplied with PyEXPINT.  Wall-clock timings are local to the
machine, node, software stack, and system load.  They are not intended as a
universal ranking of matrix-function backends.

Algorithmic quantities such as errors, accepted/rejected steps, nonlinear
evaluations, matrix-vector products, and backend work statistics are the
portable part of the benchmark record.

## Final homogeneous campaigns

Three independent replicas were retained:

| Replica | Campaign | Slurm job |
| --- | --- | ---: |
| rep1 | cpu2d_toms_balanced_v082_leja80_20260904a | 2203999 |
| rep2 | cpu2d_toms_balanced_v082_leja80_rep2_20260904b | 2206865 |
| rep3 | cpu2d_toms_balanced_v082_leja80_rep3_20260904c | 2207024 |

All three campaigns contain 24 raw result JSON files and were generated from
the same 132-file source manifest.  The SHA-256 digest of that manifest is

    ffc203e8eca9e2ad160505f3c10b0bc8fa5e2072ee50ce6a6a4e23c47abe7dda

## Contents

`campaigns.json`
: campaign identifiers, Slurm job IDs, source-manifest provenance, raw-data
  counts, and SHA-256 hashes of the retained analysis products.

`paired_speedups_three_replicas.csv`
: concatenation of the per-replica paired timing summaries.  It contains
  54 rows: 3 replicas x 6 problem/tolerance cases x 3 non-baseline backends.

`repN/raw/`
: the 24 raw JSON result files from replica N.

`repN/toms_timing_summary.csv`
: per-configuration timing summary produced by the canonical analyzer.

`repN/toms_paired_speedups.csv`
: paired backend/KIOPS timing ratios for that replica.

`repN/toms_timing_analysis.json`
: machine-readable analysis product.

`repN/source_manifest.sha256`
: exact staged source manifest used by that replica.

## Reproduction code

The canonical implementation is:

- `hpc/picasso/python/toms_timing_balanced.py`
- `hpc/picasso/python/analyze_toms_timing.py`
- `hpc/picasso/python/check_runtime.py`
- `hpc/picasso/python/make_source_manifest.py`
- `hpc/picasso/slurm/toms_timing_single.slurm`
- `hpc/picasso/scripts/02_stage_campaign.sh`
- `hpc/picasso/scripts/03_submit_toms_timing.sh`
- `hpc/picasso/scripts/04_status_campaign.sh`
- `hpc/picasso/scripts/05_collect_campaign.sh`

The protocol is documented in `BENCHMARK_PROTOCOL_TOMS.md`.

## Historical results

The root-level `phase*.json`, `prerelease*.json`, `PHASE*_REPORT.md`, and
scripts under `benchmarks/` document development and validation history.
They are intentionally retained for provenance, but they are not the
canonical final timing evidence.
