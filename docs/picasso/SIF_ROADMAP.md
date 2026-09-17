# Roadmap to the final Apptainer `.sif` runtime

## Development / benchmark phase now

`PYEXPINT_RUNTIME=source`

The active source tree is staged from HOME to:

```text
$FSCRATCH/pyexpint_toms/runs/<CAMPAIGN_ID>/code/
```

Python/NumPy/SciPy come from the Picasso `anaconda` module. No full Conda
environment is created in HOME.

This is intentionally simple while algorithms and benchmarks are changing.

## Production / publication phase

`PYEXPINT_RUNTIME=sif`

Build the image outside Picasso in a controlled environment, with:

- exact PyEXPINT release/tag;
- pinned Python/NumPy/SciPy versions;
- benchmark runner;
- metadata labels;
- Apptainer definition file;
- build log;
- SHA-256.

Store the canonical image in:

```text
$HOME/pyexpint_toms/containers/images/pyexpint_toms_vX.Y.Z.sif
```

and its provenance in:

```text
$HOME/pyexpint_toms/containers/manifests/
```

Stage a **single copy** to:

```text
$FSCRATCH/pyexpint_toms/runtime/
```

Campaign run directories then reference that SIF rather than staging hundreds or
thousands of Python/environment files.

The existing Slurm script already supports this mode. Change only:

```bash
export PYEXPINT_RUNTIME=sif
export PYEXPINT_SIF_NAME=pyexpint_toms_vX.Y.Z.sif
```

in `ops/config/picasso.env`.

## Why SIF is the final target

- one runtime file instead of a Python environment with many inodes;
- exact executable environment for GitHub/Zenodo/TOMS reproducibility;
- easy SHA-256 verification;
- simple PC → Picasso transfer;
- source repository and executable artifact remain separately auditable.

The source code remains canonical in Git/GitHub. The SIF is a reproducible runtime
artifact, not a replacement for the repository.
