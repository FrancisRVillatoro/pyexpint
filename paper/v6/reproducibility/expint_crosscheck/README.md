# Cross-check against the original EXPINT (2005)

The original MATLAB package is not redistributed.  Place its `common/` and
`schemes/` folders under a directory `EXPINT_DIR` and run, with Octave 8 or
MATLAB and with the PyEXPINT sources of this repository:

    EXPINT_DIR=/path/to/expint CROSSCHECK_OUT=results octave-cli crosscheck_expint.m
    python compare_with_pyexpint.py results

`crosscheck_expint.m` runs every scheme of the package, plus one-line corrections
of `etd2rk.m`, `etd2cf3.m`, `etd5rkf.m` and `ablawson2.m`, on a scalar problem
with exact startup and on a dense 2 x 2 problem with numerical startup, and
records observed orders of the original and corrected schemes.
`compare_with_pyexpint.py` runs the same problems with PyEXPINT and classifies
every method: agreement to 1e-12, documented one-line correction, or regenerated
coefficients (ModGenLawson45).  `results_2026-10-07/` holds the outputs obtained
with Octave 8.4 and the 2005 package (file revisions of 2005/05/11).
