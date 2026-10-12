# Changelog

All notable changes to PyEXPINT are documented in this file.

## 1.0.0 - 2026-10-12

### Publication of the reviewed candidate

- Publishes the exact executable Python sources and tests of reviewed tree
  `9f62cbf6a6455868e358386ccff824507287aeb3`, with distribution metadata 1.0.0.
- Includes the reviewed corrections to Leja degeneracy handling, work accounting,
  adaptive failure handling, and backend cloning, plus the corresponding tests.
- Documents the ETD34 estimator limitation and numerical-startup order boundary.
- Includes author-approved manuscript v6, its reproducibility materials, original
  Allen–Cahn records, historical paired timings, cross-check and recorded tests.
- New wheel/sdist are packaging rebuilds; archived scientific results and validation
  logs are not relabelled as new numerical executions.

No executable numerical source is modified during this publication step.

## 0.9.0 - 2026-09-17

### Changed

- Promoted the fully audited `0.9.0rc1` release candidate to the final
  PyEXPINT 0.9.0 release.
- Added final citation and Zenodo concept-DOI metadata.
- Confirmed the public GitHub Actions matrix on Python 3.11--3.14 and the
  distribution build/install job.

There are no numerical-method, backend, or public-API changes relative to
`0.9.0rc1`.

## 0.9.0rc1 - 2026-09-17

### Added

- Backend-independent exponential-integrator framework.
- Complete 47-method historical EXPINT catalogue with audited metadata.
- Dense, diagonal, Arnoldi/Krylov, KIOPS-style, real-Leja, SciPy-hybrid,
  rule-based Auto, and calibrated Auto backends.
- Fixed-step, adaptive step-doubling, and embedded ETD34 integration.
- Backend work and workspace instrumentation.
- Reproducible Picasso benchmark workflow.
- Canonical three-replica TOMS timing evidence with raw JSON data and
  cryptographic source provenance.
- Public API compatibility contract for the 0.9 series.

### Changed

- Adopted the MIT License for PyEXPINT software and CC BY 4.0 for original
  non-software repository content.
- Final TOMS backend benchmark uses homogeneous Leja settings for explicit
  Leja and Auto-selected Leja.
- Release-facing documentation separates canonical reproducibility evidence
  from historical development benchmarks.
- Public `__all__` no longer contains duplicate names.

### Fixed

- Full backend statistics are retained in TOMS benchmark JSON records.
- Picasso timing harness explicitly propagates runtime, runner, and analysis
  failure codes.
- Historical development-phase wording was removed from user-facing API
  messages and documentation.
