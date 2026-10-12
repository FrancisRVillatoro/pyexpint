# PyEXPINT 1.0.0 — software and materials for manuscript v6

This is the single public release of the reviewed candidate and the corresponding
author-approved manuscript v6 and supplement. It is not a claim of ACM acceptance.

## Contents

- Complete software, 47-entry method catalogue, tests, examples and drivers.
- Reviewed Leja, work-accounting, adaptive-error-handling and cloning corrections.
- Manuscript and supplement PDFs, editable sources, data and figure/table generators.
- Original Allen–Cahn records, historical Picasso timings, cross-check and validation logs.
- Installable wheel, source distribution, full repository archive and SHA-256 sums.

## Identity and validation scope

The executable Python sources and tests are byte-identical to reviewed tree
`9f62cbf6a6455868e358386ccff824507287aeb3`. The private candidate retained development
metadata 0.9.0; public metadata is now 1.0.0. Earlier public v0.9.0 and its tag are
unchanged. The manuscript files are preserved exactly as approved v6.

The supplied logs document 275 passing tests from sources and the same 275 from
the installed reviewed wheel in Python 3.11.15. GitHub CI for the final release
commit is checked separately before this release is published. No new scientific
benchmark is run for this packaging step. Historical times retain their original
implementation/environment attribution.

Code: MIT. Original non-software content: CC BY 4.0, subject to third-party exclusions.
The original EXPINT MATLAB sources are not redistributed.

Zenodo concept DOI: 10.5281/zenodo.22820009. The new version DOI must be obtained
from the archived v1.0.0 record; 10.5281/zenodo.22820595 is the old v0.9.0 DOI.
All paper materials and both distributions are inside the repository snapshot,
not only attached as separate GitHub-release assets.
