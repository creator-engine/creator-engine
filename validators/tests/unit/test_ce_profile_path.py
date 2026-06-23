"""Unit coverage for the CE-marked shell-profile PATH writer."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator import ce_profile_path


def test_profile_path_adds_managed_block_once(tmp_path: Path):
    profile = tmp_path / ".profile"
    result = ce_profile_path.ensure_profile_path_block(
        profile,
        npm_global_bin="/tmp/npm/bin",
    )

    assert result.changed is True
    text = profile.read_text(encoding="utf-8")
    assert text.count(ce_profile_path.BEGIN_MARKER) == 1
    assert text.count(ce_profile_path.END_MARKER) == 1
    assert "$HOME/.local/bin" in text
    assert "/tmp/npm/bin" in text


def test_profile_path_rerun_is_noop(tmp_path: Path):
    profile = tmp_path / ".profile"
    ce_profile_path.ensure_profile_path_block(profile, npm_global_bin="/tmp/npm/bin")
    first = profile.read_text(encoding="utf-8")

    result = ce_profile_path.ensure_profile_path_block(profile, npm_global_bin="/tmp/npm/bin")

    assert result.changed is False
    assert profile.read_text(encoding="utf-8") == first


def test_profile_path_preserves_non_ce_lines(tmp_path: Path):
    profile = tmp_path / ".profile"
    profile.write_text("export KEEP=1\nalias ll='ls -l'\n", encoding="utf-8")

    ce_profile_path.ensure_profile_path_block(profile, npm_global_bin="/tmp/npm/bin")

    text = profile.read_text(encoding="utf-8")
    assert text.startswith("export KEEP=1\nalias ll='ls -l'\n")
    assert "export KEEP=1\nalias ll='ls -l'\n" in text


def test_profile_path_replaces_existing_managed_block_only(tmp_path: Path):
    profile = tmp_path / ".profile"
    profile.write_text(
        "before\n"
        f"{ce_profile_path.BEGIN_MARKER}\n"
        "export PATH=/old/ce/path:$PATH\n"
        f"{ce_profile_path.END_MARKER}\n"
        "after\n",
        encoding="utf-8",
    )

    result = ce_profile_path.ensure_profile_path_block(
        profile,
        npm_global_bin="/new/npm/bin",
    )

    text = profile.read_text(encoding="utf-8")
    assert result.changed is True
    assert text.startswith("before\n")
    assert text.endswith("after\n")
    assert "/old/ce/path" not in text
    assert "/new/npm/bin" in text
    assert text.count(ce_profile_path.BEGIN_MARKER) == 1
    assert text.count(ce_profile_path.END_MARKER) == 1
