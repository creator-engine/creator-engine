"""Integration proof for runner-owned Ring-1 PATH inheritance.

The command launched through OpenShellBackend is a fake ``codex`` harness. That
child process shells out to ``git push``; the runner-installed PATH shim calls
the real ``hook-check`` CLI, observes governed posture, and denies before the
downstream git binary can execute, even if the child process tries to spoof
posture/ledger environment.
"""

from __future__ import annotations

import os
import pytest
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from creator_engine_validator import fs_mediation as fm
from creator_engine_validator.runner import (
    ExecOutcome,
    OpenShellBackend,
    ProvisionRequest,
    RunRequest,
    SandboxCreateSpec,
)
import creator_engine_validator.runner.ring1_tool_guard as ring1_tool_guard_module
from creator_engine_validator.runner.ring1_tool_guard import (
    DEFAULT_REAL_BINARIES,
    Ring1ToolGuardConfig,
)
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATORS_ROOT = REPO_ROOT / "validators"
_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


@pytest.fixture(autouse=True)
def _local_harness_landlock_runtime(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    monkeypatch.setattr(ring1_tool_guard_module, "landlock_preexec", lambda confinement: None)


class LocalSandboxClient:
    """Test SandboxClient that executes commands in a temp sandbox directory."""

    def __init__(self, sandbox_dir: Path) -> None:
        self.sandbox_dir = sandbox_dir
        self.created_specs: list[SandboxCreateSpec] = []
        self.exec_calls: list[tuple[str, tuple[str, ...]]] = []
        self.exec_environments: list[dict[str, str] | None] = []

    def create_sandbox(self, spec: SandboxCreateSpec) -> str:
        self.created_specs.append(spec)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        return "local-openshell-sandbox"

    def exec_sandbox(
        self,
        sandbox_id: str,
        command: Sequence[str],
        *,
        workdir: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
        preexec_fn: Callable[[], None] | None = None,
    ) -> ExecOutcome:
        self.exec_calls.append((sandbox_id, tuple(command)))
        self.exec_environments.append(dict(environment) if environment is not None else None)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(VALIDATORS_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        if environment:
            env.update(environment)
        completed = subprocess.run(
            list(command),
            cwd=Path(workdir) if workdir else self.sandbox_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            preexec_fn=preexec_fn,
        )
        return ExecOutcome(
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    def collect_evidence(self, sandbox_id: str) -> Sequence[dict[str, Any]]:
        return ()

    def delete_sandbox(self, sandbox_id: str) -> bool:
        return True


def _write_executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _test_real_binaries(*, git: Path, gh: Path, ce: Path) -> tuple[tuple[str, str], ...]:
    real_binaries = dict(DEFAULT_REAL_BINARIES)
    real_binaries.update(
        {
            "git": str(git),
            "gh": str(gh),
            "ce": str(ce),
        }
    )
    return tuple(real_binaries.items())


def _assert_ce_real_binary_is_pinned(
    guard: Ring1ToolGuardConfig,
    *,
    real_ce: Path,
    real_bin: Path,
) -> None:
    ce_real_path = Path(dict(guard.real_binaries)["ce"])

    assert "ce" in guard.tools
    assert ce_real_path == real_ce
    assert ce_real_path.is_absolute()
    assert ce_real_path.exists()
    assert ce_real_path.parent == real_bin
    assert str(real_bin) not in guard.base_path.split(os.pathsep)


def _assert_runner_uses_shims_without_real_bin_path_lookup(
    client: LocalSandboxClient,
    *,
    real_bin: Path,
) -> None:
    run_env = client.exec_environments[-1]
    assert run_env is not None
    path_entries = run_env["PATH"].split(os.pathsep)
    assert Path(path_entries[0], "git").exists()
    assert Path(path_entries[0], "ce").exists()
    assert str(real_bin) not in path_entries


def _write_governed_ledger(root: Path) -> None:
    ledger = root / ".hermes" / "active-work-ledger"
    claims = ledger / "claims" / "hermes-primary"
    panes = ledger / "panes" / "hermes-primary"
    claims.mkdir(parents=True, exist_ok=True)
    panes.mkdir(parents=True, exist_ok=True)
    (claims / "ring1-lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: ring1-lane\n"
        'record_timestamp: "source-controlled:ring1-lane.yaml"\n'
        f"worktree_path: {root.as_posix()}\n"
        "envelope_ref: none\n"
        "lease_seconds: 3600\n"
        'claimed_at: "source-controlled:ring1-lane.yaml"\n'
        'last_heartbeat_at: "source-controlled:ring1-lane.yaml"\n',
        encoding="utf-8",
    )
    (panes / "ring1-lane.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: ring1-lane\n"
        "claim_ref: claims/hermes-primary/ring1-lane.yaml\n"
        "host_id: workstation-a\n"
        "pane_id: pane-ring1-001\n"
        "role: implementer\n"
        "status: active\n"
        'record_timestamp: "2026-06-16T00:00:00Z"\n'
        "visibility: operator_visible\n"
        "terminal:\n"
        "  kind: tmux\n"
        "  session_id: ce\n"
        "  window_id: w\n"
        "  pane_id: '1'\n"
        'registered_at: "2026-06-16T00:00:00Z"\n'
        "last_seen_at: source-controlled:ring1-lane.yaml\n",
        encoding="utf-8",
    )


def _valid_policy() -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "openshell-ring1-integration-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "openshell",
        "image_ref": {"name": "registry.example/creator-engine/implementer", "sha": _IMAGE_SHA},
        "mount_manifest": [
            {"path": "/runtime/worktree", "mode": "rw", "write_justification": "allocated worktree"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "port": 443, "protocol": "https", "assurance": ["l4"]},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


@pytest.mark.parametrize(
    "git_command",
    [
        pytest.param("git push origin main", id="git_plain_push"),
        pytest.param("git -C . push origin main", id="git_global_C_push"),
    ],
)
def test_codex_child_git_command_denied_under_governed_posture(tmp_path, git_command):
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    _write_governed_ledger(sandbox_dir)

    harness_bin = sandbox_dir / "harness-bin"
    real_bin = sandbox_dir / "real-bin"
    harness_bin.mkdir()
    real_bin.mkdir()
    real_git_marker = sandbox_dir / "real-git-ran"
    codex_marker = sandbox_dir / "codex-ran"
    codex_after_marker = sandbox_dir / "codex-after-git"
    attacker_ledger = tmp_path / "attacker-ledger"
    attacker_ledger.mkdir()

    _write_executable(
        harness_bin / "codex",
        f"""#!/usr/bin/env sh
set -eu
printf 'codex child reached\\n' > {codex_marker}
export CE_RING1_POSTURE=ungoverned
export CE_LEDGER_ROOT={attacker_ledger}
{git_command}
printf 'after git\\n' > {codex_after_marker}
""",
    )
    _write_executable(
        real_bin / "git-real",
        f"""#!/usr/bin/env sh
set -eu
printf 'real git reached\\n' > {real_git_marker}
""",
    )
    real_gh = _write_executable(real_bin / "gh-real", "#!/usr/bin/env sh\nexit 0\n")
    real_ce = _write_executable(real_bin / "ce-real", "#!/usr/bin/env sh\nexit 0\n")

    guard = Ring1ToolGuardConfig(
        base_path=f"{harness_bin}:{os.environ.get('PATH', '')}",
        posture_root=str(sandbox_dir),
        extra_read_roots=(str(VALIDATORS_ROOT),),
        real_binaries=_test_real_binaries(
            git=real_bin / "git-real",
            gh=real_gh,
            ce=real_ce,
        ),
        validator_argv=(sys.executable, "-m", "creator_engine_validator"),
    )
    _assert_ce_real_binary_is_pinned(guard, real_ce=real_ce, real_bin=real_bin)
    client = LocalSandboxClient(sandbox_dir)
    backend = OpenShellBackend(client=client, ring1_guard=guard)
    handle = backend.provision(ProvisionRequest(runtime_policy=_valid_policy(), run_id="ring1-codex"))

    result = backend.run(handle, RunRequest(command=("codex",)))

    assert client.exec_calls[-1] == ("local-openshell-sandbox", ("codex",))
    _assert_runner_uses_shims_without_real_bin_path_lookup(client, real_bin=real_bin)
    assert codex_marker.exists(), "fake codex child process did not run"
    assert result.exit_code == 121
    assert "by hook-check" in result.stderr
    assert "posture=governed" in result.stderr
    assert "restricted mechanic (deploy)" in result.stderr
    assert not real_git_marker.exists(), "downstream real git must not execute"
    assert not codex_after_marker.exists(), "codex child must stop at denied git push"


def test_codex_child_git_status_allowed_under_pinned_governed_posture(tmp_path):
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    _write_governed_ledger(sandbox_dir)

    harness_bin = sandbox_dir / "harness-bin"
    real_bin = sandbox_dir / "real-bin"
    harness_bin.mkdir()
    real_bin.mkdir()
    real_git_marker = sandbox_dir / "real-git-ran"
    codex_marker = sandbox_dir / "codex-ran"
    codex_after_marker = sandbox_dir / "codex-after-git"

    _write_executable(
        harness_bin / "codex",
        f"""#!/usr/bin/env sh
set -eu
printf 'codex child reached\\n' > {codex_marker}
git status
printf 'after git\\n' > {codex_after_marker}
""",
    )
    _write_executable(
        real_bin / "git-real",
        f"""#!/usr/bin/env sh
set -eu
printf '%s\\n' "$*" > {real_git_marker}
""",
    )
    real_gh = _write_executable(real_bin / "gh-real", "#!/usr/bin/env sh\nexit 0\n")
    real_ce = _write_executable(real_bin / "ce-real", "#!/usr/bin/env sh\nexit 0\n")

    guard = Ring1ToolGuardConfig(
        base_path=f"{harness_bin}:{os.environ.get('PATH', '')}",
        posture_root=str(sandbox_dir),
        extra_read_roots=(str(VALIDATORS_ROOT),),
        real_binaries=_test_real_binaries(
            git=real_bin / "git-real",
            gh=real_gh,
            ce=real_ce,
        ),
        validator_argv=(sys.executable, "-m", "creator_engine_validator"),
    )
    _assert_ce_real_binary_is_pinned(guard, real_ce=real_ce, real_bin=real_bin)
    client = LocalSandboxClient(sandbox_dir)
    backend = OpenShellBackend(client=client, ring1_guard=guard)
    handle = backend.provision(ProvisionRequest(runtime_policy=_valid_policy(), run_id="ring1-codex"))

    result = backend.run(handle, RunRequest(command=("codex",)))

    _assert_runner_uses_shims_without_real_bin_path_lookup(client, real_bin=real_bin)
    assert result.exit_code == 0, result.stderr
    assert codex_marker.exists(), "fake codex child process did not run"
    assert real_git_marker.read_text(encoding="utf-8").strip() == "status"
    assert codex_after_marker.exists(), "codex child should continue after allowed git status"
