"""OpenShell lifecycle tests for default runner-owned Ring-1 tool guards."""

from __future__ import annotations

import ast
import json

import pytest

from creator_engine_validator import fs_mediation as fm
from creator_engine_validator.runner import (
    FakeSandboxClient,
    OpenShellBackend,
    PolicyRejected,
    ProvisionRequest,
    RunRequest,
)
from creator_engine_validator.runner import openshell_backend as ob
from creator_engine_validator.runner.ring1_tool_guard import (
    DEFAULT_EVIDENCE_ROOT,
    Ring1ToolGuardConfig,
)

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def _install_payload(script: str) -> dict:
    marker = "PAYLOAD = json.loads("
    start = script.index(marker) + len(marker)
    end = script.index(")\n\n\n", start)
    return json.loads(ast.literal_eval(script[start:end]))


@pytest.fixture(autouse=True)
def _ring1_test_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    shim_parent = tmp_path / "ring1-shim-parent"
    shim_parent.mkdir(mode=0o700)
    monkeypatch.setattr(ob, "DEFAULT_RING1_SHIM_DIR", str(shim_parent / "shim"))


def valid_policy() -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "openshell-ring1-v1",
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


def test_provision_installs_guard_after_sandbox_create():
    fake = FakeSandboxClient()
    backend = OpenShellBackend(client=fake)

    backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-ring1"))

    assert len(fake.created_specs) == 1
    assert len(fake.exec_calls) == 1
    sandbox_id, command = fake.exec_calls[0]
    assert sandbox_id == "openshell-sandbox-1"
    assert command[:2] == ("sh", "-c")
    payload = _install_payload(command[2])
    shim_by_tool = {tool: content for tool, content in payload["shims"]}
    assert payload["target_dir"] == ob.DEFAULT_RING1_SHIM_DIR
    assert set(shim_by_tool) == {"git", "gh"}
    assert "O_EXCL" in command[2]
    assert '"posture": "governed"' in shim_by_tool["git"]
    assert '"posture_root": "/runtime/worktree"' in shim_by_tool["git"]
    assert '"ledger_root": ""' in shim_by_tool["git"]
    assert fake.exec_environments == [None]


def test_run_injects_guard_path_environment():
    fake = FakeSandboxClient(sandbox_id="openshell-sandbox-ring1")
    backend = OpenShellBackend(
        client=fake,
        ring1_guard=Ring1ToolGuardConfig(base_path="/usr/bin:/bin"),
    )
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-ring1"))

    backend.run(handle, RunRequest(command=("codex", "exec")))

    assert fake.exec_calls[-1] == ("openshell-sandbox-ring1", ("codex", "exec"))
    env = fake.exec_environments[-1]
    assert env is not None
    assert env["PATH"] == f"{ob.DEFAULT_RING1_SHIM_DIR}:/usr/bin:/bin"
    assert env["CE_RING1_POSTURE"] == "governed"
    assert env["CE_RING1_EVIDENCE_ROOT"] == DEFAULT_EVIDENCE_ROOT
    assert fake.exec_preexec_fns[-1] is not None


def test_default_guard_honors_backend_pinned_root_overrides():
    fake = FakeSandboxClient(sandbox_id="openshell-sandbox-ring1")
    backend = OpenShellBackend(
        client=fake,
        ring1_posture_root="/runtime/worktree",
        ring1_ledger_root="/runtime/worktree/.hermes/active-work-ledger",
    )
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-ring1"))

    install = fake.exec_calls[0][1][2]
    payload = _install_payload(install)
    shim_by_tool = {tool: content for tool, content in payload["shims"]}
    assert '"posture_root": "/runtime/worktree"' in shim_by_tool["git"]
    assert (
        '"ledger_root": "/runtime/worktree/.hermes/active-work-ledger"'
        in shim_by_tool["git"]
    )

    backend.run(handle, RunRequest(command=("codex", "exec")))
    env = fake.exec_environments[-1]
    assert env is not None
    assert env["CE_RING1_POSTURE_ROOT"] == "/runtime/worktree"
    assert env["CE_LEDGER_ROOT"] == "/runtime/worktree/.hermes/active-work-ledger"
    assert fake.exec_preexec_fns[-1] is not None


def test_provision_fails_closed_before_sandbox_create_when_landlock_unavailable(monkeypatch):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: None)
    fake = FakeSandboxClient()
    backend = OpenShellBackend(client=fake)

    with pytest.raises(fm.FsMediationUnavailable, match="fail-closed"):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-ring1"))

    assert fake.created_specs == []
    assert fake.exec_calls == []


def test_no_guard_install_occurs_before_policy_validation_rejects():
    fake = FakeSandboxClient()
    backend = OpenShellBackend(client=fake, ring1_guard=Ring1ToolGuardConfig())
    bad = valid_policy()
    del bad["image_ref"]["sha"]

    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="bad-ring1"))

    assert fake.created_specs == []
    assert fake.exec_calls == []
