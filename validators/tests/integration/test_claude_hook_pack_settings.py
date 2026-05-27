"""Integration tests for the committed CC-G-C hook-pack settings + scripts.

Validates the static shape of ``.claude/settings.json`` and the
``.claude/hooks/*.sh`` scripts that register the Ring 1 hook-pack: PreToolUse
covers exactly the governed tool set, the Stop advisory hook is present, hook
commands point at scripts that exist on disk, the scripts are executable POSIX
sh, and there are no posture-sensitive blanket ``permissions.deny`` rules
(D-decisions keep enforcement in the validator, not in static denies). Also
checks the D4 ``.gitignore`` rule for ``.claude/settings.local.json``.
"""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS = REPO_ROOT / ".claude/settings.json"
HOOKS_DIR = REPO_ROOT / ".claude/hooks"

EXPECTED_PRETOOLUSE_TOOLS = {"Edit", "Write", "MultiEdit", "Read", "Bash"}


def _load():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def _all_hook_commands(data):
    commands = []
    for entries in data["hooks"].values():
        for entry in entries:
            for hook in entry["hooks"]:
                commands.append(hook)
    return commands


def test_settings_json_parses():
    data = _load()
    assert isinstance(data, dict)
    assert "hooks" in data


def test_pretooluse_matcher_covers_exact_tool_set():
    data = _load()
    pre = data["hooks"]["PreToolUse"]
    assert len(pre) == 1
    tools = set(pre[0]["matcher"].split("|"))
    assert tools == EXPECTED_PRETOOLUSE_TOOLS


def test_stop_advisory_hook_present():
    data = _load()
    assert "Stop" in data["hooks"]
    stop_commands = [
        h["command"] for entry in data["hooks"]["Stop"] for h in entry["hooks"]
    ]
    assert any("ce-stop.sh" in c for c in stop_commands)


def test_hook_commands_are_command_type_and_reference_existing_scripts():
    data = _load()
    hooks = _all_hook_commands(data)
    assert hooks, "expected at least one registered hook command"
    for hook in hooks:
        assert hook["type"] == "command"
        rel = hook["command"].replace("$CLAUDE_PROJECT_DIR/", "")
        assert (REPO_ROOT / rel).is_file(), hook["command"]
    joined = " ".join(h["command"] for h in hooks)
    assert "ce-pretooluse.sh" in joined
    assert "ce-stop.sh" in joined


def test_hook_scripts_are_executable_posix_sh():
    scripts = sorted(HOOKS_DIR.glob("*.sh"))
    assert scripts, "expected hook scripts under .claude/hooks"
    for script in scripts:
        mode = stat.S_IMODE(script.stat().st_mode)
        assert mode == 0o755, (str(script), oct(mode))
        first_line = script.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == "#!/usr/bin/env sh", (str(script), first_line)


def test_hook_scripts_pass_sh_syntax_check():
    for script in sorted(HOOKS_DIR.glob("*.sh")):
        proc = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)
        assert proc.returncode == 0, (str(script), proc.stderr)


def test_no_blanket_permission_deny_rules():
    data = _load()
    permissions = data.get("permissions", {})
    assert not permissions.get("deny"), permissions


def test_settings_local_json_is_gitignored_without_weakening_hermes():
    # D4: the committed repo .gitignore — not just a developer's global ignore —
    # must ignore the local-override source so it cannot silently weaken the
    # committed pack on a fresh clone, while the .hermes/ rule stays intact.
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    patterns = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}
    assert ".claude/settings.local.json" in patterns, patterns
    assert ".hermes/" in patterns, patterns
