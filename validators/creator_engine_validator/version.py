"""CE version identity — the single derived ``<semver>+<short-sha>`` token.

ce-ops#25: users need ONE honest CE version identity, derived rather than
hand-maintained, visible from ``ce``/``cev3`` (``--version``), ``ce doctor``,
the Cockpit, and the governed session frame.

The token is exactly ``<semver>+<short-sha>``:

* ``<semver>`` is :data:`SEMVER` (== :data:`__version__`, tied to
  ``validators/pyproject.toml [project].version`` by the packaging guard);
* ``<short-sha>`` is ``git rev-parse --short=8 HEAD`` when a live checkout is
  reachable, else the first 8 of the baked :data:`._version.BUILD_GIT_SHA`.

Resolution is cached once per process per normalized repo root (Open-Q1): a
fresh process reflects the current checkout HEAD; a long-running process keeps a
stable token; the L2 Cockpit fold never runs git — it receives the token as
data. If neither live git nor a valid baked SHA is available the derivation
fails closed (:class:`VersionDerivationError`) — no surface fabricates
``unknown`` (Open-Q2).

This module is part of the shared governance base (``_versions.py`` classifies
unlisted modules as ``shared``); it imports only stdlib plus the generated
``_version`` constants, so it couples to neither the v1 nor the v3 runtime.
"""
from __future__ import annotations

import argparse
import functools
import string
import subprocess
import sys
from pathlib import Path

#: The package semver. Kept a bare string literal because the packaging guard
#: reads it via AST (``packaging_runtime._source_declared_version``) and asserts
#: it equals ``pyproject [project].version``. Semver-compatible for package
#: consumers (``creator_engine_validator.__version__``).
__version__ = "0.3.1"

#: The ``<semver>`` half of the CE token (== :data:`__version__`).
SEMVER = __version__

_HEXDIGITS = frozenset(string.hexdigits)

# Baked build identity (the generated ``_version.py``, committed before the
# wheel build). Imported defensively: a source/editable process prefers LIVE
# git and only falls back to the baked SHA, so a missing/partial ``_version``
# must NOT, by itself, break live-git resolution.
try:  # pragma: no cover - exercised via the generator + wheel proofs
    from ._version import BUILD_GIT_SHA as _BAKED_BUILD_GIT_SHA
except Exception:  # noqa: BLE001 - any import failure degrades to live-git-only
    _BAKED_BUILD_GIT_SHA = None


class VersionDerivationError(RuntimeError):
    """Neither live git nor a valid baked SHA was available — fail closed.

    No version surface fabricates ``unknown``; the derivation raises instead.
    """


def _is_hex(value: object, *, min_len: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) >= min_len
        and all(ch in _HEXDIGITS for ch in value)
    )


# --- live-git / baked resolution -------------------------------------------


def _git_short_head(cwd: str) -> str | None:
    """``git -C <cwd> rev-parse --short=8 HEAD`` → short sha, or None on failure.

    None means: not a checkout, git absent, or non-hex output — the caller then
    falls through to the next resolution source.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--short=8", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out if _is_hex(out, min_len=8) else None


def _baked_short() -> str | None:
    """First 8 of the baked full SHA, or None when it is missing/malformed."""
    return _BAKED_BUILD_GIT_SHA[:8] if _is_hex(_BAKED_BUILD_GIT_SHA, min_len=8) else None


@functools.cache
def _resolve_short_sha(repo_root_key: str | None) -> str:
    """Resolve the short sha ONCE per process per normalized repo root (Open-Q1).

    Fallback order (Open-Q2): explicit repo-root git → the package's
    containing-checkout git → baked ``_version.BUILD_GIT_SHA`` → fail closed.
    """
    short: str | None = None
    if repo_root_key is not None:
        short = _git_short_head(repo_root_key)
    if short is None:
        short = _git_short_head(str(Path(__file__).resolve().parent))
    if short is None:
        short = _baked_short()
    if short is None:
        raise VersionDerivationError(
            "cannot derive CE version: no live git checkout reachable and no "
            "valid baked BUILD_GIT_SHA (_version.py missing or malformed)"
        )
    return short


def _normalize_repo_root(repo_root: Path | str | None) -> str | None:
    if repo_root is None:
        return None
    try:
        return str(Path(repo_root).resolve())
    except OSError:
        return str(repo_root)


def ce_version(repo_root: Path | str | None = None) -> str:
    """Return the user-visible CE version token ``<semver>+<short-sha>``.

    Resolved once per process per normalized repo root (cached), so a long-
    running process keeps a stable token while a fresh process reflects the
    current checkout HEAD. Raises :class:`VersionDerivationError` if neither
    live git nor a valid baked SHA is available — never returns ``unknown``.
    """
    short = _resolve_short_sha(_normalize_repo_root(repo_root))
    return f"{SEMVER}+{short}"


def add_version_flag(
    parser: argparse.ArgumentParser, *, repo_root: Path | str | None = None
) -> None:
    """Register a top-level ``--version`` that prints the token to stdout + exits.

    Lazy by construction — :func:`ce_version` runs only when ``--version`` is
    actually passed (the resolution happens in the action's ``__call__``, not at
    parser-build time), so a no-git wheel install lacking a baked SHA fails
    closed ONLY on the version path, never on every command.
    """

    class _CEVersionAction(argparse.Action):
        def __init__(self, option_strings, dest, **kwargs):
            kwargs.setdefault("nargs", 0)
            kwargs.setdefault("default", argparse.SUPPRESS)
            kwargs.setdefault(
                "help", "show the CE version identity (<semver>+<short-sha>) and exit"
            )
            super().__init__(option_strings, dest, **kwargs)

        def __call__(self, action_parser, namespace, values, option_string=None):
            sys.stdout.write(ce_version(repo_root) + "\n")
            action_parser.exit()

    parser.add_argument("--version", action=_CEVersionAction)


# --- build-time generation -------------------------------------------------

_BUILD_FILE_NAME = "_version.py"
_GENERATED_HEADER = (
    '"""GENERATED build identity — do not edit by hand.\n\n'
    "Written by ``python -m creator_engine_validator.version --write-build-file``\n"
    "(reads ``validators/pyproject.toml`` + ``git rev-parse --verify HEAD``).\n"
    "Committed BEFORE the wheel build so the wheel==source byte-parity contract\n"
    "(``packaging_runtime.verify_wheel_matches_source``) still holds. "
    "``BUILD_GIT_SHA``\n"
    "is the gate's merge-parent HEAD — the baked fallback a no-git wheel install "
    "uses.\n"
    '"""\n'
)


