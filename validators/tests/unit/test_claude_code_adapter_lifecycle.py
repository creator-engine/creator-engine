from __future__ import annotations

import json
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from creator_engine_validator.harness_adapters.claude_code_adapter import ClaudeCodeAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]

SIMPLE_LIFECYCLE_METHODS = (
    ("prepare_launch", "prepared"),
    ("seed", "seeded"),
    ("collect", "evidence_collected"),
    ("retire", "retired"),
    ("cleanup_on_failure", "cleaned_up"),
)


def _copy_claude_hook_pack(project_dir: Path) -> None:
    hooks_dir = project_dir / ".claude" / "hooks"
    shutil.copytree(REPO_ROOT / ".claude" / "hooks", hooks_dir)
    for script in hooks_dir.iterdir():
        script.chmod(script.stat().st_mode | stat.S_IXUSR)


def _seed_stop_hook(project_dir: Path) -> None:
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "unrelated": {"preserved": True},
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/ce-stop.sh",
                                }
                            ]
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(("method_name", "status"), SIMPLE_LIFECYCLE_METHODS)
def test_claude_code_lifecycle_methods_return_mapping_with_none(
    method_name: str, status: str
) -> None:
    result = getattr(ClaudeCodeAdapter(), method_name)(None)

    assert isinstance(result, Mapping)
    assert result["harness"] == "claude_code"
    assert result["status"] == status


@pytest.mark.parametrize(("method_name", "status"), SIMPLE_LIFECYCLE_METHODS)
def test_claude_code_lifecycle_methods_merge_context(method_name: str, status: str) -> None:
    result = getattr(ClaudeCodeAdapter(), method_name)({"caller_key": "v"})

    assert result["caller_key"] == "v"
    assert result["harness"] == "claude_code"
    assert result["status"] == status


def test_claude_code_cleanup_on_failure_marks_failure() -> None:
    result = ClaudeCodeAdapter().cleanup_on_failure()

    assert result["failure"] is True


def test_claude_code_spawn_reports_gvisor_integration_pending() -> None:
    result = ClaudeCodeAdapter().spawn()

    assert result["harness"] == "claude_code"
    assert result["status"] == "not_implemented"
    assert "gvisor_spawn_pending" in result["reason"]


def test_claude_code_install_enforcement_writes_and_confirms_hook(tmp_path: Path) -> None:
    _copy_claude_hook_pack(tmp_path)
    _seed_stop_hook(tmp_path)

    result = ClaudeCodeAdapter().install_enforcement({"project_dir": tmp_path, "caller_key": "v"})
    settings_path = Path(result["settings_path"])
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    assert result["caller_key"] == "v"
    assert result["harness"] == "claude_code"
    assert result["status"] == "enforcement_installed"
    assert result["mechanism"] == "pre_tool_use_hook"
    assert result["hook_confirmed"] is True
    assert settings_path.is_file()
    assert settings["unrelated"] == {"preserved": True}
    assert any(
        entry["matcher"] == "Edit|Write|MultiEdit|Read|Bash"
        for entry in settings["hooks"]["PreToolUse"]
    )


def test_claude_code_install_enforcement_requires_project_dir() -> None:
    with pytest.raises(ValueError, match="project_dir required for install_enforcement"):
        ClaudeCodeAdapter().install_enforcement({})


@pytest.mark.parametrize(("method_name", "_status"), SIMPLE_LIFECYCLE_METHODS)
def test_claude_code_all_lifecycle_results_identify_harness(
    method_name: str, _status: str
) -> None:
    result: Mapping[str, Any] = getattr(ClaudeCodeAdapter(), method_name)()

    assert result["harness"] == "claude_code"
