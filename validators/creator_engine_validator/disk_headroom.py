"""Disk headroom admission check.

Provides a single public function, ``check_headroom``, that inspects the
free space on the filesystem containing *path* and raises
``DiskHeadroomError`` when free space is below *min_free_gb*.

Design intent (F-1.2 from VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710):
  - Fail-closed *before* work starts, never mid-write.
  - Used by pr_preflight.py to block the baseline-diff test-command stage
    when free space would be consumed by the full pytest suite.
  - Keeps its own error type so callers can distinguish this class of
    failure from all other preflight errors and name the module explicitly
    in the error message.

Environment override: ``CE_SUITE_MIN_FREE_GB`` (float, default 30).
"""

from __future__ import annotations

import os

__all__ = [
    "DEFAULT_MIN_FREE_GB",
    "MIN_FREE_GB_ENV",
    "DiskHeadroomError",
    "check_headroom",
    "free_gb",
    "effective_min_free_gb",
]

DEFAULT_MIN_FREE_GB: float = 30.0
MIN_FREE_GB_ENV: str = "CE_SUITE_MIN_FREE_GB"


class DiskHeadroomError(RuntimeError):
    """Raised when free disk space is below the configured threshold.

    Attributes
    ----------
    path:
        The filesystem path that was checked.
    free_gb:
        Measured free space in gibibytes at the time of the check.
    min_free_gb:
        The minimum required free space in gibibytes.
    """

    def __init__(self, path: str, free_gb: float, min_free_gb: float) -> None:
        self.path = path
        self.free_gb = free_gb
        self.min_free_gb = min_free_gb
        super().__init__(
            f"disk_headroom: insufficient free space on {path!r}: "
            f"{free_gb:.1f} GiB free, {min_free_gb:.1f} GiB required "
            f"(set {MIN_FREE_GB_ENV} to override threshold)"
        )


def free_gb(path: str | os.PathLike[str] = ".") -> float:
    """Return free disk space in gibibytes for the filesystem containing *path*.

    Uses ``os.statvfs`` so the result reflects the POSIX free-blocks count
    (``f_bavail`` — blocks available to non-privileged users) multiplied by
    the block size (``f_frsize``).
    """
    stat = os.statvfs(path)
    free_bytes = stat.f_bavail * stat.f_frsize
    return free_bytes / (1024 ** 3)


def effective_min_free_gb() -> float:
    """Return the effective threshold from the environment or default."""
    raw = os.environ.get(MIN_FREE_GB_ENV, "").strip()
    if not raw:
        return DEFAULT_MIN_FREE_GB
    try:
        value = float(raw)
    except ValueError:
        raise RuntimeError(
            f"{MIN_FREE_GB_ENV} must be a positive number of gibibytes, got {raw!r}"
        ) from None
    if value <= 0:
        raise RuntimeError(
            f"{MIN_FREE_GB_ENV} must be a positive number of gibibytes, got {value!r}"
        )
    return value


def check_headroom(
    path: str | os.PathLike[str] = ".",
    min_free_gb: float | None = None,
) -> float:
    """Check that the filesystem containing *path* has sufficient free space.

    Parameters
    ----------
    path:
        A path on the filesystem to check.  Defaults to the current
        working directory.
    min_free_gb:
        Minimum required free space in gibibytes.  When ``None`` (default)
        the value is read from the ``CE_SUITE_MIN_FREE_GB`` environment
        variable, falling back to ``DEFAULT_MIN_FREE_GB`` (30 GiB).

    Returns
    -------
    float
        Measured free space in gibibytes (only when the check passes).

    Raises
    ------
    DiskHeadroomError
        When free space is strictly below *min_free_gb*.
    """
    threshold = min_free_gb if min_free_gb is not None else effective_min_free_gb()
    measured = free_gb(path)
    if measured < threshold:
        raise DiskHeadroomError(str(path), measured, threshold)
    return measured
