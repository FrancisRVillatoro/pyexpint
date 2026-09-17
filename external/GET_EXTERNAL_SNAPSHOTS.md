# External comparator snapshots for the final TOMS benchmark

These repositories are **not** dependencies of PyEXPINT and are not redistributed in the PyEXPINT archive.
They should be checked out separately at the pinned commits below.

## rkstiff

Pinned commit:

```text
ccf11f4c8dac3e0b6f8fd23ac357c633c1623a0f
```

On an internet-connected machine:

```bash
git clone https://github.com/whalenpt/rkstiff.git
cd rkstiff
git checkout ccf11f4c8dac3e0b6f8fd23ac357c633c1623a0f
git rev-parse HEAD
```

Then create a transport archive if the benchmark machine has no internet:

```bash
cd ..
tar -czf rkstiff-ccf11f4.tar.gz rkstiff
```

## LeXInt

Pinned commit:

```text
90319e940aec256eec9e340f7469c52054ae33fe
```

```bash
git clone https://github.com/Pranab-JD/LeXInt.git
cd LeXInt
git checkout 90319e940aec256eec9e340f7469c52054ae33fe
git rev-parse HEAD
cd ..
tar -czf LeXInt-90319e94.tar.gz LeXInt
```

## KIOPS

Use a separate checkout of the official repository and record the exact commit used in the benchmark metadata. Do not copy its source into PyEXPINT.

## Benchmark provenance

For every external run, record:

- repository commit;
- license file hash;
- Python/MATLAB version;
- NumPy/SciPy versions where relevant;
- environment variables controlling threading;
- exact problem parameters and tolerances;
- raw per-repeat timings.
