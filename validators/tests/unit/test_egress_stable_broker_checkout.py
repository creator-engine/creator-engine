from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT = Path("tools/egress-broker/update-stable-broker-checkout.sh")


def _run_script(repo_root: Path, *args: str, env: dict[str, str] | None = None):
    script = repo_root / SCRIPT
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=repo_root,
        env={**os.environ, **(env or {})},
        check=False,
        capture_output=True,
        text=True,
    )


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(path: Path) -> str:
    path.mkdir(parents=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "test@example.invalid")
    _git(path, "config", "user.name", "CE Test")
    (path / "README.md").write_text("stable\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    return _git(path, "rev-parse", "HEAD").stdout.strip()


def test_update_stable_broker_checkout_is_idempotent_for_verified_pin(
    repo_root: Path, tmp_path: Path
):
    upstream = tmp_path / "upstream"
    pin = _init_repo(upstream)
    checkout = tmp_path / "stable"
    subprocess.run(
        ["git", "clone", str(upstream), str(checkout)],
        check=True,
        capture_output=True,
        text=True,
    )

    first = _run_script(repo_root, "--checkout", str(checkout), "--pin", pin)
    second = _run_script(repo_root, "--checkout", str(checkout), "--pin", pin)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert _git(checkout, "rev-parse", "HEAD").stdout.strip() == pin
    assert "stable broker checkout ready" in second.stdout


def test_update_stable_broker_checkout_refuses_missing_target(repo_root: Path, tmp_path: Path):
    missing = tmp_path / "missing"
    result = _run_script(repo_root, "--checkout", str(missing), "--pin", "a" * 40)

    assert result.returncode != 0
    assert "stable broker checkout is missing" in result.stderr


def test_update_stable_broker_checkout_refuses_dirty_tree(repo_root: Path, tmp_path: Path):
    checkout = tmp_path / "stable"
    head = _init_repo(checkout)
    (checkout / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = _run_script(repo_root, "--checkout", str(checkout), "--pin", head)

    assert result.returncode != 0
    assert "stable broker checkout is dirty" in result.stderr


def test_update_stable_broker_checkout_refuses_bad_pin_before_fetch(repo_root: Path, tmp_path: Path):
    checkout = tmp_path / "stable"
    _init_repo(checkout)

    result = _run_script(repo_root, "--checkout", str(checkout), "--pin", "not-a-sha")

    assert result.returncode != 0
    assert "pin must be a full 40-character commit SHA" in result.stderr


def test_update_stable_broker_checkout_refuses_seat_worktree_path(repo_root: Path):
    result = _run_script(repo_root, "--checkout", "/workspace/creator-engine", "--pin", "a" * 40)

    assert result.returncode != 0
    assert "seat working tree" in result.stderr
