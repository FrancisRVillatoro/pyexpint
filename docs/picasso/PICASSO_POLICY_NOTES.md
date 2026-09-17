# Picasso policy choices used by PyEXPINT

1. **HOME is persistent**: source, scripts and consolidated/final results live there.
2. **FSCRATCH is execution space**: jobs are staged and executed there.
3. **No benchmark on login nodes**: login is for staging, submission and short checks.
4. **One CPU thread per timing task**: OpenMP/MKL/OpenBLAS/NumExpr are set to 1.
5. **Homogeneous CPU campaign**: default benchmark constraint is `intel`.
6. **Array jobs**: 24 cases, throttled to 8 concurrent tasks by default.
7. **No automatic FSCRATCH deletion**: collection and cleanup are separate commands.
8. **Raw result files are archived** before persistent storage to reduce inode use.
9. **No full Conda environment in HOME** during development; use the central Anaconda module.
10. **Future production uses one SIF** staged to FSCRATCH.
11. **LOCALSCRATCH is not needed for the current benchmark** because each task writes
    only one JSON plus stdout/stderr. It will be introduced only if a future workflow
    produces heavy temporary I/O or many files.


## Benchmark roles (v0.8.2)

- `03_submit_smoke.sh`: one-case pipeline smoke test.
- `03_submit_pilot_array.sh`: 24-case concurrent validation/pilot; not final timing evidence.
- `03_submit_toms_timing.sh`: recommended publication timing protocol; one job/core/node,
  12 balanced sequential blocks, 24 result JSON files.
