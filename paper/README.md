# Approved manuscript v6 and its evidence

`v6/main.pdf` and `v6/supplement.pdf` are the approved author manuscripts, not
publisher versions. Their bytes, scientific text, figures and selected data are
preserved from `PyEXPINT_T10_manuscript_v6.zip`.

The text was prepared against a privately delivered, content-identified candidate
which retained package metadata 0.9.0. Release 1.0.0 publishes the same executable
Python sources under an unambiguous new distribution version. `../PUBLICATION.json`
records the relationship; the manuscript's original historical identifiers and
statements about what was private at review time are not silently rewritten.
The old public 0.9.0 DOI remains an explicitly historical citation.

Companion-path translation from the manuscript and its original companion index:

| Review-package path | Public repository path |
| --- | --- |
| `software/src/pyexpint` | `src/pyexpint` |
| `software/tests`, `software/tools`, `software/examples` | `tests`, `tools`, `examples` |
| `software/reproducibility/toms` | `reproducibility/toms` |
| `evidence/` | `validation/reviewed-snapshot/` |
| `records/` | `records/` |
| old private wheel/sdist | `validation/reviewed-snapshot/c5_20261011_090904/` |
| public 1.0.0 wheel/sdist | `distribution/` |

The alternative v5 manuscript nested in the original private package is NOT
published as the current paper. Internal revision notes and provisional duplicates
are excluded; the exact inclusion/exclusion map is in `../provenance/release_changes.json`.
No new numerical result is created by this repackaging.
