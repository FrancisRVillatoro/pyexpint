# PyEXPINT Phase 7 — embedded adaptivity and cost-aware control

## Executive result

Phase 7 reaches **119/119 automated tests** and upgrades the adaptive layer from
a generic Richardson/step-doubling reference implementation to a published
embedded exponential Runge--Kutta pair.

The main result is positive but nuanced:

- **ETD34 embedded adaptivity is a clear success.**
- **A cost-aware controller based only on matvec count is not yet a universal
  wall-time optimizer.**
- Backend non-convergence is now handled as an adaptive rejection rather than a
  fatal solver error.
- A current independent external comparator (`rkstiff` ETD34, MIT) is identified
  and a runtime harness is supplied, but was not executable in this offline
  container.

## 1. ETD34: Krogstad 4 with third-order embedding

The high-order candidate is exactly Krogstad's ETDRK4-B.  After the usual four
Krogstad nonlinear stage values, the fourth-order candidate \(Y_5\) is formed.
One additional nonlinear evaluation gives \(N_5=N(Y_5)\), and the embedded
error estimator is

\[
e_n=h[-arphi_2(hL)+4arphi_3(hL)]\,[N_4-N_5].
\]

The high-order solution is accepted.  After acceptance, \(N_5\) is reused as
the first nonlinear value of the next step (FSAL).  After rejection, the old
\(N(y_n)\) is reused for the retry.

A one-step audit confirms that the high candidate agrees with the existing
PyEXPINT Krogstad `MethodSpec` to roundoff.  The estimator scales as \(h^4\), as
required for a 4(3) embedded pair.

## 2. Embedded vs step doubling

Periodic manufactured reaction-diffusion, \(N=256\).

[
  {
    "backend": "kiops",
    "rtol": 0.0001,
    "wall_speedup": 4.7267462963618705,
    "matvec_reduction_fraction": 0.5430916552667578,
    "nonlinear_eval_reduction_fraction": 0.6388888888888888,
    "error_ratio_embedded_over_doubling": 11.427525677088912
  },
  {
    "backend": "kiops",
    "rtol": 1e-06,
    "wall_speedup": 7.582318677951845,
    "matvec_reduction_fraction": 0.39714525608732154,
    "nonlinear_eval_reduction_fraction": 0.3125,
    "error_ratio_embedded_over_doubling": 1.2682996420849317
  },
  {
    "backend": "leja",
    "rtol": 0.0001,
    "wall_speedup": 3.938428410712961,
    "matvec_reduction_fraction": 0.5767928593413358,
    "nonlinear_eval_reduction_fraction": 0.6388888888888888,
    "error_ratio_embedded_over_doubling": 0.4341702895826699
  },
  {
    "backend": "leja",
    "rtol": 1e-06,
    "wall_speedup": 1.5740962490356345,
    "matvec_reduction_fraction": 0.36012622981251163,
    "nonlinear_eval_reduction_fraction": 0.3125,
    "error_ratio_embedded_over_doubling": 1.2407521238617913
  }
]

The most relevant raw cases are:

### KIOPS, rtol = 1e-4

- step doubling: 731 matvecs, 36 nonlinear evaluations;
- embedded ETD34: 334 matvecs, 13 nonlinear evaluations;
- final errors: \(2.0	imes10^{-7}\) and \(2.3	imes10^{-6}\), both comfortably
  below the requested tolerance scale.

### KIOPS, rtol = 1e-6

- step doubling: 1191 matvecs, 48 nonlinear evaluations;
- embedded ETD34: 718 matvecs, 33 nonlinear evaluations;
- final errors: \(4.0	imes10^{-8}\) vs \(5.1	imes10^{-8}\).

### Leja, rtol = 1e-4

- step doubling: 3249 matvecs;
- embedded: 1375 matvecs.

### Leja, rtol = 1e-6

- step doubling: 5387 matvecs;
- embedded: 3447 matvecs.

The measured serial wall-time speedups in this container range from about
1.6x to 7.6x. These timings are **development measurements, not final
paper benchmarks**.

## 3. Stiff adaptive problems

The adaptive pair was also run on the two Hochbruck--Ostermann order-reduction
problems.

At rtol=1e-4 the embedded scheme uses 21 nonlinear evaluations versus 60 for
step doubling on both examples.  At rtol=1e-6 the nonlocal example is more
demanding: the embedded estimator takes 22 accepted + 2 rejected steps (97
nonlinear evaluations), whereas step doubling takes 7 accepted steps (84
evaluations).  Nevertheless the embedded solution is substantially more
accurate in that case.

