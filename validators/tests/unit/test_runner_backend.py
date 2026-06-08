"""Unit tests for the v3 G-1.1 runner-backend adapter interface.

Pure interface + the inert local-noop backend — no live container, no network,
no subprocess. The adapter consumes the G-1.0 runtime-policy record and keeps
its deny surface load-bearing at the provision boundary.
"""

import subprocess

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.runner import (
    BackendAlreadyRegistered,
    CollectedEvidence,
    LOCAL_NOOP_BACKEND_KEY,
    LocalNoopBackend,
    OPENSHELL_BACKEND_KEY,
    OpenShellBackend,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunRequest,
    RunResult,
    RunnerBackend,
    TeardownResult,
    UnknownBackend,
    available_backends,
    get_backend,
    register_backend,
)
from creator_engine_validator.runner.backend import _REGISTRY

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy() -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "gvisor-proxy",
        "image_ref": {
            "name": "registry.example/creator-engine/implementer",
            "sha": _IMAGE_SHA,
        },
        "mount_manifest": [{"path": "governance", "mode": "ro"}],
        "egress_allowlist": [],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------
def test_runner_backend_is_abstract():
    with pytest.raises(TypeError):
        RunnerBackend()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# local-noop backend: registration + full inert lifecycle
# ---------------------------------------------------------------------------
def test_local_noop_registered():
    assert LOCAL_NOOP_BACKEND_KEY == "local-noop"
    assert "local-noop" in available_backends()
    backend = get_backend("local-noop")
    assert isinstance(backend, LocalNoopBackend)
    assert isinstance(backend, RunnerBackend)


def test_full_lifecycle_inert():
    backend = get_backend("local-noop")
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    assert isinstance(handle, ProvisionedHandle)
    assert handle.backend_key == "local-noop"
    assert handle.run_id == "run-1"
    assert handle.policy_sha == _POLICY_SHA  # binds the exact policy version

    result = backend.run(handle, RunRequest(command=("echo", "hi")))
    assert isinstance(result, RunResult)
    assert result.exit_code == 0
    assert "echo" in result.stdout
    assert result.started_ref == handle.ref

    evidence = backend.collect(handle)
    assert isinstance(evidence, CollectedEvidence)
    assert evidence.handle_ref == handle.ref
    assert evidence.records == ()

    teardown = backend.teardown(handle)
    assert isinstance(teardown, TeardownResult)
    assert teardown.released is True
    assert teardown.handle_ref == handle.ref


# ---------------------------------------------------------------------------
# SD-D: provision keeps the G-1.0 deny surface load-bearing
# ---------------------------------------------------------------------------
def test_provision_rejects_controller_key_secret():
    backend = get_backend("local-noop")
    bad = valid_policy()
    bad["secret_allowlist"] = ["controller-private-key"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-2"))


def test_provision_rejects_unpinned_image():
    backend = get_backend("local-noop")
    bad = valid_policy()
    del bad["image_ref"]["sha"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-3"))


def test_provision_rejects_forbidden_mount():
    backend = get_backend("local-noop")
    bad = valid_policy()
    bad["mount_manifest"] = [{"path": "~/.ssh", "mode": "ro"}]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-4"))


def test_provision_rejects_non_mapping():
    backend = get_backend("local-noop")
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=[], run_id="run-5"))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def test_openshell_registered():
    # openshell is registered as of v3.5-A.2a (the slice that closes the loop A.1
    # deferred): it resolves to an OpenShellBackend and joins available_backends().
    assert OPENSHELL_BACKEND_KEY == "openshell"
    assert "openshell" in available_backends()
    backend = get_backend("openshell")
    assert isinstance(backend, OpenShellBackend)
    assert isinstance(backend, RunnerBackend)
    # A genuinely-unknown key still raises — the negative-path teeth stay live.
    with pytest.raises(UnknownBackend):
        get_backend("no-such-backend")


def test_register_and_duplicate():
    key = "test-only-backend"
    register_backend(key, LocalNoopBackend)
    try:
        assert key in available_backends()
        assert isinstance(get_backend(key), LocalNoopBackend)
        with pytest.raises(BackendAlreadyRegistered):
            register_backend(key, LocalNoopBackend)
    finally:
        _REGISTRY.pop(key, None)


def test_available_backends_is_sorted():
    keys = available_backends()
    assert list(keys) == sorted(keys)


# ---------------------------------------------------------------------------
# No live subprocess / network in G-1.1
# ---------------------------------------------------------------------------
def test_no_subprocess_invoked(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("runner adapter must not invoke a live subprocess in G-1.1")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    backend = get_backend("local-noop")
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-6"))
    backend.run(handle, RunRequest(command=("echo", "hi")))
    backend.collect(handle)
    backend.teardown(handle)


# ---------------------------------------------------------------------------
# Importing the adapter registers no validator check (--list-checks unchanged)
# ---------------------------------------------------------------------------
def test_importing_runner_registers_no_check():
    import creator_engine_validator.runner  # noqa: F401  (ensure imported)

    names = set(registered_checks())
    assert "ce_runtime_policy" in names  # G-1.0 check is present
    assert not any("runner" in name or "backend" in name for name in names)
