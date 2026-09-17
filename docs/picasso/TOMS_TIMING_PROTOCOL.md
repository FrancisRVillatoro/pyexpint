# Final TOMS CPU timing protocol on Picasso

## Purpose

The 24-task Slurm array is a **validation/pilot** protocol, not the final source
of publication wall-clock claims, because concurrent tasks can share a physical
node and contend for caches/memory bandwidth.

The final timing protocol uses one Slurm job, one Intel core, and one physical
node for the entire comparison.

## Cases

- `N_side = 64, 128, 256` (`N = 4096, 16384, 65536`)
- `rtol = 1e-5, 1e-7`
- backends: KIOPS, Leja, hybrid SciPy/KIOPS, Auto

There are 24 configurations.

## Balanced design

One untimed warm-up is performed for each configuration. Then 12 measured
blocks are executed. In block `b`:

- the six `(N_side, rtol)` cases are cyclically rotated by `b mod 6`;
- the four backends are cyclically rotated by `b mod 4`.

Across 12 blocks every case occupies each of the six case positions exactly
twice, and every backend occupies each of the four backend positions exactly
three times.

The primary wall-time comparison is paired by block against KIOPS. This controls
for slow drift during the single job better than comparisons across independent
concurrent jobs.

## Resource control

- `constraint=intel` -> Xeon Gold 6230R class nodes
- `nodes=1`, `ntasks=1`, `cpus-per-task=1`
- `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=NUMEXPR_NUM_THREADS=1`
- `srun --cpu-bind=cores`

No whole-node exclusivity is requested: that would reserve 52 cores while using
one and would be an inefficient use of Picasso. The balanced repeated design is
used to quantify residual system noise.

## Interpretation

The pilot array may support correctness, work counts and qualitative crossover
hypotheses. Publication wall-clock claims should use the balanced single-job
campaign and its paired block ratios.
