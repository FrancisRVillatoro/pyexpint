# PyEXPINT reproducibility material

This directory contains the release-facing reproducibility material for
PyEXPINT.

## Official TOMS benchmark evidence

The canonical backend-timing evidence is under `toms/`.

It consists of three independent replicas of the final homogeneous Leja80
campaign.  These are the campaigns intended for release-facing benchmark
documentation.

## Other benchmark files

The scripts under the repository-level `benchmarks/` directory are validation
and development experiments accumulated during PyEXPINT development.  They
remain useful for scientific validation, regression work, and historical
provenance, but they do not define the canonical TOMS timing comparison.

In particular, some historical backend experiments used explicit Leja
configurations different from the final Auto/Leja configuration.  They must
therefore not be interpreted as the release benchmark protocol.
