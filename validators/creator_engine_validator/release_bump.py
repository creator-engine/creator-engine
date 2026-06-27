"""Tag-as-source-of-truth version bumper for autonomous release (Phase A1).

A release version has ONE source of truth: the ``release/vX.Y.Z`` tag. This
module drives the canonical semver source (``version.py:__version__`` and
``validators/pyproject.toml [project].version``) to the target derived from
that tag, then **asserts** ``tag_version == version.py.__version__``
fail-closed — exactly the pattern :mod:`.release_publish` uses when it raises
on ``wheel_manifest.version != version``.

It is *staged-only*: it mutates the working tree's version sources so the
downstream :mod:`.release_publish` stage can build a wheel at the requested
version. Nothing it does lands on ``main``; the version only becomes live when
the Operator-signed publish commit is made (Phase B). No publishing, no
signing, no tag creation happens here.

The bumper deliberately edits the two coupled sources only (the packaging
guard couples ``version.py`` ↔ ``pyproject.toml``); it re-runs that coupling
assertion after writing so the two can never drift.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: ``MAJOR.MINOR.PATCH`` with an optional ``-pre``/``+build`` suffix, matching
#: :data:`.release_publish.SEMVER_RE` so a bumped version is always stageable.
SEMVER_RE = re.compile(r"^(?P<core>[0-9]+\.[0-9]+\.[0-9]+)(?P<suffix>[-+][0-9A-Za-z.-]+)?$")
_CORE_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
#: ``release/vX.Y.Z`` (the only release-tag shape the trigger pipeline arms).
RELEASE_TAG_RE = re.compile(r"^release/v(?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?)$")

_PARTS = ("major", "minor", "patch")


class ReleaseBumpError(RuntimeError):
    """Version bump refused before the working tree was mutated (fail-closed)."""


@dataclass(frozen=True)
class BumpResult:
    version: str
    previous_version: str
    source: str  # "tag" or "part:<major|minor|patch>"
    version_py: Path
    pyproject: Path


def version_from_tag(tag: str) -> str:
    """Extract ``X.Y.Z`` from a ``release/vX.Y.Z`` tag, fail-closed."""
    match = RELEASE_TAG_RE.fullmatch(tag.strip())
    if not match:
        raise ReleaseBumpError(
            f"not a release tag: {tag!r}; expected release/vMAJOR.MINOR.PATCH"
        )
    return match.group("version")


def next_version(current: str, part: str) -> str:
    """Compute the next core semver from ``current`` bumping ``part``.

    Operates on the ``MAJOR.MINOR.PATCH`` core only; any pre-release/build
    suffix on ``current`` is dropped (a bump produces a clean release core).
    """
    if part not in _PARTS:
        raise ReleaseBumpError(f"invalid part {part!r}; expected one of {_PARTS}")
    match = SEMVER_RE.fullmatch(current.strip())
    if not match:
        raise ReleaseBumpError(f"current version {current!r} is not valid semver")
    major, minor, patch = (int(n) for n in match.group("core").split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _validators_dir(repo_root: Path) -> Path:
    if (repo_root / "validators" / "pyproject.toml").is_file():
        return repo_root / "validators"
    if (repo_root / "pyproject.toml").is_file():
        return repo_root
    raise ReleaseBumpError(f"cannot locate validators/pyproject.toml under {repo_root}")


def _read_version_py(version_py: Path) -> str:
    text = version_py.read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', text, flags=re.MULTILINE)
    if not match:
        raise ReleaseBumpError(f"no __version__ assignment found in {version_py}")
    return match.group(1)


def _read_pyproject_version(pyproject: Path) -> str:
    import tomllib

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ReleaseBumpError(f"no [project].version in {pyproject}")
    return version


def _write_version_py(version_py: Path, new_version: str) -> None:
    text = version_py.read_text(encoding="utf-8")
    replaced, count = re.subn(
        r'^(__version__ = ")[^"]+(")$',
        rf"\g<1>{new_version}\g<2>",
        text,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ReleaseBumpError(
            f"expected exactly one __version__ assignment in {version_py}, found {count}"
        )
    version_py.write_text(replaced, encoding="utf-8")


def _write_pyproject_version(pyproject: Path, new_version: str) -> None:
    text = pyproject.read_text(encoding="utf-8")
    # Only the [project] table version line. The packaging guard reads
    # [project].version; we anchor on the bare top-level `version = "..."`
    # assignment, which is the [project] version in this pyproject.
    replaced, count = re.subn(
        r'^(version = ")[^"]+(")$',
        rf"\g<1>{new_version}\g<2>",
        text,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ReleaseBumpError(
            f"expected exactly one top-level version assignment in {pyproject}, found {count}"
        )
    pyproject.write_text(replaced, encoding="utf-8")


def bump_release_version(
    *,
    repo_root: Path | str,
    tag: str | None = None,
    part: str | None = None,
) -> BumpResult:
    """Drive the canonical semver sources to the release target, fail-closed.

    Exactly one of ``tag`` (``release/vX.Y.Z``) or ``part`` must be given:

    * ``tag``: target version IS the tag's version (tag-as-source-of-truth).
    * ``part``: target = :func:`next_version` of the current ``version.py``
      version (the ``workflow_dispatch`` rehearsal path).

    Writes ``version.py:__version__`` and ``pyproject [project].version``
    atomically, then asserts the two agree AND that, for the tag path, the
    written version equals the tag version — refusing (and rolling the two
    files back) on any mismatch. This is staging only: nothing is committed,
    nothing signed, nothing published.
    """
    if (tag is None) == (part is None):
        raise ReleaseBumpError("provide exactly one of tag or part")

    root = Path(repo_root).resolve()
    validators = _validators_dir(root)
    version_py = validators / "creator_engine_validator" / "version.py"
    pyproject = validators / "pyproject.toml"
    if not version_py.is_file():
        raise ReleaseBumpError(f"missing canonical version source: {version_py}")
    if not pyproject.is_file():
        raise ReleaseBumpError(f"missing pyproject: {pyproject}")

    previous = _read_version_py(version_py)
    py_previous = _read_pyproject_version(pyproject)
    if previous != py_previous:
        raise ReleaseBumpError(
            f"version sources already drifted before bump: version.py={previous!r} "
            f"pyproject={py_previous!r}; resolve the coupling first"
        )

    if tag is not None:
        target = version_from_tag(tag)
        source = "tag"
    else:
        target = next_version(previous, part)  # type: ignore[arg-type]
        source = f"part:{part}"

    if not SEMVER_RE.fullmatch(target):
        raise ReleaseBumpError(f"computed target version {target!r} is not valid semver")

    original_version_py = version_py.read_bytes()
    original_pyproject = pyproject.read_bytes()
    try:
        _write_version_py(version_py, target)
        _write_pyproject_version(pyproject, target)

        # Fail-closed coupling + tag-agreement assertions on the written tree.
        written_py = _read_version_py(version_py)
        written_pyproject = _read_pyproject_version(pyproject)
        if written_py != target or written_pyproject != target:
            raise ReleaseBumpError(
                "post-write version drift: "
                f"version.py={written_py!r} pyproject={written_pyproject!r} target={target!r}"
            )
        if tag is not None and written_py != version_from_tag(tag):
            raise ReleaseBumpError(
                f"tag/version disagreement after bump: tag={tag!r} version.py={written_py!r}"
            )
    except Exception:
        version_py.write_bytes(original_version_py)
        pyproject.write_bytes(original_pyproject)
        raise

    return BumpResult(
        version=target,
        previous_version=previous,
        source=source,
        version_py=version_py,
        pyproject=pyproject,
    )
