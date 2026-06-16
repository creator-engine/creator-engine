"""OpenShell lifecycle tests for opt-in runner-owned Ring-1 tool guards."""

from __future__ import annotations

import pytest

from creator_engine_validator.runner import (
    FakeSandboxClient,
    OpenShellBackend,
    PolicyRejected,
    ProvisionRequest,
    RunRequest,
)
from creator_engine_validator.runner.ring1_tool_guard import (
    DEFAULT_EVIDENCE_ROOT,
    DEFAULT_SHIM_DIR,
    Ring1ToolGuardConfig,
)

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


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
    backend = OpenShellBackend(client=fake, ring1_guard=Ring1ToolGuardConfig())

    backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-ring1"))

    assert len(fake.created_specs) == 1
    assert len(fake.exec_calls) == 1
    sandbox_id, command = fake.exec_calls[0]
    assert sandbox_id == "openshell-sandbox-1"
    assert command[:2] == ("sh", "-c")
    assert f"cat > {DEFAULT_SHIM_DIR}/git" in command[2]
    assert f"cat > {DEFAULT_SHIM_DIR}/gh" in command[2]
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
    assert env["PATH"] == f"{DEFAULT_SHIM_DIR}:/usr/bin:/bin"
    assert env["CE_RING1_POSTURE"] == "auto"
    assert env["CE_RING1_EVIDENCE_ROOT"] == DEFAULT_EVIDENCE_ROOT


def test_no_guard_install_occurs_before_policy_validation_rejects():
    fake = FakeSandboxClient()
    backend = OpenShellBackend(client=fake, ring1_guard=Ring1ToolGuardConfig())
    bad = valid_policy()
    del bad["image_ref"]["sha"]

    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="bad-ring1"))

    assert fake.created_specs == []
    assert fake.exec_calls == []
