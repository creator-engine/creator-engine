"""Fast tests for contained-launch pre-spawn policy validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.launch_runtime import (
    ContainedLaunchPreflightRefused,
    _validate_contained_launch_plan,
)


pytestmark = pytest.mark.fast

_VALID_DIGEST = "sha256:" + "a" * 64
_ZERO_DIGEST = "sha256:" + "0" * 64


def _make_policy(
    *,
    sha: str = _VALID_DIGEST,
    mounts: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "kind": "runtime-policy-record",
        "policy_id": "test-policy",
        "image_ref": {"name": "ghcr.io/test/ce-seat", "sha": sha},
        "mount_manifest": mounts if mounts is not None else [],
    }


def test_zero_digest_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    policy = _make_policy(sha=_ZERO_DIGEST, mounts=[{"path": str(tmp_path), "mode": "rw"}])

    with pytest.raises(ContainedLaunchPreflightRefused, match="placeholder"):
        _validate_contained_launch_plan(policy, sentinel)


def test_valid_digest_passes(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    policy = _make_policy(mounts=[{"path": str(tmp_path), "mode": "rw"}])

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert updated["image_ref"]["sha"] == _VALID_DIGEST
    assert warnings == []


def test_absent_optional_dotfile_skipped(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_dir = str(tmp_path / "home" / "user" / ".claude")
    policy = _make_policy(
        mounts=[
            {"path": str(tmp_path), "mode": "rw"},
            {"path": absent_dir, "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert absent_dir not in [entry["path"] for entry in updated["mount_manifest"]]
    assert any("skipping mount" in warning for warning in warnings)


def test_absent_config_claude_skipped(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_dir = str(tmp_path / "home" / "user" / ".config" / "claude")
    policy = _make_policy(
        mounts=[
            {"path": str(tmp_path), "mode": "rw"},
            {"path": absent_dir, "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert absent_dir not in [entry["path"] for entry in updated["mount_manifest"]]
    assert warnings


def test_absent_required_path_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_required = str(tmp_path / "required" / "workspace")
    policy = _make_policy(
        mounts=[
            {"path": str(tmp_path), "mode": "rw"},
            {"path": absent_required, "mode": "ro"},
        ]
    )

    with pytest.raises(
        ContainedLaunchPreflightRefused,
        match="bind source path does not exist",
    ):
        _validate_contained_launch_plan(policy, sentinel)


def test_sentinel_not_covered_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "other-dir" / "sentinel-wrapper.sh"
    sentinel.parent.mkdir()
    sentinel.touch()
    mounted_dir = tmp_path / "mounted"
    mounted_dir.mkdir()
    policy = _make_policy(mounts=[{"path": str(mounted_dir), "mode": "rw"}])

    with pytest.raises(
        ContainedLaunchPreflightRefused,
        match="not under any mounted source",
    ):
        _validate_contained_launch_plan(policy, sentinel)


def test_sentinel_covered_passes(tmp_path: Path) -> None:
    mounted_dir = tmp_path / "repo"
    mounted_dir.mkdir()
    sentinel = mounted_dir / ".ce" / "state" / "sentinel-wrapper.sh"
    sentinel.parent.mkdir(parents=True)
    sentinel.touch()
    policy = _make_policy(mounts=[{"path": str(mounted_dir), "mode": "rw"}])

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert len(updated["mount_manifest"]) == 1
    assert warnings == []


def test_returned_policy_excludes_absent_optional_mounts(tmp_path: Path) -> None:
    present = tmp_path / "present"
    present.mkdir()
    sentinel = present / "sentinel-wrapper.sh"
    sentinel.touch()
    absent_optional = str(tmp_path / "some" / "path" / ".codex")
    policy = _make_policy(
        mounts=[
            {"path": str(present), "mode": "ro"},
            {"path": absent_optional, "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert updated["mount_manifest"] == [{"path": str(present), "mode": "ro"}]
    assert warnings


def test_empty_mount_manifest_refused(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel-wrapper.sh"
    policy = _make_policy(mounts=[])

    with pytest.raises(
        ContainedLaunchPreflightRefused,
        match="not under any mounted source",
    ):
        _validate_contained_launch_plan(policy, sentinel)


def test_no_warnings_when_all_mounts_present(tmp_path: Path) -> None:
    mounted = tmp_path / "workspace"
    mounted.mkdir()
    sentinel = mounted / "sentinel-wrapper.sh"
    sentinel.touch()
    codex_config = tmp_path / "home" / "user" / ".config" / "codex"
    codex_config.mkdir(parents=True)
    policy = _make_policy(
        mounts=[
            {"path": str(mounted), "mode": "rw"},
            {"path": str(codex_config), "mode": "ro"},
        ]
    )

    updated, warnings = _validate_contained_launch_plan(policy, sentinel)

    assert len(updated["mount_manifest"]) == 2
    assert warnings == []
