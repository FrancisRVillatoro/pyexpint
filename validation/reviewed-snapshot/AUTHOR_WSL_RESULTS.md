# Checks run by the author on his workstation (WSL, conda environment pyx-audit)

Python 3.11.16, NumPy 1.24.3, SciPy 1.10.1, pytest 7.1.2, Intel Core Ultra 9 185H.
Summaries as printed by the scripts; the commits are those of the author's branch
at the time, before the later documentation and record commits.

| Date (local) | Check | Commit | Result |
|---|---|---|---|
| 2026-10-04 20:44 | tools/c2_c4.sh | 830f874823c5 | A 80/80; B 27 passed, 53 failed (must fail); C 275/275; D 195/195; E 72 compared, 0 mismatches, largest error difference / tolerance 1.4e-03; F slopes 4.79-4.90, ratio 15-882. VERDICT C2-C4: OK |
| 2026-10-04 21:10 | tools/rerun_cheap_experiments.py | 15f0db2 | classical 0.0e+00; stiff 1.6e-04; fusion unfused 7/7, fused 5/7 as archived; KIOPS-type reductions 11.8-44.2 %; Lawson 0.39. VERDICT: OK |
| 2026-10-06 21:30 | tools/c5_clean_install.sh | 6b5f1af | 275 passed against the installed wheel; 4/4 examples; sdist built and installed. VERDICT C5: OK |
| 2026-10-09 | benchmarks/fusion_ablation.py, benchmarks/broadband_allen_cahn.py | f6ef3de1a850 | records in ../records/ (audited environment, single-threaded BLAS) |

The re-run of all checks on the final tree on the author's workstation is pending
(the block that applies pyexpint_final.patch and calls tools/build_submission_package.sh).
