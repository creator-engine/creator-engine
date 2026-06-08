"""Unit tests for the v3.5-A.1 OpenShell runner backend (pure, green-now).

Translate-vs-execute split (mirrors the gVisor backend's tests): the policy
translation is pure and fully tested here; the backend's live work goes through
an injected ``FakeSandboxClient`` so these tests perform ZERO network/gRPC and
importing the module pulls in no ``grpcio``/``openshell`` dependency. The live
gRPC/SDK client is v3.5-A.2; spend metering is v3.5-A.3 — neither is exercised
here. The G-1.0 deny surface stays load-bearing: ``provision`` refuses a
runtime-policy that does not validate clean.
"""

import socket

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.runner import (
    BackendUnavailable,
    CollectedEvidence,
    Endpoint,
    FakeSandboxClient,
    FilesystemPolicy,
    NetworkRule,
    OPENSHELL_BACKEND_KEY,
    OPENSHELL_PINNED_VERSION,
    OpenShellBackend,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunRequest,
    RunResult,
    RunnerBackend,
    SandboxCreateSpec,
    SandboxPolicy,
    translate_to_sandbox_policy,
)
from creator_engine_validator.runner.openshell_backend import SandboxPolicy as _SandboxPolicyModule

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy() -> dict:
    """A schema-clean runtime-policy record provisioned under the openshell backend."""
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "openshell-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "openshell",
        "image_ref": {"name": "registry.example/creator-engine/implementer", "sha": _IMAGE_SHA},
        "mount_manifest": [
            {"path": "/runtime/worktree", "mode": "rw", "write_justification": "allocated worktree"},
            {"path": "governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "port": 443, "protocol": "https", "assurance": ["l4"]},
            {"host": "pkg.example", "protocol": "https", "assurance": ["l7"], "tls_terminated": True},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


# ---------------------------------------------------------------------------
# Pure translation
# ---------------------------------------------------------------------------
def test_translate_returns_sandbox_policy():
    policy = translate_to_sandbox_policy(valid_policy())
    assert isinstance(policy, SandboxPolicy)
    assert policy is not None and SandboxPolicy is _SandboxPolicyModule


def test_translate_filesystem_mounts_to_ro_rw():
    fs = translate_to_sandbox_policy(valid_policy()).filesystem
    assert isinstance(fs, FilesystemPolicy)
    assert "/runtime/worktree" in fs.read_write
    assert "governance" in fs.read_only
    # The rw mount is NOT also listed read-only, and vice versa.
    assert "/runtime/worktree" not in fs.read_only
    assert "governance" not in fs.read_write
    # No explicit include_workdir field on a schema-clean record => default true.
    assert fs.include_workdir is True


def test_translate_include_workdir_honours_explicit_field():
    # translate is pure (no schema validation), so an explicit field is honoured.
    policy = valid_policy()
    policy["include_workdir"] = False
    assert translate_to_sandbox_policy(policy).filesystem.include_workdir is False


def test_translate_landlock_and_process_defaults():
    policy = translate_to_sandbox_policy(valid_policy())
    assert policy.landlock.compatibility == "best_effort"
    assert policy.process.run_as_user == "sandbox"
    assert policy.process.run_as_group == "sandbox"


def test_translate_egress_to_network_policies():
    policy = translate_to_sandbox_policy(valid_policy())
    assert not policy.no_egress
    assert len(policy.network_policies) == 2
    rules = {rule.name: rule for rule in policy.network_policies}
    by_host = {rule.endpoints[0].host: rule for rule in policy.network_policies}
    assert set(by_host) == {"model-provider.example", "pkg.example"}
    mp = by_host["model-provider.example"]
    assert isinstance(mp, NetworkRule)
    endpoint = mp.endpoints[0]
    assert isinstance(endpoint, Endpoint)
    assert endpoint.port == 443
    assert endpoint.protocol == "https"
    # Every translated endpoint is binding (enforce), not advisory (audit).
    assert endpoint.enforcement == "enforce"
    assert endpoint.access == "read-write"
    # Names are deterministic, map-safe slugs derived from the host(+port).
    assert "model_provider_example_443" in rules


def test_translate_empty_allowlist_is_no_egress():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    translated = translate_to_sandbox_policy(policy)
    assert translated.no_egress is True
    assert translated.network_policies == ()


def test_translate_does_not_carry_image_or_policy_sha():
    # image_ref -> create-spec template.image (in provision); policy_sha -> handle.
    policy = translate_to_sandbox_policy(valid_policy())
    assert not hasattr(policy, "image")
    assert not hasattr(policy, "image_ref")
    assert not hasattr(policy, "policy_sha")


# ---------------------------------------------------------------------------
# Identity — exercised by DIRECT instantiation (the backend is UNREGISTERED in
# A.1; registration + the get_backend/available_backends assertions move to A.2).
# ---------------------------------------------------------------------------
def test_backend_is_a_runner_backend():
    backend = OpenShellBackend(client=FakeSandboxClient())
    assert isinstance(backend, RunnerBackend)
    assert backend.backend_key == "openshell"


def test_backend_key_and_pinned_version_constants():
    assert OPENSHELL_BACKEND_KEY == "openshell"
    assert OPENSHELL_PINNED_VERSION == "v0.0.57"


# ---------------------------------------------------------------------------
# Backend — deny-guard at the boundary (G-1.0 deny surface stays load-bearing)
# ---------------------------------------------------------------------------
def test_provision_clean_policy_binds_policy_sha():
    backend = OpenShellBackend(client=FakeSandboxClient())
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    assert isinstance(handle, ProvisionedHandle)
    assert handle.backend_key == "openshell"
    assert handle.policy_sha == _POLICY_SHA
    assert handle.ref.startswith("openshell:")


def test_provision_rejects_non_mapping_policy():
    backend = OpenShellBackend(client=FakeSandboxClient())
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=["not", "a", "mapping"], run_id="run-2"))


