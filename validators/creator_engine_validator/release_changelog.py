"""Deterministic changelog aggregator for autonomous release (Phase A2).

Assembles the hand-authored ``.ce/changelog/*.md`` fragments into dated
release notes, grouped by ``kind``. The design's preferred rent — ``towncrier``
— is **not available offline** (no wheel in ``validators/wheelhouse``, not
importable in the build env), so per the design's stated fallback this is a
minimal, deterministic aggregator over the existing fragment convention:

    ---
    slug: <slug>
    date: <YYYY-MM-DD>
    kind: <added|changed|fixed|...>
    scope: <free text>
    issue: <ce-ops#N, ...>
    ---
    <markdown body>

Fragments without front-matter are still included (slug derived from the
filename, kind = ``other``) so nothing silently drops from a release.

``since-last-tag`` selection: fragments whose commit was introduced after the
previous ``release/*`` tag's commit. When no ``release/*`` tag exists yet (the
current state of the repo) the whole active fragment set is the release —
deterministic and re-runnable. This module only *reads* fragments and emits
notes; it does NOT archive/move anything (archive-on-publish is Phase B).
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

CHANGELOG_DIRNAME = ".ce/changelog"
RELEASE_TAG_GLOB = "release/*"

# Display order + heading for known kinds; everything else falls to "other".
_KIND_ORDER = (
    "added",
    "feat",
    "feature",
    "changed",
    "fixed",
    "fix",
    "hardening",
    "documented",
    "docs",
    "story",
    "epic",
    "chore",
)
_KIND_HEADINGS = {
    "added": "Added",
    "feat": "Added",
    "feature": "Added",
    "changed": "Changed",
    "fixed": "Fixed",
    "fix": "Fixed",
    "hardening": "Hardening",
    "documented": "Documentation",
    "docs": "Documentation",
    "story": "Stories",
    "epic": "Epics",
    "chore": "Chores",
    "other": "Other",
}
_FRONT_MATTER_RE = re.compile(r"\A---\n(?P<fm>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)


class ReleaseChangelogError(RuntimeError):
    """Changelog aggregation refused (fail-closed)."""


@dataclass(frozen=True)
class Fragment:
    path: Path
    slug: str
    date: str
    kind: str
    scope: str
    issue: str
    body: str


@dataclass(frozen=True)
class ChangelogResult:
    version: str
    notes: str
    fragment_count: int
    since_tag: str | None
    fragments: tuple[Fragment, ...] = field(default_factory=tuple)


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text.strip()
    fields: dict[str, str] = {}
    for line in match.group("fm").splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, match.group("body").strip()


def _load_fragment(path: Path) -> Fragment:
    text = path.read_text(encoding="utf-8")
    fields, body = _parse_front_matter(text)
    return Fragment(
        path=path,
        slug=fields.get("slug") or path.stem,
        date=fields.get("date", ""),
        kind=(fields.get("kind") or "other").strip().lower(),
        scope=fields.get("scope", ""),
        issue=fields.get("issue", ""),
        body=body,
    )


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _previous_release_tag(repo_root: Path) -> str | None:
    """Most recent ``release/*`` tag by tag creation order, or None.

    ``--sort=-creatordate`` puts the newest release tag first; absent any
    such tag (current repo state) returns None → "everything is the release".
    """
    proc = _git(repo_root, "tag", "--list", RELEASE_TAG_GLOB, "--sort=-creatordate")
    if proc.returncode != 0:
        return None
    tags = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return tags[0] if tags else None


def _fragments_changed_since(repo_root: Path, changelog_dir: Path, since_ref: str) -> set[str] | None:
    """Names of fragment files added/modified after ``since_ref``.

    Returns a set of basenames, or None if git could not resolve the diff
    (caller then falls back to including all fragments — fail-open on
    selection so a release never silently drops content).
    """
    rel = changelog_dir.relative_to(repo_root).as_posix()
    proc = _git(repo_root, "diff", "--name-only", f"{since_ref}..HEAD", "--", rel)
    if proc.returncode != 0:
        return None
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.endswith(".md"):
            names.add(Path(line).name)
    return names


def _kind_sort_key(kind: str) -> tuple[int, str]:
    try:
        return (_KIND_ORDER.index(kind), kind)
    except ValueError:
        return (len(_KIND_ORDER), kind)


def _render_notes(version: str, fragments: list[Fragment]) -> str:
    grouped: dict[str, list[Fragment]] = {}
    for frag in fragments:
        grouped.setdefault(frag.kind, []).append(frag)

    lines = [f"# Release {version}", ""]
    if not fragments:
        lines.append("_No changelog fragments for this release._")
        lines.append("")
        return "\n".join(lines)

    for kind in sorted(grouped, key=_kind_sort_key):
        heading = _KIND_HEADINGS.get(kind, kind.capitalize())
        lines.append(f"## {heading}")
        lines.append("")
        # Deterministic intra-group order: slug.
        for frag in sorted(grouped[kind], key=lambda f: f.slug):
            suffix = f" ({frag.issue})" if frag.issue else ""
            first_line = frag.body.splitlines()[0].strip() if frag.body else frag.slug
            # Strip a leading markdown bullet/emphasis so we control the bullet.
            first_line = re.sub(r"^[-*]\s+", "", first_line)
            lines.append(f"- **{frag.slug}**{suffix}: {first_line}")
        lines.append("")
    return "\n".join(lines)


def aggregate_changelog(
    *,
    repo_root: Path | str,
    version: str,
    since_tag: str | None = None,
) -> ChangelogResult:
    """Aggregate active ``.ce/changelog`` fragments into release notes.

    ``since_tag`` selects fragments introduced after that ref; when omitted it
    is auto-resolved to the most recent ``release/*`` tag, and when none exists
    the whole active fragment set is the release. Read-only — no fragment is
    moved or deleted (archive is Phase B publish).
    """
    root = Path(repo_root).resolve()
    changelog_dir = root / CHANGELOG_DIRNAME
    if not changelog_dir.is_dir():
        raise ReleaseChangelogError(f"changelog directory not found: {changelog_dir}")

    all_paths = sorted(
        p for p in changelog_dir.glob("*.md") if p.is_file()
    )

    resolved_tag = since_tag if since_tag is not None else _previous_release_tag(root)
    selected_names: set[str] | None = None
    if resolved_tag is not None:
        selected_names = _fragments_changed_since(root, changelog_dir, resolved_tag)

    if selected_names is None:
        chosen = all_paths
    else:
        chosen = [p for p in all_paths if p.name in selected_names]

    fragments = tuple(_load_fragment(p) for p in chosen)
    notes = _render_notes(version, list(fragments))
    return ChangelogResult(
        version=version,
        notes=notes,
        fragment_count=len(fragments),
        since_tag=resolved_tag,
        fragments=fragments,
    )
