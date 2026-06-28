"""Deterministic changelog aggregation for autonomous release (Phase A2).

The release brief points at ``towncrier``. This repository's offline validator
environment does not carry a ``towncrier`` wheel, so this module owns a thin
towncrier-compatible adapter over the existing CE fragment convention instead
of adding a network dependency or silently pretending the runtime exists.

Supported front matter shapes:

    ---
    slug: <slug>
    date: <YYYY-MM-DD>
    kind: <added|changed|fixed|...>
    scope: <free text>
    issue: <ce-ops#N, ...>
    ---

and the older variant:

    ---
    slug: <slug>
    date: <YYYY-MM-DD>
    type: <added|changed|fixed|...>
    scope: <free text>
    ticket: <ce-ops#N, ...>
    ---

Fragments without front matter are still included (slug derived from the
filename, kind = ``other``) so nothing silently drops from a release.

``since-last-tag`` selection: fragments whose commit was introduced after the
previous ``release/*`` tag's commit. When no ``release/*`` tag exists yet, the
whole active fragment set is the release. This module only reads fragments and
emits notes; it does NOT archive, move, or delete anything.
"""
from __future__ import annotations

import importlib.util
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
_ISO_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

TOWNCRIER_COMPATIBLE_CONFIG = {
    "directory": CHANGELOG_DIRNAME,
    "section_field": "kind",
    "section_field_alias": "type",
    "issue_field": "issue",
    "issue_field_alias": "ticket",
    "filename": "CHANGELOG.md",
    "start_string": "<!-- towncrier release notes start -->",
    "template": "ce-frontmatter-fragment",
    "types": {kind: _KIND_HEADINGS.get(kind, kind.capitalize()) for kind in _KIND_ORDER},
}


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
class TowncrierCompatibility:
    """Runtime-free description of the CE fragment adapter for towncrier."""

    runtime_available: bool
    config: dict[str, object]


@dataclass(frozen=True)
class ChangelogResult:
    version: str
    notes: str
    github_body: str
    release_date: str
    fragment_count: int
    since_tag: str | None
    fragments: tuple[Fragment, ...] = field(default_factory=tuple)
    towncrier: TowncrierCompatibility | None = None


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
        kind=(fields.get("kind") or fields.get("type") or "other").strip().lower(),
        scope=fields.get("scope", ""),
        issue=fields.get("issue") or fields.get("ticket", ""),
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


def _fragment_sort_key(fragment: Fragment) -> tuple[str, str, str]:
    return (fragment.date, fragment.slug, fragment.path.name)


def _release_date(fragments: list[Fragment], explicit_date: str | None) -> str:
    if explicit_date:
        if not _ISO_DATE_RE.match(explicit_date):
            raise ReleaseChangelogError(f"release date must be YYYY-MM-DD: {explicit_date!r}")
        return explicit_date
    dates = sorted({frag.date for frag in fragments if _ISO_DATE_RE.match(frag.date)})
    return dates[-1] if dates else "undated"


def _indent_markdown(lines: list[str]) -> list[str]:
    rendered: list[str] = []
    for line in lines:
        rendered.append(f"  {line}" if line else "")
    return rendered


def _body_lines_for_bullet(frag: Fragment) -> list[str]:
    body = frag.body.strip()
    if not body:
        return [frag.slug]
    raw_lines = body.splitlines()
    first_idx = next((idx for idx, line in enumerate(raw_lines) if line.strip()), 0)
    first = re.sub(r"^[-*]\s+", "", raw_lines[first_idx].strip())
    return [first, *_indent_markdown(raw_lines[first_idx + 1 :])]


def _render_grouped_fragments(lines: list[str], grouped: dict[str, list[Fragment]], *, github: bool) -> None:
    heading_prefix = "###" if github else "##"
    for kind in sorted(grouped, key=_kind_sort_key):
        heading = _KIND_HEADINGS.get(kind, kind.capitalize())
        lines.append(f"{heading_prefix} {heading}")
        lines.append("")
        for frag in sorted(grouped[kind], key=_fragment_sort_key):
            suffix_bits = []
            if frag.issue:
                suffix_bits.append(frag.issue)
            if frag.scope:
                suffix_bits.append(frag.scope)
            suffix = f" ({'; '.join(suffix_bits)})" if suffix_bits else ""
            body_lines = _body_lines_for_bullet(frag)
            lines.append(f"- **{frag.slug}**{suffix}: {body_lines[0]}")
            for line in body_lines[1:]:
                lines.append(line)
        lines.append("")


def _group_fragments(fragments: list[Fragment]) -> dict[str, list[Fragment]]:
    grouped: dict[str, list[Fragment]] = {}
    for frag in fragments:
        grouped.setdefault(frag.kind, []).append(frag)
    return grouped


def _render_notes(version: str, release_date: str, fragments: list[Fragment], since_tag: str | None) -> str:
    grouped = _group_fragments(fragments)

    lines = [f"# Release {version} - {release_date}", ""]
    lines.append(
        f"_Selected {len(fragments)} changelog fragment(s) since {since_tag or 'the beginning'}._"
    )
    lines.append("")
    if not fragments:
        lines.append("_No changelog fragments for this release._")
        lines.append("")
        return "\n".join(lines)

    _render_grouped_fragments(lines, grouped, github=False)
    return "\n".join(lines)


def _render_github_body(version: str, release_date: str, fragments: list[Fragment], since_tag: str | None) -> str:
    grouped = _group_fragments(fragments)

    lines = [
        f"## Release {version} - {release_date}",
        "",
        f"Generated from {len(fragments)} `.ce/changelog` fragment(s) since `{since_tag or 'the beginning'}`.",
        "",
    ]
    if not fragments:
        lines.append("_No changelog fragments for this release._")
        lines.append("")
        return "\n".join(lines)

    _render_grouped_fragments(lines, grouped, github=True)
    return "\n".join(lines)


def towncrier_compatibility() -> TowncrierCompatibility:
    """Return the offline adapter shape without importing or requiring towncrier."""

    return TowncrierCompatibility(
        runtime_available=importlib.util.find_spec("towncrier") is not None,
        config=dict(TOWNCRIER_COMPATIBLE_CONFIG),
    )


def aggregate_changelog(
    *,
    repo_root: Path | str,
    version: str,
    since_tag: str | None = None,
    release_date: str | None = None,
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
    fragment_list = list(fragments)
    resolved_date = _release_date(fragment_list, release_date)
    notes = _render_notes(version, resolved_date, fragment_list, resolved_tag)
    github_body = _render_github_body(version, resolved_date, fragment_list, resolved_tag)
    return ChangelogResult(
        version=version,
        notes=notes,
        github_body=github_body,
        release_date=resolved_date,
        fragment_count=len(fragments),
        since_tag=resolved_tag,
        fragments=fragments,
        towncrier=towncrier_compatibility(),
    )
