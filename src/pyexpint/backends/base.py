from __future__ import annotations


class Backend:
    """Backend protocol base with optional cumulative statistics."""

    name = "base"

    def bind(self, linear_operator, h: float):
        raise NotImplementedError

    def reset_stats(self) -> None:
        """Reset cumulative backend counters, if any."""

    def stats(self) -> dict:
        """Return cumulative backend counters."""
        return {}
