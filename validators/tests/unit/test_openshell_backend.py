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
import subprocess

import pytest
import yaml

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
    SubprocessSandboxClient,
    available_backends,
    get_backend,
    render_sandbox_policy_yaml,
    translate_to_sandbox_policy,
)
from creator_engine_validator.runner.openshell_backend import (
    SandboxPolicy as _SandboxPolicyModule,
    parse_ocsf_jsonl,
)

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
# Identity — direct instantiation (still valid). The registry assertions A.1
# deferred to A.2 now live in the "Registry (v3.5-A.2a)" section at the bottom.
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


# ---------------------------------------------------------------------------
# Registry (v3.5-A.2a) — the now-valid assertions A.1 said belonged in A.2.
# Registering the backend adds NO validator check (--list-checks byte-identical);
# register_backend is the BACKEND registry, not the @register check registry.
# ---------------------------------------------------------------------------
def test_openshell_registered_in_registry():
    assert OPENSHELL_BACKEND_KEY in available_backends()
    # The sorted 3-tuple — the ~10 registry-pinning tests A.1 deferred move to this.
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell")
    backend = get_backend("openshell")
    assert isinstance(backend, OpenShellBackend)
    assert isinstance(backend, RunnerBackend)


def test_registry_resolved_default_refuses_at_provision():
    # get_backend("openshell")() returns an instance with NO injected client → the
    # inert _UnwiredSandboxClient default. Now that the backend is REGISTERED it must
    # NOT silently shell out: it refuses at provision with BackendUnavailable (the
    # honest "registered but not auto-live in CI" posture, mirroring gVisor's
    # availability gate). The live run is A.2b. This extends the A.1
    # direct-instantiation test_default_client_is_unwired_and_refuses to the
    # registry-resolved case.
    backend = get_backend("openshell")
    with pytest.raises(BackendUnavailable):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-reg"))


# ---------------------------------------------------------------------------
# Pure policy serialization — render_sandbox_policy_yaml (the --policy wire form)
# ---------------------------------------------------------------------------
def test_render_sandbox_policy_yaml_round_trips_structure():
    rendered = render_sandbox_policy_yaml(translate_to_sandbox_policy(valid_policy()))
    loaded = yaml.safe_load(rendered)
    # filesystem (directory allowlists)
    assert loaded["filesystem"]["include_workdir"] is True
    assert "/runtime/worktree" in loaded["filesystem"]["read_write"]
    assert "governance" in loaded["filesystem"]["read_only"]
    # landlock + process
    assert loaded["landlock"]["compatibility"] == "best_effort"
    assert loaded["process"]["run_as_user"] == "sandbox"
    assert loaded["process"]["run_as_group"] == "sandbox"
    # network_policies is a MAP keyed by rule name, each value carrying endpoints[]
    nps = loaded["network_policies"]
    assert isinstance(nps, dict)
    assert set(nps) == {"model_provider_example_443", "pkg_example"}
    mp = nps["model_provider_example_443"]["endpoints"][0]
    assert mp["host"] == "model-provider.example"
    assert mp["port"] == 443
    assert mp["protocol"] == "https"
    # Every translated endpoint is binding (enforce), not advisory (audit).
    assert mp["enforcement"] == "enforce"
    assert mp["access"] == "read-write"
    # An endpoint with no port omits the key on the wire (no null port).
    pkg = nps["pkg_example"]["endpoints"][0]
    assert pkg["host"] == "pkg.example"
    assert "port" not in pkg


def test_render_sandbox_policy_yaml_is_deterministic():
    a = render_sandbox_policy_yaml(translate_to_sandbox_policy(valid_policy()))
    b = render_sandbox_policy_yaml(translate_to_sandbox_policy(valid_policy()))
    assert a == b


def test_render_sandbox_policy_yaml_empty_allowlist_is_no_egress():
    record = valid_policy()
    record["egress_allowlist"] = []
    translated = translate_to_sandbox_policy(record)
    assert translated.no_egress is True
    loaded = yaml.safe_load(render_sandbox_policy_yaml(translated))
    # Empty map => the OPA proxy denies all egress (deny-by-default on the wire).
    assert loaded["network_policies"] == {}


# ---------------------------------------------------------------------------
# Pure OCSF JSONL parser — parse_ocsf_jsonl (the live file read is # pragma: no cover)
# ---------------------------------------------------------------------------
def test_parse_ocsf_jsonl_parses_lines_and_skips_blanks():
    text = (
        '{"class_uid": 4001, "action": "Allowed", "disposition": "Allowed", "status": "Success"}\n'
        "\n"
        "   \n"
        '{"class_uid": 4001, "action": "Denied", "disposition": "Blocked", '
        '"status": "Failure", "status_detail": "no matching policy"}\n'
    )
    records = parse_ocsf_jsonl(text)
    assert len(records) == 2
    assert records[0]["action"] == "Allowed"
    assert records[1]["action"] == "Denied"
    assert records[1]["status_detail"] == "no matching policy"


def test_parse_ocsf_jsonl_empty_text_is_empty_list():
    assert parse_ocsf_jsonl("") == []
    assert parse_ocsf_jsonl("\n  \n") == []


def test_parse_ocsf_jsonl_malformed_line_raises():
    # Audit-log corruption is surfaced, never silently dropped.
    import json

    with pytest.raises(json.JSONDecodeError):
        parse_ocsf_jsonl('{"action": "Allowed"}\nthis is not json\n')


def test_parsed_ocsf_records_flow_through_collect():
    # The parser's output is exactly what the backend's collect() maps via the OCSF
    # decision-field mapper — exercised end-to-end through the injected fake.
    text = (
        '{"class_uid": 4001, "action": "Allowed", "disposition": "Allowed", "status": "Success"}\n'
        '{"class_uid": 4001, "action": "Denied", "disposition": "Blocked", "status": "Failure"}\n'
    )
    backend = OpenShellBackend(client=FakeSandboxClient(ocsf_records=parse_ocsf_jsonl(text)))
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-ocsf"))
    evidence = backend.collect(handle)
    assert [record["action"] for record in evidence.records] == ["Allowed", "Denied"]


# ---------------------------------------------------------------------------
# SubprocessSandboxClient — the live CLI transport. The shell-outs are
# # pragma: no cover; only the side-effect-free availability probe is exercised.
# ---------------------------------------------------------------------------
def test_subprocess_sandbox_client_available_false_for_missing_binary():
    client = SubprocessSandboxClient(binary="ce-definitely-no-such-openshell-bin")
    assert client.available() is False


def test_subprocess_sandbox_client_available_spawns_no_subprocess(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("available() must not spawn a subprocess in CI")

    monkeypatch.setattr(subprocess, "run", explode)
    SubprocessSandboxClient(binary="ce-definitely-no-such-openshell-bin").available()
