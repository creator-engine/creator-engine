"""Dead carrier-manifest hygiene sweep (``ce carrier gc``).

Carrier manifests live under ``.ce/pr-manifests/<slug>.md`` (the
per-PR carrier convention). When a PR merges (or its branch is deleted) the
carrier stays behind forever, so the directory accretes dead files that no
longer correspond to any branch. This module classifies each carrier and,
optionally, removes the dead ones.

Liveness rule (conservative — a carrier is only DEAD when nothing matches):

    A carrier with slug ``S`` is DEAD iff **none** of the following match ``S``:
      * a local branch (``refs/heads/<S>``),
      * a remote-tracking ref (``refs/remotes/origin/<S>``),
      * the currently checked-out branch.

    Matching is against both a ref's raw short name **and** its canonical
    ``branch_slug()`` projection, because carriers are named
    ``<branch_slug(branch)>.md``. Anything that matches keeps the carrier LIVE.

    A carrier whose slug cannot be parsed at all is reported ``UNPARSEABLE`` and
    is **never** deleted.

Egress note: this sweep never contacts ``origin``. It reads only the local
remote-tracking refs (``refs/remotes/origin/*``) as they were last fetched, so
an operator should ``git fetch --prune`` first for the remote-tracking view to
reflect the true upstream state before running ``--apply``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .checks.path_manifest_fidelity import MANIFEST_DIR, branch_slug

DEAD = "DEAD"
LIVE = "LIVE"
UNPARSEABLE = "UNPARSEABLE"

# ``slug:`` frontmatter key, matched only inside the leading ``---`` block.
_FRONTMATTER_SLUG_RE = re.compile(r"^slug:\s*(?P<slug>\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class CarrierClassification:
    """One carrier's liveness verdict with its supporting evidence."""

    path: str  # repo-relative POSIX path
    slug: str | None
    status: str  # DEAD | LIVE | UNPARSEABLE
    matched_ref: str | None = None  # which ref kept a LIVE carrier alive
    checked: tuple[str, ...] = ()  # probes performed (evidence)
    detail: str = ""


@dataclass
class SweepResult:
    """Aggregate outcome of a sweep."""

    dead: list[CarrierClassification] = field(default_factory=list)
    live: list[CarrierClassification] = field(default_factory=list)
    unparseable: list[CarrierClassification] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all(self) -> list[CarrierClassification]:
        return [*self.dead, *self.live, *self.unparseable]


def _frontmatter_block(text: str) -> str:
    """Return the text between the leading ``---`` fences, or ``""`` when none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(body)
        body.append(line)
    # Unterminated frontmatter — treat as absent so we fall back to the stem.
    return ""


def _stem(path: Path) -> str:
    name = path.name
    return name[:-3] if name.endswith(".md") else name


def read_carrier_slug(path: Path) -> str | None:
    """Return a carrier's slug.

    Prefer a non-empty ``slug:`` frontmatter value; otherwise fall back to the
    filename stem. Returns ``None`` only when neither is derivable (an unreadable
    file with no usable name, or an empty stem) so the caller can classify the
    carrier ``UNPARSEABLE`` and refuse to delete it.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _stem(path) or None
    match = _FRONTMATTER_SLUG_RE.search(_frontmatter_block(text))
    if match:
        slug = match.group("slug").strip()
        if slug:
            return slug
    return _stem(path) or None


def _slug_variants(name: str) -> set[str]:
    """A ref name maps to itself and to its canonical ``branch_slug`` projection."""
    variants = {name}
    try:
        variants.add(branch_slug(name))
    except Exception:  # pragma: no cover - branch_slug is total, defensive only
        pass
    return variants


def live_slug_index(
    local_branches: Iterable[str],
    remote_tracking: Iterable[str],
    current_branch: str | None,
) -> dict[str, str]:
    """Map every live slug variant to a human description of its source ref.

    ``remote_tracking`` entries are the origin branch names **without** the
    ``origin/`` prefix (e.g. ``feature-x``, not ``origin/feature-x``).
    """
    index: dict[str, str] = {}

    def _add(name: str, describe: Callable[[str], str]) -> None:
        for variant in _slug_variants(name):
            index.setdefault(variant, describe(name))

    for name in local_branches:
        if name:
            _add(name, lambda n: f"refs/heads/{n}")
    for name in remote_tracking:
        if name:
            _add(name, lambda n: f"refs/remotes/origin/{n}")
    if current_branch:
        _add(current_branch, lambda n: f"HEAD (checked-out branch {n})")
    return index


def classify(
    path_rel: str,
    slug: str | None,
    live_index: dict[str, str],
) -> CarrierClassification:
    """Classify a single carrier against the live-slug index."""
    if slug is None:
        return CarrierClassification(
            path=path_rel,
            slug=None,
            status=UNPARSEABLE,
            detail="slug could not be parsed (no frontmatter slug and empty filename stem)",
        )
    checked = (
        f"refs/heads/{slug}",
        f"refs/remotes/origin/{slug}",
        "HEAD (current branch)",
    )
    matched = live_index.get(slug)
    if matched is not None:
        return CarrierClassification(
            path=path_rel,
            slug=slug,
            status=LIVE,
            matched_ref=matched,
            checked=checked,
        )
    return CarrierClassification(
        path=path_rel,
        slug=slug,
        status=DEAD,
        checked=checked,
        detail="no local branch, no remote-tracking origin ref, and not the current branch",
    )


def enumerate_carriers(manifests_dir: Path) -> list[Path]:
    """Every ``*.md`` carrier under ``manifests_dir`` (sorted, files only)."""
    if not manifests_dir.is_dir():
        return []
    return sorted(p for p in manifests_dir.glob("*.md") if p.is_file())


def _default_remover(path: Path) -> None:
    path.unlink()


def sweep(
    *,
    repo_root: Path,
    local_branches: Sequence[str],
    remote_tracking: Sequence[str],
    current_branch: str | None,
    manifests_dir: Path | None = None,
    apply: bool = False,
    remover: Callable[[Path], None] | None = None,
) -> SweepResult:
    """Classify every carrier and, when ``apply`` is set, remove the dead ones.

    ``remover`` defaults to ``Path.unlink``; tests inject a spy. Live and
    unparseable carriers are never passed to the remover. Removal failures are
    collected in :attr:`SweepResult.errors` and do not abort the sweep.
    """
    repo_root = repo_root.resolve()
    if manifests_dir is None:
        manifests_dir = repo_root / MANIFEST_DIR
    remove = remover or _default_remover
    index = live_slug_index(local_branches, remote_tracking, current_branch)
    result = SweepResult()

    for path in enumerate_carriers(manifests_dir):
        try:
            rel = path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        slug = read_carrier_slug(path)
        verdict = classify(rel, slug, index)
        if verdict.status == DEAD:
            result.dead.append(verdict)
        elif verdict.status == UNPARSEABLE:
            result.unparseable.append(verdict)
        else:
            result.live.append(verdict)

    if apply:
        for verdict in result.dead:
            target = repo_root / verdict.path
            try:
                remove(target)
            except OSError as exc:
                result.errors.append(f"{verdict.path}: could not remove ({exc})")
            else:
                result.removed.append(verdict.path)

    return result
