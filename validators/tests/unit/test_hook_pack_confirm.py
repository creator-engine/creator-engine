"""CC-G-D Ring 0 — unit tests for ``hook_pack_confirm`` (strict TDD).

``confirm_hook_pack`` is the pure-ish predicate that confirms the committed
Claude hook-pack is present, parseable, registered, and that the validator is
reachable — the precondition Ring 0 must satisfy before permitting
``--dangerously-skip-permissions``. It reads ``.claude/`` from a tmp fixture and
takes an injectable ``validator_probe`` so tests never shell out or launch
Claude.
"""
from __future__ import annotations

import json
import stat
from pathlib import Path

from creator_engine_validator import hook_pack_confirm as hpc


def _write_pack(root: Path, *, executable=True, settings_ok=True):
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    settings = root / ".claude" / "settings.json"
    if settings_ok:
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Edit|Write|MultiEdit|Read|Bash",
                                "hooks": [{"type": "command", "command": "x/ce-pretooluse.sh"}],
                            }
                        ],
                        "Stop": [{"hooks": [{"type": "command", "command": "x/ce-stop.sh"}]}],
                    }
                }
            )
        )
    else:
        settings.write_text("{ not json")
    for name in ("ce-hook-common.sh", "ce-pretooluse.sh", "ce-stop.sh"):
        p = hooks / name
        p.write_text("#!/usr/bin/env sh\n")
        if executable:
            p.chmod(p.stat().st_mode | stat.S_IXUSR)


def test_confirm_ok(tmp_path):
    _write_pack(tmp_path)
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: True)
    assert c.confirmed is True
    assert c.present and c.settings_parsed and c.pretooluse_registered
    assert c.stop_registered and c.hooks_executable and c.validator_reachable


def test_confirm_fails_on_missing_pack(tmp_path):
    # No .claude/ at all.
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: True)
    assert c.present is False and c.confirmed is False


def test_confirm_fails_on_unparseable_settings(tmp_path):
    _write_pack(tmp_path, settings_ok=False)
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: True)
    assert c.settings_parsed is False and c.confirmed is False


def test_confirm_fails_on_non_executable_hooks(tmp_path):
    _write_pack(tmp_path, executable=False)
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: True)
    assert c.hooks_executable is False and c.confirmed is False


def test_confirm_fails_on_unreachable_validator(tmp_path):
    _write_pack(tmp_path)
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: False)
    assert c.validator_reachable is False and c.confirmed is False


def test_confirm_fails_when_pretooluse_matcher_incomplete(tmp_path):
    # A PreToolUse matcher missing required tools must not count as registered.
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "x.sh"}]}
                    ],
                    "Stop": [{"hooks": [{"type": "command", "command": "x.sh"}]}],
                }
            }
        )
    )
    for name in ("ce-hook-common.sh", "ce-pretooluse.sh", "ce-stop.sh"):
        p = hooks / name
        p.write_text("#!/usr/bin/env sh\n")
        p.chmod(p.stat().st_mode | stat.S_IXUSR)
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: True)
    assert c.pretooluse_registered is False and c.confirmed is False


def test_confirm_to_dict_is_json_safe(tmp_path):
    _write_pack(tmp_path)
    c = hpc.confirm_hook_pack(tmp_path, validator_probe=lambda: True)
    json.dumps(c.to_dict())
    assert c.to_dict()["confirmed"] is True
