# Third-party software and provenance

PyEXPINT does not vendor source code from the external projects listed below.

## Runtime dependencies

### NumPy

PyEXPINT uses NumPy as a normal runtime dependency. NumPy source code is not
vendored into PyEXPINT.

### SciPy

PyEXPINT uses SciPy as a normal runtime dependency, including linear algebra,
sparse linear algebra, and `scipy.sparse.linalg.expm_multiply`.

SciPy is distributed under the BSD 3-Clause license. SciPy source code is not
vendored into PyEXPINT.

## External algorithm/software references

### KIOPS

Reference project:
https://gitlab.com/stephane.gaudreault/kiops

The reference KIOPS implementation is LGPL-2.1.

PyEXPINT's `KiopsBackend` is an independent Python implementation based on the
published mathematical algorithm. The reference MATLAB source is not copied,
translated, vendored, or distributed with PyEXPINT.

### LeXInt

Reference project:
https://github.com/Pranab-JD/LeXInt

LeXInt is MIT licensed.

PyEXPINT's `LejaBackend` independently implements real-Leja point generation,
Newton divided differences, convergence control, and spectral-bound handling.
LeXInt source is not vendored or copied.

### rkstiff

Reference project:
https://github.com/whalenpt/rkstiff

rkstiff is MIT licensed.

Its ETD34 implementation was inspected as an external reference during
validation. No rkstiff source is included in PyEXPINT.

## Historical EXPINT package

PyEXPINT reproduces the mathematical catalogue associated with

H. Berland, B. Skaflestad, and W. M. Wright,
"EXPINT -- A MATLAB package for exponential integrators",
ACM Transactions on Mathematical Software 33(1), 2007.

The historical EXPINT MATLAB distribution available during development did not
contain an explicit software license.

PyEXPINT does not redistribute the historical MATLAB source. Its Python
implementation was developed independently from published mathematical
descriptions and independently derived constructions.

Names of historical source files may be retained in method metadata solely for
scientific provenance and auditability.

## External benchmark snapshots

External comparator repositories are checked out separately at pinned commits.
They are not dependencies of PyEXPINT and are not included in PyEXPINT release
archives.

See:

- `external/pinned_comparators.json`
- `external/GET_EXTERNAL_SNAPSHOTS.md`
- `MODERN_BACKENDS_PROVENANCE.md`
