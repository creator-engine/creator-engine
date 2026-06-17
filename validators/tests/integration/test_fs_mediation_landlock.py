"""Live integration proof for Ring-1 Section-8c Landlock credential read-deny.

These tests apply a REAL Landlock read-confinement to a launched subprocess (the
runner-subprocess model: confinement applied at launch via ``preexec_fn``, the
launched process cannot opt out) and assert BOTH directions:

* DENY — a runner-launched process reading an out-of-workspace ``.env`` /
  ``~/.ssh/id_rsa`` / ``~/.aws/credentials`` is blocked by the kernel.
* ALLOW (regression) — normal workspace source reads still succeed, and
  ``git status`` / ``git add`` in the runner's workspace are unaffected.

Gated on real Landlock availability so the suite stays green on a host/kernel
without Landlock (where the unit tests already cover the honest fail-closed
fallback).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from creator_engine_validator import fs_mediation as fm

pytestmark = pytest.mark.skipif(
    not fm.fs_mediation_available(),
    reason="Landlock not available on this host; honest fail-closed fallback is "
    "covered by tests/unit/test_fs_mediation.py",
)


def _read_probe(target: str) -> str:
    """A tiny child program: try to read ``target``, print READ_OK / Denied."""
    return textwrap.dedent(
        f"""
        try:
            with open({target!r}) as fh:
                fh.read()
            print("READ_OK")
        except PermissionError:
            print("DENIED")
        except FileNotFoundError:
            print("MISSING")
        """
    )


def _make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """A workspace root (allow-listed) and an out-of-workspace secret store."""
    work = tmp_path / "workspace"
    work.mkdir()
    (work / "source.py").write_text("VALUE = 42\n", encoding="utf-8")

    secrets = tmp_path / "host-home"
    (secrets / ".ssh").mkdir(parents=True)
    (secrets / ".ssh" / "id_rsa").write_text("-----PRIVATE KEY-----\n", encoding="utf-8")
    (secrets / ".aws").mkdir(parents=True)
    (secrets / ".aws" / "credentials").write_text("[default]\nkey=AKIA\n", encoding="utf-8")
    (secrets / ".env").write_text("API_TOKEN=super-secret\n", encoding="utf-8")
    return work, secrets


def _run_probe(work: Path, target: Path) -> str:
    conf = fm.RunnerFsConfinement(workspace_read_roots=(str(work),))
    result = fm.run_confined(
        [sys.executable, "-c", _read_probe(str(target))],
        conf,
        require_enforcement=True,
        cwd=str(work),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


# --- DENY direction ----------------------------------------------------------

def test_deny_out_of_workspace_dotenv(tmp_path):
    work, secrets = _make_workspace(tmp_path)
    assert _run_probe(work, secrets / ".env") == "DENIED"


def test_caller_preexec_cannot_bypass_out_of_workspace_dotenv_deny(tmp_path):
    work, secrets = _make_workspace(tmp_path)
    secret = secrets / ".env"
    marker = work / "caller-preexec-read"
    conf = fm.RunnerFsConfinement(workspace_read_roots=(str(work),))

    def caller_preexec() -> None:  # pragma: no cover - runs only in forked child
        try:
            fd = os.open(str(secret), os.O_RDONLY)
        except PermissionError:
            outcome = b"DENIED"
        else:
            try:
                os.read(fd, 1)
            finally:
                os.close(fd)
            outcome = b"READ_OK"
        marker_fd = os.open(str(marker), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(marker_fd, outcome)
        finally:
            os.close(marker_fd)

    result = fm.run_confined(
        [sys.executable, "-c", "pass"],
        conf,
        require_enforcement=True,
        cwd=str(work),
        preexec_fn=caller_preexec,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8") == "DENIED"


def test_deny_ssh_private_key(tmp_path):
    work, secrets = _make_workspace(tmp_path)
    assert _run_probe(work, secrets / ".ssh" / "id_rsa") == "DENIED"


def test_deny_aws_credentials(tmp_path):
    work, secrets = _make_workspace(tmp_path)
    assert _run_probe(work, secrets / ".aws" / "credentials") == "DENIED"


# --- ALLOW regression --------------------------------------------------------

def test_allow_workspace_source_read(tmp_path):
    work, _ = _make_workspace(tmp_path)
    assert _run_probe(work, work / "source.py") == "READ_OK"


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_allow_git_status_and_add_in_workspace(tmp_path):
    work, _ = _make_workspace(tmp_path)
    env = dict(os.environ)
    env["HOME"] = str(work)  # the runner's HOME is its sandbox, inside the allow-list
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    subprocess.run(["git", "init", "-q"], cwd=str(work), env=env, check=True)
    subprocess.run(
        ["git", "config", "user.email", "runner@example.invalid"],
        cwd=str(work), env=env, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "runner"], cwd=str(work), env=env, check=True
    )
    (work / "new.txt").write_text("hello\n", encoding="utf-8")

    conf = fm.RunnerFsConfinement(workspace_read_roots=(str(work),))
    preexec = fm.landlock_preexec(conf)

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(work), env=env, preexec_fn=preexec, capture_output=True, text=True,
    )
    assert status.returncode == 0, status.stderr
    assert "new.txt" in status.stdout

    add = subprocess.run(
        ["git", "add", "new.txt"],
        cwd=str(work), env=env, preexec_fn=preexec, capture_output=True, text=True,
    )
    assert add.returncode == 0, add.stderr


# --- honest residual: in-workspace credential file is NOT carved out ---------

def test_in_workspace_dotenv_is_declared_residual_not_landlock_covered(tmp_path):
    """Landlock has no sub-path deny: a ``.env`` planted INSIDE an allowed
    workspace root is still readable under the confinement. This is the honest
    residual the capability declares (covered by the in-band is_secret_path
    hook/shim layer + deferred FUSE/fanotify), proven here so the boundary is
    explicit and ratcheted, not silently assumed closed.
    """
    work, _ = _make_workspace(tmp_path)
    planted = work / ".env"
    planted.write_text("INSIDE=1\n", encoding="utf-8")
    assert _run_probe(work, planted) == "READ_OK"

    # And the declaration names exactly this residual.
    conf = fm.RunnerFsConfinement(workspace_read_roots=(str(work),))
    cap = fm.build_runner_fs_capability(conf, require_enforcement=True)
    assert cap.sandbox_fs_enforced is True
    assert any("INSIDE an allowed read root" in c for c in cap.non_coverage)
