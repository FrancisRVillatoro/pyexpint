# v0.8.2.dev0 validation

Before packaging the clean Picasso development bundle:

- Python source compilation: passed.
- Bash syntax validation for Picasso scripts and Slurm files: passed.
- PyEXPINT unit/regression suite: **121 passed**.
- Balanced timing runner microtest: passed.
- Timing analyzer microtest: passed; paired block ratios generated.
- Package minimums: Python >=3.11, NumPy >=1.24, SciPy >=1.10.

The production Picasso stack already validated in the prior smoke campaign is
Python 3.11.4 / NumPy 1.24.3 / SciPy 1.10.1.
