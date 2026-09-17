from __future__ import annotations

"""Backend work/memory metrics used by the reproducible benchmark suite."""


def estimated_backend_workspace_bytes(backend_name: str, stats: dict) -> int | None:
    """Estimate peak matrix-function workspace from backend statistics.

    This is an algorithmic workspace estimate, not process RSS.  It intentionally
    excludes the problem state, sparse matrix storage, Python-object overhead and
    small cached scalar data.  Complex128 (16 bytes) is used conservatively.
    """
    n = int(stats.get("max_operator_dimension", 0) or 0)
    if n <= 0:
        return None
    name = backend_name.lower().replace("adaptive:", "")
    if name in {"kiops", "krylov"}:
        m = int(stats.get("max_krylov_dim_used", 0) or 0)
        if m <= 0:
            return 0
        # Basis + one work vector + Hessenberg/projected matrix.
        return int(16 * (n * (m + 2) + (m + 2) * (m + 2)))
    if name == "leja":
        # Current implementation keeps input, Newton vector and accumulator.
        return int(16 * 3 * n)
    if name == "diagonal":
        return int(16 * n)
    if name == "dense":
        return int(16 * n * n)
    return None
