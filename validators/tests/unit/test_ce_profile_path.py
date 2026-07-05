"""Unit coverage for the CE-marked shell-profile PATH writer."""

from __future__ import annotations

import os
import shlex
import subprocess
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


def test_dynamic_profile_path_uses_npm_prefix_with_directory_guard():
    block = ce_profile_path.build_path_block()

    assert "npm prefix -g" in block
    assert "bin -g" not in block
    assert '[ -d "$1" ] || return 0' in block
    assert '_ce_path_prepend "$_ce_npm_bin"' in block
    assert "[[:space:]]" not in block


def test_profile_path_rewrites_previous_dynamic_npm_block(tmp_path: Path):
    profile = tmp_path / ".profile"
    profile.write_text(
        "before\n"
        f"{ce_profile_path.BEGIN_MARKER}\n"
        "if command -v npm >/dev/null 2>&1; then\n"
        '  _ce_npm_bin="$(npm ' + 'bin -g 2>/dev/null || true)"\n'
        '  [ -z "$_ce_npm_bin" ] || _ce_path_prepend "$_ce_npm_bin"\n'
        "fi\n"
        f"{ce_profile_path.END_MARKER}\n"
        "after\n",
        encoding="utf-8",
    )

    result = ce_profile_path.ensure_profile_path_block(profile)

    text = profile.read_text(encoding="utf-8")
    assert result.changed is True
    assert text.startswith("before\n")
    assert text.endswith("after\n")
    assert "npm prefix -g" in text
    assert "bin -g" not in text
    assert text.count(ce_profile_path.BEGIN_MARKER) == 1
    assert text.count(ce_profile_path.END_MARKER) == 1


def test_npm_stdout_error_does_not_pollute_path(tmp_path: Path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    npm = fake_bin / "npm"
    npm.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' 'Unknown command: \"bin\"'\n"
        "exit 1\n",
        encoding="utf-8",
    )
    npm.chmod(0o755)

    profile = tmp_path / ".profile"
    ce_profile_path.ensure_profile_path_block(profile)

    original_path = os.pathsep.join((str(fake_bin), "/usr/bin", "/bin"))
    script = (
        f"HOME={shlex.quote(str(tmp_path))}; "
        f"PATH={shlex.quote(original_path)}; "
        f". {shlex.quote(str(profile))}; "
        'printf "%s" "$PATH"'
    )
    result = subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == original_path
    assert "Unknown command" not in result.stdout


def test_npm_plain_garbage_token_does_not_pollute_path(tmp_path: Path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    npm = fake_bin / "npm"
    npm.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' 'ENOTSUP'\n"
        "exit 1\n",
        encoding="utf-8",
    )
    npm.chmod(0o755)

    profile = tmp_path / ".profile"
    ce_profile_path.ensure_profile_path_block(profile)

    original_path = os.pathsep.join((str(fake_bin), "/usr/bin", "/bin"))
    script = (
        f"HOME={shlex.quote(str(tmp_path))}; "
        f"PATH={shlex.quote(original_path)}; "
        f". {shlex.quote(str(profile))}; "
        'printf "%s" "$PATH"'
    )
    result = subprocess.run(
        ["sh", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == original_path
    assert "ENOTSUP" not in result.stdout
