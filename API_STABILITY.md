# Public API — release 1.0.0

This release publishes the reviewed candidate without changes to its executable
Python sources. It retains the named core API in the historical 0.9 document,
while incorporating the reviewed correctness, error-reporting, instrumentation
and backend-cloning changes already present in that candidate.

The historical policy is retained at
`provenance/historical_documentation/API_STABILITY.md`. It is not a claim that
corrected work-statistics dictionaries are structurally identical to those of
the old public release. Missing work, partial attempts, and units must be read
according to the current source and tests. Implementation-private names and
benchmark drivers are not promised as stable extension APIs.

The limits documented by the manuscript (fixed-step history, conditional starter
accuracy, ETD34 estimator degeneracy, and backend admissibility) remain in force.
No new method or compatibility guarantee is invented by the version-number change.
