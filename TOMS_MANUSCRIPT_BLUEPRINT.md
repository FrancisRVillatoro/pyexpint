# PyEXPINT TOMS manuscript blueprint

## Working title

**PyEXPINT: A Verified Backend-Independent Framework for Exponential General Linear Integrators**

## Central thesis

The paper is not a Python port of EXPINT.  It presents a verified mathematical method
registry and a backend-independent execution architecture that decouples exponential
integrators from matrix-function-vector algorithms, while preserving and auditing the
historical EXPINT catalogue.

## Proposed paper structure

1. **Introduction**
   - EXPINT 2007 and why the original abstraction remains valuable;
   - evolution from materialized phi matrices to matrix-free phi actions;
   - gap: modern software usually couples a smaller method family to one/few action engines;
   - contributions.

2. **Mathematical framework**
   - semilinear problem;
   - exponential GLM representation;
   - method metadata and classical/stiff/weak order;
   - phi-action algebra and fusion.

3. **Software architecture**
   - `MethodSpec`;
   - external state and startup;
   - backend protocol;
   - dense/diagonal/sparse/LinearOperator semantics;
   - fixed and adaptive interfaces.

4. **Verified historical catalogue**
   - 47/47 EXPINT methods;
   - automatic order/consistency tests;
   - corrected historical inconsistencies;
   - clean provenance policy.

5. **Matrix-function backends**
   - full Arnoldi reference;
   - KIOPS-style augmented action;
   - real Leja interpolation;
   - SciPy hybrid;
   - fusion of multiple phi actions;
   - selector/calibration philosophy.

6. **Adaptive integration**
   - reference step doubling;
   - embedded Krogstad ETD34;
   - matrix-action tolerance coupling;
   - backend failure as step rejection;
   - cost-aware controller and its limitations.

7. **Numerical experiments**
   - historical order reproduction;
   - Hochbruck--Ostermann stiff-order experiments;
   - phi-kernel benchmarks;
   - 1-D work/precision/workspace;
   - 2-D controlled CPU results;
   - external pinned comparisons;
   - optional HPC scaling.

8. **Discussion**
   - when Leja/Krylov/hybrid engines win;
   - why matvec count is insufficient;
   - limits of automatic selection;
   - variable-step multistep EGLM and distributed low-sync Arnoldi as future work.

9. **Conclusions**

## Core figures

1. Architecture diagram: `MethodSpec -> EGLM engine -> action backend`.
2. Historical verification/order-reduction figure.
3. Phi-engine crossover map in dimension/spectral-width space.
4. Work-precision curves for ETD34 KIOPS/Leja/hybrid/Auto.
5. 2-D CPU scaling/crossover plot.
6. Embedded ETD34 vs step-doubling work-precision.

## Core tables

1. Representative method families and verified orders (full 47-method table in supplement/data).
2. Backend capabilities and asymptotic workspace.
3. Historical inconsistencies found and canonical corrections.
4. Controlled benchmark environment and external comparator commits.

## Supplement / reproducibility repository

- full 47-method registry;
- all order-condition checks;
- raw benchmark JSON;
- benchmark-generation scripts;
- Picasso Slurm files;
- external comparator manifests;
- environment metadata;
- figures generated only from committed raw data.