def _read_pyproject_semver(repo_root: Path) -> str | None:
    """Read ``[project].version`` from ``<repo_root>/validators/pyproject.toml``.

    Accepts either a repo root (``validators/pyproject.toml``) or the validators
    dir itself (``pyproject.toml``).
    """
    import tomllib

    candidates = [repo_root / "validators" / "pyproject.toml", repo_root / "pyproject.toml"]
    for pyproject in candidates:
        if pyproject.is_file():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            version = data.get("project", {}).get("version")
            return version if isinstance(version, str) and version else None
    return None


def _git_full_head(cwd: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out if _is_hex(out, min_len=40) else None


def _git_is_dirty(cwd: str) -> bool | None:
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return bool(proc.stdout.strip())


def render_build_file(semver: str, build_git_sha: str) -> str:
    """Render the generated ``_version.py`` body (constants only)."""
    return (
        _GENERATED_HEADER
        + "\n"
        + f'SEMVER = "{semver}"\n'
        + f'BUILD_GIT_SHA = "{build_git_sha}"\n'
    )


def write_build_file(
    repo_root: Path | str,
    *,
    allow_dirty: bool = False,
    out_path: Path | str | None = None,
) -> Path:
    """Generate ``_version.py`` from pyproject semver + ``git rev-parse HEAD``.

    Refuses a missing semver or an unresolvable HEAD. Refuses a dirty work tree
    UNLESS ``allow_dirty`` — the in-gate rebuild (where the generated file and
    the rebuilt wheel are committed together as one manifest) passes it, so the
    baked SHA is the gate's merge-parent HEAD. Writes to the package's own
    ``_version.py`` unless ``out_path`` overrides it (tests). Returns the path.
    """
    root = Path(repo_root)
    semver = _read_pyproject_semver(root)
    if not semver:
        raise VersionDerivationError(f"generator: no [project].version under {root}")
    full = _git_full_head(str(root))
    if full is None:
        raise VersionDerivationError(f"generator: cannot resolve git HEAD at {root}")
    if not allow_dirty and _git_is_dirty(str(root)):
        raise VersionDerivationError(
            f"generator: refusing to bake a build SHA over a dirty work tree at "
            f"{root} (commit first, or pass --allow-dirty for the in-gate build)"
        )
    target = Path(out_path) if out_path is not None else Path(__file__).resolve().parent / _BUILD_FILE_NAME
    target.write_text(render_build_file(semver, full), encoding="utf-8")
    return target


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m creator_engine_validator.version",
        description="generate the baked _version.py build-identity module",
    )
    parser.add_argument(
        "--write-build-file",
        action="store_true",
        required=True,
        help="write creator_engine_validator/_version.py",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="repo root holding validators/pyproject.toml (default: .)",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="bake HEAD even with a dirty work tree (the in-gate rebuild)",
    )
    args = parser.parse_args(argv)
    path = write_build_file(args.repo_root, allow_dirty=args.allow_dirty)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
