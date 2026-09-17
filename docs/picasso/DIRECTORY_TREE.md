# Canonical Picasso directory layout for PyEXPINT

## Persistent tree: HOME

```text
$HOME/pyexpint_toms/
├── README_START_HERE.md
├── incoming/                       # files just transferred from the PC
├── repo/                           # ACTIVE, VERSIONED source tree
│   ├── src/
│   ├── tests/
│   ├── benchmarks/
│   ├── hpc/
│   │   └── picasso/                # canonical Picasso scripts/config
│   ├── docs/
│   │   └── picasso/                # canonical Picasso documentation
│   ├── containers/
│   │   └── defs/                   # versioned Apptainer definitions/templates
│   └── pyproject.toml
├── ops -> repo/hpc/picasso         # stable operational path; symbolic link
├── docs -> repo/docs/picasso       # stable documentation path; symbolic link
├── snapshots/                      # immutable PyEXPINT source/release archives
├── external/
│   └── snapshots/                  # pinned external comparator tarballs
├── containers/
│   ├── defs -> ../repo/containers/defs
│   ├── images/                     # canonical .sif files; NOT in Git
│   └── manifests/                  # SIF hashes/build metadata
├── results/
│   └── campaigns/
│       └── <CAMPAIGN_ID>/
│           ├── README.md
│           ├── COLLECTED_OK
│           ├── MANIFEST.sha256
│           ├── summary/
│           └── artifacts/
│               └── raw_run_bundle.tar.gz
├── manifests/
└── state/                          # tiny operational state/job-id files
```

### Canonical-source rule

`repo/` is the only editable source tree. Picasso Slurm scripts and documentation
are stored **inside the repository** so the exact workflow used for the paper is
also the workflow published on GitHub/Zenodo.

`ops` and `docs` are symbolic links only. Never edit a second copy.

## Ephemeral tree: FSCRATCH

```text
$FSCRATCH/pyexpint_toms/
├── runs/
│   └── <CAMPAIGN_ID>/
│       ├── campaign.env
│       ├── code/                   # source-mode only; staged snapshot
│       ├── ops/python/
│       ├── slurm/
│       ├── logs/
│       ├── results/
│       │   ├── raw/
│       │   └── consolidated/
│       ├── metadata/
│       └── tmp/
└── runtime/                        # one staged SIF in future production mode
```

FSCRATCH is expendable. Every important result must be collected to HOME before
a run directory is removed.

## Provenance key

Every run has an immutable `CAMPAIGN_ID`. The source tree is hashed at staging time.
The collected HOME directory contains:

- source manifest/hash;
- Slurm job ID and accounting;
- compact JSON/CSV summaries;
- one compressed raw bundle containing raw JSON, logs, metadata and the exact Slurm script;
- SHA-256 manifest for all persistent campaign artifacts.
