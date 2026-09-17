# Modern backend provenance

The Phase-5 matrix-function backends are independent implementations.

## KiopsBackend

Algorithmic references:

- S. Gaudreault, G. Rainwater, M. Tokman, *KIOPS: A fast adaptive Krylov
  subspace solver for exponential integrators*, J. Comput. Phys. 372 (2018),
  236–255.
- J. Niesen, W. M. Wright, *Algorithm 919*, ACM TOMS 38(3) (2012), Article 22.

The public reference KIOPS MATLAB implementation is LGPL-2.1. PyEXPINT does not
copy or translate that source. The Python module was written from the mathematical
algorithmic description and uses its own data structures/control flow.

## LejaBackend

Algorithmic/context references:

- P. J. Deka, L. Einkemmer, M. Tokman, *LeXInt: Package for exponential
  integrators employing Leja interpolation*, SoftwareX 21 (2023), 101302.

The LeXInt repository is MIT licensed. Phase-5 PyEXPINT nevertheless implements its
own real-Leja generator, Newton divided-difference evaluator, convergence test, and
spectral-bound handling rather than importing/copying LeXInt code.
