# Migration to v0.8.2.dev0

v0.8.2.dev0 absorbs the Picasso development hotfixes v0.8.1a--e into one
clean source tree. The canonical Picasso runtime is:

- `python/3.11.4`
- NumPy >= 1.24 (Picasso: 1.24.3)
- SciPy >= 1.10 (Picasso: 1.10.1)

The SciPy GMRES compatibility layer supports both the older `tol=` API and the
newer `rtol=` API.

The v0.8.1 pilot array is retained as a validation campaign only. Final TOMS
wall-clock measurements use the single-job balanced sequential protocol in
`TOMS_TIMING_PROTOCOL.md`.
