from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from creator_engine_validator.checks import portability_plane as guard


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_tracked(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", "--", rel)
    return path


def _write_manifest(
    repo: Path,
    *,
    runtime_paths: list[str] | None = None,
    baseline_exemptions: list[dict[str, str]] | None = None,
) -> None:
    payload = {
        "portability_plane": {
            "runtime_plane_paths": runtime_paths or [],
            "baseline_exemptions": baseline_exemptions or [],
        }
    }
    _write_tracked(repo, guard.MANIFEST.as_posix(), yaml.safe_dump(payload, sort_keys=False))


def _make_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _write_tracked(tmp_path, "validators/creator_engine_validator/__init__.py", "")
    _write_manifest(tmp_path)
    return tmp_path


def _error_text(result) -> str:
    return "\n".join(error.format() for error in result.errors)


def test_guard_catches_forbidden_patterns_in_control_plane_module(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(
        repo,
        "validators/creator_engine_validator/new_control.py",
        '''"""Docstring may mention systemd and /run/ without tripping the guard."""

# Comments may mention systemctl, socket.AF_UNIX, and /dev/shm/ too.
import systemd
import sdnotify
import socket
from pathlib import Path

sock = socket.socket(socket.AF_UNIX)
run_dir = "/run/creator-engine"
shm_dir = Path("/dev/shm/creator-engine")
cmd = ["systemctl status ce"]
''',
    )

    result = guard.run([repo])

    assert not result.ok
    rendered = _error_text(result)
    assert "systemd or sdnotify reference" in rendered
    assert "literal /run path" in rendered
    assert "literal /dev/shm path" in rendered
    assert "socket.AF_UNIX usage" in rendered
    assert "runtime-only subprocess command" in rendered
    assert "Docstring may mention systemd" not in rendered
    assert "Comments may mention systemctl" not in rendered


def test_runtime_plane_manifested_module_passes_through(tmp_path: Path):
    repo = _make_repo(tmp_path)
    rel = "validators/creator_engine_validator/runtime_only.py"
    _write_manifest(repo, runtime_paths=[rel])
    _write_tracked(
        repo,
        rel,
        'import socket\npath = "/run/creator-engine.sock"\nsock = socket.socket(socket.AF_UNIX)\n',
    )

    result = guard.run([repo])

    assert result.ok, _error_text(result)


def test_undeclared_new_module_fails_closed(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(
        repo,
        "validators/creator_engine_validator/new_module.py",
        'runtime_socket = "/run/creator-engine.sock"\n',
    )

    result = guard.run([repo])

    assert not result.ok
    assert "new_module.py:1" in _error_text(result)


def test_baseline_exemption_is_honored_and_counted(tmp_path: Path):
    repo = _make_repo(tmp_path)
    rel = "validators/creator_engine_validator/legacy_control.py"
    line = 'HELP = "systemd-run wraps legacy runtime seats"\n'
    _write_manifest(
        repo,
        baseline_exemptions=[
            {
                "path": rel,
                "pattern": "systemd-reference",
                "match": line.strip(),
                "date": "2026-07-04",
                "reason": "Existing control-plane help text pending a portability cleanup slice.",
            }
        ],
    )
    _write_tracked(repo, rel, line)

    result = guard.run([repo])

    assert result.ok, _error_text(result)
    assert any("portability baseline exemptions: 1" in warning.message for warning in result.warnings)
