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

import os
import re
import subprocess
import tempfile
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


def _core_tuple(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(version.strip())
    if not match:
        raise ReleaseBumpError(f"version {version!r} is not valid semver")
    major, minor, patch = match.group("core").split(".")
    return int(major), int(minor), int(patch)


def _rehearsal_baseline(current: str, tag_version: str | None) -> str:
    """Use the greater of current source semver and latest release-tag semver."""
    if tag_version is None:
        return current
    return tag_version if _core_tuple(tag_version) > _core_tuple(current) else current


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _latest_release_tag_version(repo_root: Path) -> str | None:
    """Latest valid ``release/v*`` tag version, or None outside a git repo.

    The rehearsal path is allowed to run in throwaway fixtures with no git
    history, so tag discovery is advisory: no git/no tag means "use current
    version.py".
    """
    proc = _git(repo_root, "tag", "--list", "release/v*", "--sort=-creatordate")
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        tag = line.strip()
        if not tag:
            continue
        try:
            return version_from_tag(tag)
        except ReleaseBumpError:
            continue
    return None


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
    _atomic_write_text(version_py, replaced)


def _write_pyproject_version(pyproject: Path, new_version: str) -> None:
    text = pyproject.read_text(encoding="utf-8")
    replaced, count = _replace_project_version(text, new_version)
    if count != 1:
        raise ReleaseBumpError(
            f"expected exactly one [project].version assignment in {pyproject}, found {count}"
        )
    _atomic_write_text(pyproject, replaced)


def _replace_project_version(text: str, new_version: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    in_project = False
    count = 0
    rendered: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
        if in_project:
            line, replaced = re.subn(
                r'^(\s*version\s*=\s*")[^"]+(".*)$',
                rf"\g<1>{new_version}\g<2>",
                line,
            )
            count += replaced
        rendered.append(line)
    return "".join(rendered), count


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def bump_release_version(
    *,
    repo_root: Path | str,
    tag: str | None = None,
    part: str | None = None,
) -> BumpResult:
    """Drive the canonical semver sources to the release target, fail-closed.

    Exactly one of ``tag`` (``release/vX.Y.Z``) or ``part`` must be given:

    * ``tag``: target version IS the tag's version (tag-as-source-of-truth).
    * ``part``: target = :func:`next_version` from the greater semver core of
      current ``version.py`` and the latest valid ``release/v*`` tag when one
      is visible (the ``workflow_dispatch`` rehearsal path).

    Writes ``version.py:__version__`` and ``pyproject [project].version``
    with atomic per-file replacement and transaction rollback, then asserts
    the two agree AND that, for the tag path, the
    written version equals the tag version — refusing (and rolling the two
    files back) on any mismatch. This is staging only: nothing is committed,
    nothing signed, nothing published.

    ``version_runtime.render_build_file`` is intentionally not used here:
    that renders the generated ``_version.py`` build-identity file tied to a
    commit SHA. The bump surface owns only the canonical source semver files;
    release-stage regenerates ``_version.py`` later at build time.
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
        baseline = _rehearsal_baseline(previous, _latest_release_tag_version(root))
        target = next_version(baseline, part)  # type: ignore[arg-type]
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
        _atomic_write_bytes(version_py, original_version_py)
        _atomic_write_bytes(pyproject, original_pyproject)
        raise

    return BumpResult(
        version=target,
        previous_version=previous,
        source=source,
        version_py=version_py,
        pyproject=pyproject,
    )
