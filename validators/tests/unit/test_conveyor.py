from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from creator_engine_validator.conveyor import ConveyorCommandResult, ConveyorHarvestSpec, prepare_harvest


class FakeGit:
    def __init__(self, current_branch: str = "Feature/Test", diff: str = "validators/creator_engine_validator/conveyor.py\n"):
        self.current_branch = current_branch
        self.diff = diff
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args: Sequence[str], cwd: Path) -> ConveyorCommandResult:
        self.calls.append(tuple(args))
        if tuple(args) == ("branch", "--show-current"):
            return ConveyorCommandResult(0, f"{self.current_branch}\n", "")
        if tuple(args) == ("branch", "-m", "feature-test"):
            self.current_branch = "feature-test"
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("fetch", "origin", "main"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("rebase", "origin/main"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("merge-base", "--is-ancestor", "origin/main", "HEAD"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("diff", "--name-only", "--find-renames", "origin/main..HEAD"):
            return ConveyorCommandResult(0, self.diff, "")
        return ConveyorCommandResult(1, "", f"unexpected git call: {args}")


class FakeValidate:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.calls: list[tuple[tuple[str, ...], Path, Mapping[str, str] | None]] = []

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None,
    ) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd, env))
        (cwd / "validators" / "build").mkdir(parents=True, exist_ok=True)
        return ConveyorCommandResult(self.returncode, "ok\n", "" if self.returncode == 0 else "failed\n")


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "validators" / "build").mkdir(parents=True)
    (root / "validators" / "creator_engine_validator").mkdir(parents=True)
    (root / "validators" / "old.egg-info").mkdir()
    return root


def test_prepare_harvest_renames_branch_cleans_artifacts_writes_carriers_and_validates(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit()
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(
            worktree_path=root,
            branch="Feature/Test",
            issue="ce-ops#1",
            title="Conveyor harvest",
            body="- Added conveyor helper.",
            carrier_date="2026-06-30",
        ),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is True
    assert result.reasons == ()
    assert result.branch_slug == "feature-test"
    assert result.removed_artifacts == ("validators/build", "validators/old.egg-info")
    assert git.calls == [
        ("branch", "--show-current"),
        ("branch", "-m", "feature-test"),
        ("fetch", "origin", "main"),
        ("rebase", "origin/main"),
        ("diff", "--name-only", "--find-renames", "origin/main..HEAD"),
    ]
    assert validate.calls == [
        (
            (
                "python",
                "-m",
                "creator_engine_validator.ce_cli",
                "validate-pr",
                "--repo-root",
                str(root),
                "--base",
                "origin/main",
                "--declared-work-class",
                "story",
                "--head-ref",
                "feature-test",
                "--allow-dirty",
            ),
            root,
            {"PYTHONPATH": str(root / "validators"), "TMPDIR": "/var/tmp"},
        )
    ]
    assert not (root / "validators" / "build").exists()
    assert result.changelog_path == root / ".ce" / "changelog" / "feature-test.md"
    assert result.manifest_path == root / ".ce" / "pr-manifests" / "feature-test.md"
    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert "- **Declared work class:** story\n" in manifest
    assert "validators/creator_engine_validator/conveyor.py" in manifest


def test_prepare_harvest_refuses_unexpected_current_branch_before_mutation(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="other-branch")
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(worktree_path=root, branch="Feature/Test"),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is False
    assert result.reasons == ("current branch 'other-branch' is neither requested branch 'Feature/Test' nor slug 'feature-test'",)
    assert git.calls == [("branch", "--show-current")]
    assert validate.calls == []


def test_prepare_harvest_validation_failure_is_not_ready_and_post_cleans(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="feature-test")
    validate = FakeValidate(returncode=2)

    result = prepare_harvest(
        ConveyorHarvestSpec(worktree_path=root, branch="Feature/Test"),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is False
    assert result.validation_returncode == 2
    assert result.reasons == ("validate-pr failed: failed",)
    assert not (root / "validators" / "build").exists()


def test_prepare_harvest_can_verify_base_without_rebase(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="feature-test")
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(worktree_path=root, branch="Feature/Test", rebase=False, refresh_base=False),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is True
    assert ("rebase", "origin/main") not in git.calls
    assert ("merge-base", "--is-ancestor", "origin/main", "HEAD") in git.calls
