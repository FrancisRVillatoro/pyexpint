# Candidate claims for the PyEXPINT TOMS manuscript

| ID | Candidate claim | Current evidence | Status for manuscript |
|---|---|---|---|
| C1 | PyEXPINT represents all 47 historical EXPINT schemes in one verified `MethodSpec`/EGLM framework. | 47/47 mapping, order-condition tests, 119-test suite. | **Strong / ready** |
| C2 | The same method definitions execute with dense, diagonal, sparse and matrix-free operators. | Full catalogue exercised with multiple backends. | **Strong / ready** |
| C3 | The framework exposes/fuses phi-action combinations and can reduce matrix-vector work. | Phase-3 fused/unfused benchmarks, up to ~37% matvec reduction in tested cases. | **Strong but benchmark-dependent** |
| C4 | Embedded ETD34 is substantially cheaper than generic step doubling for adaptive Krogstad. | 36--58% fewer matvecs and large nonlinear-evaluation reductions in Phase 7. | **Strong; needs final hardware timings** |
| C5 | No single phi engine is universally optimal; backend crossovers depend on size/spectrum/cost model. | 1-D and 2-D KIOPS/Leja/hybrid crossover data. | **Strong qualitative claim** |
| C6 | Auto selection can track the favorable backend on calibrated problem classes. | Calibration + 2-D development benchmark. | **Moderate; do not claim universal optimality** |
| C7 | Cost-aware time-step control reduces total computational cost. | Reduces matvec proxy 8--21%, but serial wall time can worsen. | **Do not claim as wall-time improvement**; present as diagnostic / future refinement |
| C8 | PyEXPINT outperforms `rkstiff`, LeXInt or official KIOPS. | No pinned runtime comparison executed yet. | **Not allowed yet** |
| C9 | PyEXPINT scales efficiently on distributed memory. | No MPI/low-sync implementation benchmark. | **Not allowed** |
| C10 | PyEXPINT finds and corrects inconsistencies in the historical EXPINT implementation/specification. | ETD2RK, ETD2CF3, ETD5RKF executable bugs plus metadata inconsistencies. | **Strong historical/verification contribution** |

## Recommended headline

The strongest defensible headline is not raw speed. It is:

> A verified backend-independent exponential-general-linear-method framework in which the same integrator catalogue can be coupled to multiple matrix-function engines, with automatic algebraic fusion, modern adaptivity, and reproducible backend-selection diagnostics.
