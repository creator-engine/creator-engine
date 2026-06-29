"""Deterministic docs-as-skills bundle projector for ``ce ask``.

The support corpus is owned by ``support_corpus``. This module projects that
eligible product-lens corpus into a concrete, read-only skill bundle shape: one
stable skill per manifest family, with copied source files and citation
metadata. The projector returns data only; callers may hand the rendered file
map to a governed fresh-context answering seat, but this module performs no
filesystem writes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from . import support_corpus

BUNDLE_VERSION = 1
SKILL_PREFIX = "ce-support"


@dataclass(frozen=True)
class BundleSource:
    """One corpus source projected into a support skill."""

    path: str
    sha256: str
    bytes: int
    lines: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "lines": self.lines,
        }


@dataclass(frozen=True)
class SkillEntry:
    """A deterministic skill entry a fresh-context seat can load."""

    name: str
    family: str
    description: str
    sources: tuple[BundleSource, ...]
    skill_md: str
    files: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "family": self.family,
            "description": self.description,
            "sources": [s.to_dict() for s in self.sources],
            "skill_md": self.skill_md,
            "files": [{"path": p, "content": c} for p, c in self.files],
        }


@dataclass(frozen=True)
class SupportBundle:
    """Projected support-agent docs-as-skills bundle."""

    version: int
    corpus_sha256: str
    skills: tuple[SkillEntry, ...]
    eligible_paths: tuple[str, ...]
    rejected: tuple[tuple[str, str], ...]
    missing: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "corpus_sha256": self.corpus_sha256,
            "skills": [s.to_dict() for s in self.skills],
            "eligible_paths": list(self.eligible_paths),
            "rejected": [{"path": p, "reason": r} for p, r in self.rejected],
            "missing": list(self.missing),
        }

    def citation_paths(self) -> tuple[str, ...]:
        return tuple(src.path for skill in self.skills for src in skill.sources)

    def rendered_files(self) -> dict[str, str]:
        """Return a concrete skill-bundle file map, without writing it to disk."""
        files: dict[str, str] = {}
        for skill in self.skills:
            root = f"skills/{skill.name}"
            files[f"{root}/SKILL.md"] = skill.skill_md
            for rel, content in skill.files:
                files[f"{root}/{rel}"] = content
        return dict(sorted(files.items()))


def _expand_pattern(pattern: str, *, root: Path) -> tuple[str, ...]:
    if any(ch in pattern for ch in "*?[]"):
        return tuple(
            p.resolve().relative_to(root).as_posix()
            for p in sorted(root.glob(pattern))
            if p.is_file()
        )
    return (pattern,) if (root / pattern).is_file() else ()


def _source_for(rel: str, *, root: Path) -> tuple[BundleSource, str]:
    content = (root / rel).read_text(encoding="utf-8")
    encoded = content.encode("utf-8")
    source = BundleSource(
        path=rel,
        sha256=hashlib.sha256(encoded).hexdigest(),
        bytes=len(encoded),
        lines=content.count("\n") + (0 if not content else 1),
    )
    return source, content


def _corpus_hash(sources: tuple[BundleSource, ...]) -> str:
    h = hashlib.sha256()
    for src in sorted(sources, key=lambda s: s.path):
        h.update(src.path.encode("utf-8"))
        h.update(b"\0")
        h.update(src.sha256.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _skill_markdown(
    *,
    family: str,
    description: str,
    sources: tuple[BundleSource, ...],
) -> str:
    lines = [
        f"# {SKILL_PREFIX}-{family}",
        "",
        description.strip() or "Creator Engine support corpus skill.",
        "",
        "Use this skill only for Creator Engine product support answers.",
        "Every answer drawn from this skill must cite one of the source paths below.",
        "If the listed sources do not cover the question, answer exactly: I don't know.",
        "",
        "## Sources",
        "",
    ]
    for src in sources:
        lines.append(f"- `{src.path}` (sha256 `{src.sha256}`)")
    lines.append("")
    return "\n".join(lines)


def build_support_bundle(*, repo_root: Path | None = None) -> SupportBundle:
    """Project the eligible support corpus into stable docs-as-skills entries."""
    root = (repo_root or support_corpus.repo_root()).resolve()
    eligibility = support_corpus.evaluate(repo_root=root)
    eligible = set(eligibility.eligible)
    manifest = support_corpus.load_manifest()
    families = manifest.get("families") or {}

    skills: list[SkillEntry] = []
    all_sources: list[BundleSource] = []
    claimed: set[str] = set()

    for family, meta in families.items():
        family_name = str(family).strip()
        if not family_name:
            continue
        description = str((meta or {}).get("description") or "").strip()
        family_sources: list[BundleSource] = []
        files: list[tuple[str, str]] = []

        for pattern in (meta or {}).get("serve") or []:
            for rel in _expand_pattern(str(pattern), root=root):
                if rel not in eligible or rel in claimed:
                    continue
                claimed.add(rel)
                source, content = _source_for(rel, root=root)
                family_sources.append(source)
                all_sources.append(source)
                files.append((f"sources/{rel}", content))

        if family_sources:
            sources_tuple = tuple(sorted(family_sources, key=lambda s: s.path))
            skill_name = f"{SKILL_PREFIX}-{family_name}"
            skills.append(
                SkillEntry(
                    name=skill_name,
                    family=family_name,
                    description=description,
                    sources=sources_tuple,
                    skill_md=_skill_markdown(
                        family=family_name,
                        description=description,
                        sources=sources_tuple,
                    ),
                    files=tuple(sorted(files)),
                )
            )

    return SupportBundle(
        version=BUNDLE_VERSION,
        corpus_sha256=_corpus_hash(tuple(all_sources)),
        skills=tuple(skills),
        eligible_paths=eligibility.eligible,
        rejected=eligibility.rejected,
        missing=eligibility.missing,
    )


__all__ = [
    "BUNDLE_VERSION",
    "BundleSource",
    "SkillEntry",
    "SupportBundle",
    "build_support_bundle",
]
