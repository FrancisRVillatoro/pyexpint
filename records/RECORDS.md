# Original experimental records from the author's workstation

These are the files written by the drivers on the author's WSL workstation and
committed to the repository as reproducibility/paper/*.json; they are byte-identical
to the copies inside software/reproducibility/paper/.

- broadband_allen_cahn.json, written by benchmarks/broadband_allen_cahn.py with five
  repetitions per solve. Inside the file: environment (Python 3.11.16, NumPy 1.24.3,
  SciPy 1.10.1, OMP/OPENBLAS/MKL threads 1, Intel Core Ultra 9 185H, commit
  f6ef3de1a85005d93f8a3e3744514dce65b9f68a), problem parameters, seed 7 and the twelve
  mode coefficients of the initial state, initial and reference states (HochOst4,
  h = 1/4096, KIOPS-type 1e-13, difference to h = 1/2048 of 3.9e-14), and for each of
  the 18 solves the options, action tolerance, error, matrix-vector products,
  nonlinear evaluations, accepted and rejected steps, accepted step sequence, the five
  wall times and their median. SHA-256
  392065a9ac1d8eaa38312850060fc31597f658c7ba21e5529064d89d694a89b4.
- fusion_ablation.json, written by benchmarks/fusion_ablation.py in the same session:
  full-Arnoldi and KIOPS-type counts without and with fusion for seven methods, the
  relative difference of the final states, and the full-Arnoldi counts for three
  other initial states. The driver does not record the environment; the counts are
  identical to those obtained in the preparation environment. SHA-256
  d06e53e342a10133247f9c7c3e7711fd3a08b27ed9717e3634b6eb9690d136c1.
