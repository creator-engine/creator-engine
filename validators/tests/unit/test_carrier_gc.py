"""Hermetic tests for the dead carrier-manifest hygiene sweep.

No network and no git are required: liveness is exercised by passing the ref
lists directly to :func:`carrier_gc.sweep`, and the filesystem side uses a
``tmp_path`` carrier directory with an injected remover spy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator import carrier_gc
from creator_engine_validator.checks.path_manifest_fidelity import MANIFEST_DIR, branch_slug


def _write_carrier(manifests_dir: Path, stem: str, *, frontmatter_slug: str | None = None) -> Path:
    manifests_dir.mkdir(parents=True, exist_ok=True)
    path = manifests_dir / f"{stem}.md"
    if frontmatter_slug is not None:
        text = f"---\nslug: {frontmatter_slug}\ndate: 2026-07-18\n---\n\n# carrier {stem}\n"
    else:
        text = f"# PR path manifest — {stem}\n"
    path.write_text(text, encoding="utf-8")
    return path


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path
    manifests_dir = repo_root / MANIFEST_DIR
    manifests_dir.mkdir(parents=True, exist_ok=True)
    return repo_root, manifests_dir


# --------------------------------------------------------------------------
# slug parsing
# --------------------------------------------------------------------------


def test_read_slug_prefers_frontmatter(tmp_path: Path):
    path = _write_carrier(tmp_path, "filename-stem", frontmatter_slug="frontmatter-slug")
    assert carrier_gc.read_carrier_slug(path) == "frontmatter-slug"


def test_read_slug_falls_back_to_stem_when_no_frontmatter(tmp_path: Path):
    path = _write_carrier(tmp_path, "ce38-work-claims")
    assert carrier_gc.read_carrier_slug(path) == "ce38-work-claims"


def test_read_slug_ignores_slug_outside_frontmatter(tmp_path: Path):
    path = tmp_path / "real-stem.md"
    # A ``slug:`` line in the body must NOT be read as frontmatter.
    path.write_text("# body\n\nslug: not-the-frontmatter\n", encoding="utf-8")
    assert carrier_gc.read_carrier_slug(path) == "real-stem"


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------


def test_dead_when_no_ref_matches(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "ce38-work-claims")
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=["main", "some-other-branch"],
        remote_tracking=["main", "another-branch"],
        current_branch="my-current-branch",
    )
    assert [c.slug for c in result.dead] == ["ce38-work-claims"]
    assert result.live == []
    assert result.removed == []  # dry-run default never removes
    dead = result.dead[0]
    assert dead.checked == (
        "refs/heads/ce38-work-claims",
        "refs/remotes/origin/ce38-work-claims",
        "HEAD (current branch)",
    )


def test_live_when_local_branch_matches(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "feature-x")
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=["feature-x"],
        remote_tracking=[],
        current_branch="main",
    )
    assert result.dead == []
    assert [c.slug for c in result.live] == ["feature-x"]
    assert result.live[0].matched_ref == "refs/heads/feature-x"


def test_live_when_remote_tracking_matches(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "feature-y")
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=[],
        remote_tracking=["feature-y"],
        current_branch="main",
    )
    assert result.dead == []
    assert result.live[0].matched_ref == "refs/remotes/origin/feature-y"


def test_live_when_current_branch_matches(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "ce-547-carrier-hygiene-sweep")
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=[],
        remote_tracking=[],
        current_branch="ce-547-carrier-hygiene-sweep",
    )
    assert result.dead == []
    assert "checked-out branch" in result.live[0].matched_ref


def test_live_when_branch_slug_projection_matches(tmp_path: Path):
    # A branch name that slugifies to the carrier stem keeps it LIVE even when
    # the raw name differs (carriers are named ``branch_slug(branch).md``).
    branch = "Feature/Big_Thing"
    slug = branch_slug(branch)
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, slug)
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=[branch],
        remote_tracking=[],
        current_branch="main",
    )
    assert result.dead == []
    assert [c.slug for c in result.live] == [slug]


def test_frontmatter_slug_used_for_liveness(tmp_path: Path):
    # Liveness keys on the frontmatter slug, not the filename stem.
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "old-filename", frontmatter_slug="live-branch")
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=["live-branch"],
        remote_tracking=[],
        current_branch="main",
    )
    assert result.dead == []
    assert [c.slug for c in result.live] == ["live-branch"]


# --------------------------------------------------------------------------
# apply / removal
# --------------------------------------------------------------------------


def test_apply_removes_only_dead(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    dead = _write_carrier(manifests_dir, "dead-carrier")
    live = _write_carrier(manifests_dir, "live-carrier")
    removed: list[Path] = []

    def _spy(p: Path) -> None:
        removed.append(p)
        p.unlink()

    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=["live-carrier"],
        remote_tracking=[],
        current_branch="main",
        apply=True,
        remover=_spy,
    )
    assert result.removed == [f"{MANIFEST_DIR}/dead-carrier.md"]
    assert removed == [dead]
    assert not dead.exists()
    assert live.exists()


def test_dry_run_never_removes(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    dead = _write_carrier(manifests_dir, "dead-carrier")
    calls: list[Path] = []
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=[],
        remote_tracking=[],
        current_branch="main",
        apply=False,
        remover=lambda p: calls.append(p),
    )
    assert result.dead and result.removed == []
    assert calls == []
    assert dead.exists()


def test_removal_error_is_collected_not_raised(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "dead-carrier")

    def _boom(_path: Path) -> None:
        raise OSError("permission denied")

    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=[],
        remote_tracking=[],
        current_branch="main",
        apply=True,
        remover=_boom,
    )
    assert result.removed == []
    assert result.errors and "permission denied" in result.errors[0]


def test_empty_directory_is_a_clean_noop(tmp_path: Path):
    repo_root, _ = _repo(tmp_path)
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=[],
        remote_tracking=[],
        current_branch="main",
    )
    assert result.all == []


def test_missing_directory_is_a_clean_noop(tmp_path: Path):
    repo_root = tmp_path
    result = carrier_gc.sweep(
        repo_root=repo_root,
        manifests_dir=repo_root / "does-not-exist",
        local_branches=[],
        remote_tracking=[],
        current_branch="main",
    )
    assert result.all == []


# --------------------------------------------------------------------------
# the two named carriers this ticket removes (ce38 / ce57)
# --------------------------------------------------------------------------


def test_named_ticket_carriers_classified_dead_when_refs_absent(tmp_path: Path):
    repo_root, manifests_dir = _repo(tmp_path)
    _write_carrier(manifests_dir, "ce38-work-claims")
    _write_carrier(manifests_dir, "ce57-datebomb-fix")
    result = carrier_gc.sweep(
        repo_root=repo_root,
        local_branches=["main"],
        remote_tracking=["main"],
        current_branch="ce-547-carrier-hygiene-sweep",
    )
    assert sorted(c.slug for c in result.dead) == ["ce38-work-claims", "ce57-datebomb-fix"]
