# PyEXPINT — exponential integrators in Python

**Release 1.0.0: software and research materials corresponding to the author-approved TOMS manuscript v6.**

PyEXPINT represents exponential Runge–Kutta, multistep and general linear methods
through a common execution engine with interchangeable matrix-function actions.
The 47-entry historical catalogue is accompanied by coefficient, regression and
cross-implementation evidence. The exact scope of each validation is documented;
the number of tests is not a proof of every order label.

## Install

Python 3.11 or newer, NumPy >= 1.24 and SciPy >= 1.10 are required.

```bash
python -m pip install distribution/pyexpint-1.0.0-py3-none-any.whl
```

Or, from the repository root:

```bash
python -m pip install .
```

This release is not automatically uploaded to PyPI. See `docs/QUICKSTART.md` and
`examples/no_exact_history.py` for use. The latter uses numerical startup, not exact history.

## Start here

- `paper/v6/main.pdf`: author-approved manuscript (not an ACM-accepted or published article).
- `paper/v6/supplement.pdf`: scientific supplementary material.
- `paper/v6/`: LaTeX, data, figures and table/figure generators.
- `src/pyexpint/`, `tests/`, `examples/`, `benchmarks/`, `tools/`: software and checks.
- `validation/reviewed-snapshot/`: original test/build/differential/cross-check logs.
- `records/`: original Allen–Cahn and fusion records.
- `reproducibility/toms/`: three historical Picasso campaigns and their raw repetitions.
- `PUBLICATION.json`, `provenance/` and `RELEASE_MANIFEST.sha256`: content identity and mapping.

## Exact relationship to the reviewed candidate

All 20 installed Python modules and all tests are byte-identical to the reviewed
source tree `9f62cbf6a6455868e358386ccff824507287aeb3`.
That candidate retained development metadata 0.9.0; this public distribution uses
1.0.0 to avoid confusing it with the older public release. Only packaging/version
metadata and explanatory release documents change. The scientific manuscript v6,
its selected data and the experimental records are not rewritten by publication.
See `provenance/release_changes.json` for the exact file-level mapping.

Recorded preparation-environment validation comprises 275 passing tests against
sources and the same 275 against the installed candidate wheel (Python 3.11.15,
NumPy 1.24.3, SciPy 1.10.1, pytest 7.1.2). These are preserved records, not newly
executed tests of every advertised environment. The GitHub workflow separately
covers Python 3.11–3.14; consult its actual run for the release commit.

## Limits and historical evidence

Real-Leja public actions use direct coefficient interpolation; `target_width`
does not activate semigroup substepping in that path. ETD34 has a known estimator
degeneracy for state-independent forcing; step doubling is an alternative.
The default numerical startup does not generically guarantee preservation of
orders six and seven. Recorded work, achieved error and elapsed time have distinct
meanings. Historical timing measurements remain attributed to the implementations
and machines that produced them. No universal backend or external-speed ranking,
or distributed-memory scaling, is claimed.

The legacy `PHASE*_REPORT.md`, `phase*.json`, old release checklists and project
planning documents are historical records, not new release validation claims.

## Reproduce the manuscript without rerunning integrations

From `paper/v6`:

```bash
python figure_sources/make_figures.py reproducibility/t8_data figures
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
pdflatex -interaction=nonstopmode -halt-on-error supplement.tex
```

Matplotlib is required for figure generation; an ACM-compatible LaTeX installation
is required for the PDFs. Table-generator interfaces are described by their own
`--help`. The software's original MATLAB EXPINT inputs are not redistributed;
see `tools/expint_crosscheck/README.md` for their identification and acquisition.

## Citation and archive

GitHub repository: https://github.com/FrancisRVillatoro/pyexpint

The existing Zenodo concept DOI is **10.5281/zenodo.22820009**. The earlier version
DOI **10.5281/zenodo.22820595** belongs to the historical release, not this release.
Use the new version DOI once the GitHub–Zenodo integration has archived tag
`v1.0.0`. No prospective DOI is fabricated in this tree. `CITATION.cff` contains
the software authorship/version metadata.

## License

Code is MIT (`LICENSE`). Original non-software materials are CC BY 4.0
(`CONTENT-LICENSE.md`), subject to the stated third-party exclusions. No new rights
to third-party or publisher-owned material are asserted.
