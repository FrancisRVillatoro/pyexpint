# Recorded validation, not a newly generated test history

`reviewed-snapshot/` is copied byte for byte from the supplied review package.
The validated source tree is `9f62cbf6a6455868e358386ccff824507287aeb3`;
all installed Python modules and tests are unchanged for public release 1.0.0.
The old wheel/sdist inside these logs retain their historical 0.9.0 label and
must not be confused with the new distributions in `distribution/`.

The detailed logs were produced in the preparation Linux environment (Python
3.11.15, NumPy 1.24.3, SciPy 1.10.1, pytest 7.1.2). A fixed WSL label in a script
header is NOT evidence that the corresponding run occurred on the author's PC.
The 53 failures on the C1 baseline are an intentional negative-control outcome;
they are not failures of the reviewed candidate. See the individual JUnit records.

No claim that historical timing data were remeasured on the new public release
is made. The workflow run attached to the final GitHub commit, when completed,
is separate additional CI evidence. Original tests and experiments are not
rerun merely to create this directory.
