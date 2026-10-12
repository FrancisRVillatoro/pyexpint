# Release 1.0.0: publication gate

## Completed before GitHub publication

- Reviewed-source manifest and tree identity checked.
- Installed Python sources and tests preserved byte for byte.
- Version metadata changed to 1.0.0, with old 0.9.0 release preserved.
- Approved manuscript v6, original records and validation logs included.
- New wheel/sdist rebuilt and compared with the exact release source.
- Complete repository payload identified by a content manifest.

## Checked by the WSL publisher before a public release

- Correct GitHub account/repository, unchanged public base, no forced updates.
- Exact staged repository tree matches the supplied publication plan.
- Final GitHub commit's configured CI succeeds.
- Tag resolves to that exact commit.
- Draft-release assets are downloaded and their hashes checked before publication.

## Checked after the GitHub release

- Zenodo creates the new version under concept DOI 10.5281/zenodo.22820009.
- The archived repository payload matches the release manifest.
- The actual version DOI is recorded in the publication result.

A pending GitHub/Zenodo step is not pre-labelled PASS. The older release
checklist is preserved as historical documentation, not as evidence for 1.0.0.