This is evidence that the embedded estimator detects stiff/order-reduction
difficulty rather than blindly reproducing the scalar-controller behavior.

## 4. Cost-aware controller

The Phase-7 controller combines:

1. the traditional accuracy-limited proposal;
2. the Deka--Einkemmer log-cost-gradient proposal.

The next step is the smaller of the two.

Stress problem: periodic manufactured problem, \(N=512, T=2\), KIOPS backend.

[
  {
    "rtol": 0.0001,
    "matvec_reduction_fraction": 0.08007170600537794,
    "wall_ratio_cost_over_accuracy": 1.0973328933706779,
    "error_ratio_cost_over_accuracy": 0.7799290352408259,
    "accepted_steps_accuracy": 4,
    "accepted_steps_cost": 8,
    "cost_limited_steps": 7
  },
  {
    "rtol": 1e-06,
    "matvec_reduction_fraction": 0.21425258927191215,
    "wall_ratio_cost_over_accuracy": 1.0382243410141865,
    "error_ratio_cost_over_accuracy": 0.5968773189124205,
    "accepted_steps_accuracy": 12,
    "accepted_steps_cost": 24,
    "cost_limited_steps": 22
  }
]

At rtol=1e-4, the cost-aware controller reduces matvecs from 3347 to 3079
(~8.0%) but doubles the number of accepted steps from 4 to 8.  At rtol=1e-6,
matvecs decrease from 6469 to 5083 (~21.4%) while accepted steps increase from
12 to 24.

In this serial Python environment the wall time is slightly **worse** despite
the reduced matvec count.

This is not a failure of the cost-aware principle. It demonstrates that
`matvecs` is an incomplete hardware/software cost proxy once Python overhead,
orthogonalization, small dense exponentials, and nonlinear evaluations matter.
The final selector/controller should therefore optimize a calibrated composite
cost or wall time, not a universal matvec count.

## 5. Iterative-backend failure handling

A Leja stress test at strict tolerance exposed an action that reached the
maximum polynomial degree.  Phase 6 would abort the integration.

Phase 7 now treats `LejaConvergenceError`, `KiopsConvergenceError`, and
`KrylovConvergenceError` as rejected time steps: \(h\) is reduced and the
step is retried.  The previously failing Leja test now completes after one
backend-failure rejection.

This behavior matches the standard adaptive strategy for iterative exponential
integrators: a matrix-function failure at an excessively large step should
feed back into the time-step controller.

## 6. External comparator status

A current `rkstiff` package exists and provides ETD34/ETD35.  Its public
repository is MIT licensed.  Its current ETD34 source independently confirms
the Krogstad-high/third-order-embedding structure used here.

`benchmarks/external_rkstiff_phase7.py` is provided as an executable comparison
harness.  It was not executed here because `rkstiff` is not installed and this
container cannot install packages from the network.

Therefore Phase 7 makes **no runtime superiority claim against rkstiff**.

## 7. TOMS decision after Phase 7

The methodological story survives.

A defensible paper contribution is now:

1. verified, machine-readable reproduction of the 47-method EXPINT catalogue;
2. one common EGLM execution abstraction;
3. interchangeable dense/diagonal/Krylov/KIOPS-style/Leja/hybrid backends;
4. automatic fusion of phi actions;
5. embedded ETD34 adaptivity that materially outperforms generic step doubling;
6. explicit separation of temporal error and matrix-action error;
7. calibrated backend selection and cost-aware step selection;
8. evidence that backend/controller choice is a multi-cost optimization problem.

What is **not yet publishable as a strong claim** is universal optimality of the
automatic selector or cost controller.  The Phase-7 stress test explicitly shows
that minimizing matvecs can increase wall time.

## 8. Remaining work before manuscript freeze

The next phase should be a release/benchmark phase rather than another algorithm
expansion:

- run the external `rkstiff` harness in a pinned environment;
- run LeXInt from a pinned MIT commit on common kernels/problems;
- run official KIOPS where MATLAB/Octave licensing/environment allows;
- execute CPU benchmarks on a controlled workstation and HPC benchmarks on Picasso;
- repeat timings with multiple seeds/runs and report medians/IQR;
- add a 2-D large-scale case;
- decide whether a low-synchronization Arnoldi backend is needed for the paper;
- freeze API and documentation;
- then draft the TOMS manuscript.