def test_provision_rejects_controller_key_secret():
    backend = OpenShellBackend(client=FakeSandboxClient())
    bad = valid_policy()
    bad["secret_allowlist"] = ["controller-private-key"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-3"))


def test_provision_rejects_unpinned_image():
    backend = OpenShellBackend(client=FakeSandboxClient())
    bad = valid_policy()
    del bad["image_ref"]["sha"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-4"))


def test_default_client_is_unwired_and_refuses():
    # No injected client => the inert default; the live gRPC path is A.2, so it
    # honestly refuses rather than pretending to provision.
    backend = OpenShellBackend()
    with pytest.raises(BackendUnavailable):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-5"))


# ---------------------------------------------------------------------------
# Lifecycle through the injected fake client
# ---------------------------------------------------------------------------
def test_create_spec_carries_translated_policy_and_image():
    fake = FakeSandboxClient()
    backend = OpenShellBackend(client=fake)
    backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-6"))
    assert len(fake.created_specs) == 1
    spec = fake.created_specs[0]
    assert isinstance(spec, SandboxCreateSpec)
    # template.image is the digest-pinned image assembled from image_ref.
    assert spec.image == f"registry.example/creator-engine/implementer@{_IMAGE_SHA}"
    assert isinstance(spec.policy, SandboxPolicy)
    assert len(spec.policy.network_policies) == 2


def test_full_lifecycle_through_fake_client():
    fake = FakeSandboxClient(sandbox_id="openshell-sandbox-xyz", exit_code=0, stdout="hello")
    backend = OpenShellBackend(client=fake)
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-7"))

    result = backend.run(handle, RunRequest(command=("echo", "hi")))
    assert isinstance(result, RunResult)
    assert result.exit_code == 0 and result.stdout == "hello"
    assert result.started_ref == handle.ref
    # The injected client saw the exec against the created sandbox id.
    assert fake.exec_calls == [("openshell-sandbox-xyz", ("echo", "hi"))]

    evidence = backend.collect(handle)
    assert isinstance(evidence, CollectedEvidence)
    assert evidence.handle_ref == handle.ref

    teardown = backend.teardown(handle)
    assert teardown.released is True
    assert fake.deleted == ["openshell-sandbox-xyz"]


def test_collect_maps_ocsf_records_action_allowed_denied():
    ocsf = [
        {"class_uid": 4001, "action": "Allowed", "disposition": "Allowed", "status": "Success"},
        {
            "class_uid": 4001,
            "action": "Denied",
            "disposition": "Blocked",
            "status": "Failure",
            "status_detail": "no matching policy",
        },
    ]
    backend = OpenShellBackend(client=FakeSandboxClient(ocsf_records=ocsf))
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-8"))
    evidence = backend.collect(handle)
    assert len(evidence.records) == 2
    actions = [record["action"] for record in evidence.records]
    assert actions == ["Allowed", "Denied"]
    denied = evidence.records[1]
    assert denied["disposition"] == "Blocked"
    assert denied["status"] == "Failure"
    assert denied["status_detail"] == "no matching policy"
    # The full raw OCSF record is preserved for evidence-spine fidelity.
    assert denied["raw"]["class_uid"] == 4001


def test_teardown_reports_unreleased_when_client_says_so():
    backend = OpenShellBackend(client=FakeSandboxClient(delete_released=False))
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-9"))
    assert backend.teardown(handle).released is False


# ---------------------------------------------------------------------------
# No network / no gRPC — the pure-slice invariant
# ---------------------------------------------------------------------------
def test_no_network_during_lifecycle(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the A.1 OpenShell backend must not open a socket in CI")

    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    backend = OpenShellBackend(client=FakeSandboxClient())
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-10"))
    backend.run(handle, RunRequest(command=("echo", "hi")))
    backend.collect(handle)
    backend.teardown(handle)


def test_no_grpc_dependency_imported():
    import sys

    # Importing the A.1 backend must not pull in grpcio (the live client is A.2).
    assert "grpc" not in sys.modules
    assert "grpcio" not in sys.modules


# ---------------------------------------------------------------------------
# Importing the adapter registers no validator check (--list-checks invariant)
# ---------------------------------------------------------------------------
def test_importing_runner_registers_no_check():
    names = set(registered_checks())
    assert "ce_runtime_policy" in names
    assert not any("runner" in n or "backend" in n or "openshell" in n for n in names)
