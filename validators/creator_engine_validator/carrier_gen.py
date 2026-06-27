"""Per-PR carrier/changelog generation helpers.

These helpers intentionally share parsing and canonicalization with the
``path_manifest_fidelity`` verifier so generated carriers round-trip through
the same contract the gate enforces.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .checks.path_manifest_fidelity import (
    MANIFEST_DIR,
    _normalize_manifest,
    branch_slug,
    parse_carrier,
)

GitRunner = Callable[[Sequence[str], Path], tuple[int, str, str]]


@dataclass(frozen=True)
class CarrierSpec:
    """Inputs needed to write a PR changelog fragment and path manifest."""

    head_ref: str
    issue: str
    title: str
    kind: str
    scope: str
    body: str
    date: str
    base: str = "origin/main"

    @property
    def slug(self) -> str:
        return branch_slug(self.head_ref)


@dataclass(frozen=True)
class WrittenCarriers:
    """Paths and computed identity for the generated carrier files."""

    changelog_path: Path
    manifest_path: Path
    slug: str
    paths: tuple[str, ...]
    count: int
    sha256: str


def _default_git_runner(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def _normalise_paths(paths: Sequence[str]) -> tuple[tuple[str, ...], int, str]:
    count, sha256, _ = _normalize_manifest([p.strip() for p in paths if p.strip()])
    return tuple(sorted({p.strip() for p in paths if p.strip()})), count, sha256


def compute_path_set(
    repo_root: str | Path,
    slug: str,
    base: str = "origin/main",
    *,
    git_runner: GitRunner | None = None,
) -> tuple[tuple[str, ...], int, str]:
    """Return canonical ``base..HEAD`` paths plus this PR's manifest carrier.

    The hash is verifier-compatible:
    ``sha256("\\n".join(sorted(unique_paths)) + "\\n")``.
    """

    root = Path(repo_root)
    runner = git_runner or _default_git_runner
    returncode, stdout, stderr = runner(["diff", "--name-only", "--find-renames", f"{base}..HEAD"], root)
    if returncode != 0:
        detail = stderr.strip() or "unknown error"
        raise RuntimeError(f"git diff --name-only --find-renames {base}..HEAD failed: {detail}")

    manifest_path = f"{MANIFEST_DIR}/{slug}.md"
    raw_paths = list(stdout.splitlines()) + [manifest_path]
    return _normalise_paths(raw_paths)


def render_manifest(
    slug: str,
    issue: str,
    title: str,
    paths: Sequence[str],
    count: int,
    sha: str,
) -> str:
    """Render a verifier-readable per-PR path-manifest carrier."""

    canonical_paths, canonical_count, canonical_sha = _normalise_paths(paths)
    if count != canonical_count:
        raise ValueError(f"declared count {count} does not match {canonical_count} paths")
    if sha != canonical_sha:
        raise ValueError(f"declared sha {sha!r} does not match canonical sha {canonical_sha!r}")

    body = "\n".join(canonical_paths)
    text = (
        f"# PR path manifest — {issue} · {title}\n\n"
        f"This per-PR carrier (`{MANIFEST_DIR}/<branch-slug>.md`) lists the closed "
        "authorized path-set for this PR. CI runs "
        f"`verify-path-manifest --base <sha> --manifest-dir {MANIFEST_DIR} --head-ref {slug}` "
        "and requires this PR's `base..HEAD` diff to equal exactly the authorized "
        "path-set below; this carrier lists itself.\n\n"
        'Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.\n\n'
        f"AUTHORIZED_PATHS_COUNT={count}\n\n"
        f"AUTHORIZED_PATHS_SHA256={sha}\n\n"
        "```text\n"
        f"{body}\n"
        "```\n"
    )
    identity = parse_carrier(text)
    if identity is None or not identity.consistent:
        raise ValueError("rendered manifest did not round-trip through parse_carrier")
    return text


def render_changelog(
    slug: str,
    issue: str,
    title: str,
    kind: str,
    scope: str,
    body: str,
    date: str,
) -> str:
    """Render a CE changelog fragment with the repo's current frontmatter shape."""

    clean_body = body.strip()
    if not clean_body:
        clean_body = f"- {issue}"
    summary = title.strip()
    if summary and summary[-1] not in ".!?":
        summary = f"{summary}."
    return (
        "---\n"
        f"slug: {slug}\n"
        f"date: {date}\n"
        f"kind: {kind}\n"
        f"scope: {scope}\n"
        f"issue: {issue}\n"
        "---\n\n"
        f"**{summary}**\n\n"
        f"{clean_body}\n"
    )


def write_carriers(
    repo_root: str | Path,
    spec: CarrierSpec,
    *,
    git_runner: GitRunner | None = None,
) -> WrittenCarriers:
    """Write changelog first, then compute/write the self-inclusive manifest."""

    root = Path(repo_root)
    slug = spec.slug
    changelog_path = root / ".ce" / "changelog" / f"{slug}.md"
    manifest_path = root / MANIFEST_DIR / f"{slug}.md"

    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    changelog_path.write_text(
        render_changelog(
            slug,
            spec.issue,
            spec.title,
            spec.kind,
            spec.scope,
            spec.body,
            spec.date,
        ),
        encoding="utf-8",
    )

    diff_paths, _diff_count, _diff_sha256 = compute_path_set(
        root,
        slug,
        spec.base,
        git_runner=git_runner,
    )
    paths, count, sha256 = _normalise_paths([*diff_paths, f".ce/changelog/{slug}.md"])
    manifest_path.write_text(
        render_manifest(slug, spec.issue, spec.title, paths, count, sha256),
        encoding="utf-8",
    )

    return WrittenCarriers(
        changelog_path=changelog_path,
        manifest_path=manifest_path,
        slug=slug,
        paths=paths,
        count=count,
        sha256=sha256,
    )


__all__ = [
    "CarrierSpec",
    "WrittenCarriers",
    "compute_path_set",
    "render_changelog",
    "render_manifest",
    "write_carriers",
]
