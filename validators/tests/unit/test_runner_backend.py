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
    BackendUnavailable,
    CollectedEvidence,
    LOCAL_NOOP_BACKEND_KEY,
    LocalNoopBackend,
    OPENSHELL_BACKEND_KEY,
    OS_NATIVE_BACKEND_KEY,
    OpenShellBackend,
    OsNativeCapability,
    OsNativeBackend,
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


def os_native_capability_available() -> OsNativeCapability:
    return OsNativeCapability(
        platform_name="Linux",
        bwrap_path="/usr/bin/bwrap",
        landlock_abi=4,
        seccomp_available=True,
        proxy_path="/usr/bin/proxy",
        missing=(),
    )


def os_native_capability_missing(*missing: str) -> OsNativeCapability:
    return OsNativeCapability(
        platform_name="Linux",
        bwrap_path=None if "bwrap" in missing else "/usr/bin/bwrap",
        landlock_abi=None if "landlock" in missing else 4,
        seccomp_available="seccomp" not in missing,
        proxy_path=None if "proxy" in missing else "/usr/bin/proxy",
        missing=tuple(missing),
    )


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------
def test_runner_backend_is_abstract():
    with pytest.raises(TypeError):
        RunnerBackend()  # type: ignore[abstract]


def test_subclass_cannot_override_the_provision_template():
    # ce-ops#71 req-3 made STRUCTURAL: a backend that overrides the
    # validate-at-provision TEMPLATE (instead of the `_provision` hook) could skip
    # the G-1.0 deny surface. __init_subclass__ rejects that at CLASS-CREATION time
    # — no instance, no registry, no live call needed.
    with pytest.raises(TypeError, match="must not override RunnerBackend.provision"):

        class SkipsValidation(RunnerBackend):  # noqa: F811 - defined to be rejected
            backend_key = "skips-validation"

            def provision(self, request):  # the forbidden override
                return ProvisionedHandle(self.backend_key, request.run_id, _POLICY_SHA, "ref")

            def _provision(self, request):  # pragma: no cover - class never created
                raise NotImplementedError

            def run(self, handle, request):  # pragma: no cover
                raise NotImplementedError

            def collect(self, handle):  # pragma: no cover
                raise NotImplementedError

            def teardown(self, handle):  # pragma: no cover
                raise NotImplementedError


def test_subclass_overriding_only__provision_is_allowed():
    # the legitimate shape: override the hook, inherit the template. This is exactly
    # what every shipped backend does — class creation must NOT raise.
    class HookOnly(RunnerBackend):
        backend_key = "hook-only-test"

        def _provision(self, request):
            return ProvisionedHandle(self.backend_key, request.run_id, _POLICY_SHA, "ref")

        def run(self, handle, request):  # pragma: no cover
            raise NotImplementedError

        def collect(self, handle):  # pragma: no cover
            raise NotImplementedError

        def teardown(self, handle):  # pragma: no cover
            raise NotImplementedError

    assert HookOnly().provision.__func__ is RunnerBackend.provision


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


# ---------------------------------------------------------------------------
# ce-ops#71 Tranche 1 — the os-native scaffold + the validate-at-provision
# invariant promoted to the ABC (req-3).
# ---------------------------------------------------------------------------
def test_os_native_registered():
    assert OS_NATIVE_BACKEND_KEY == "os-native"
    assert "os-native" in available_backends()
    backend = get_backend("os-native")
    assert isinstance(backend, OsNativeBackend)
    assert isinstance(backend, RunnerBackend)


def test_os_native_fails_closed_when_required_linux_primitives_are_missing():
    backend = OsNativeBackend(
        capability_probe=lambda: os_native_capability_missing("bwrap", "landlock", "proxy")
    )
    clean = valid_policy()
    clean["isolation_backend"] = "os-native"
    with pytest.raises(BackendUnavailable) as exc:
        backend.provision(ProvisionRequest(runtime_policy=clean, run_id="run-osn"))
    message = str(exc.value)
    assert "os-native" in message
    assert "missing: bwrap, landlock, proxy" in message
    assert "falling back to unsandboxed execution or gvisor-proxy" in message


def test_os_native_fails_closed_on_non_linux_host():
    backend = OsNativeBackend(
        capability_probe=lambda: OsNativeCapability(
            platform_name="Darwin",
            bwrap_path=None,
            landlock_abi=None,
            seccomp_available=False,
            proxy_path=None,
            missing=("linux",),
        )
    )
    clean = valid_policy()
    clean["isolation_backend"] = "os-native"
    with pytest.raises(BackendUnavailable) as exc:
        backend.provision(ProvisionRequest(runtime_policy=clean, run_id="run-osn-darwin"))
    assert "Linux bwrap + Landlock + seccomp" in str(exc.value)
    assert "refusing rather than falling back to unsandboxed execution" in str(exc.value)


def test_os_native_provisions_scaffold_when_option_a_primitives_are_available():
    backend = OsNativeBackend(capability_probe=os_native_capability_available)
    clean = valid_policy()
    clean["isolation_backend"] = "os-native"

    handle = backend.provision(ProvisionRequest(runtime_policy=clean, run_id="run-osn-ready"))

    assert handle.backend_key == "os-native"
    assert handle.ref == "os-native-scaffold:run-osn-ready"
    evidence = backend.collect(handle)
    assert evidence.records[0]["mechanism"] == "bwrap+landlock+seccomp+proxy"
    assert evidence.records[0]["execution"] == "follow-on"
    with pytest.raises(BackendUnavailable, match="refusing to run a command rather than launching unsandboxed"):
        backend.run(handle, RunRequest(command=("echo", "hi")))
    assert backend.teardown(handle).released is True


def test_every_registered_backend_rejects_a_dirty_record():
    # The promoted invariant: because #71 ADDS a backend, "validate-at-provision"
    # is enforced by RunnerBackend.provision for EVERY registered backend, not a
    # per-backend discipline. A controller-key secret is the canonical dirty record.
    dirty = valid_policy()
    dirty["secret_allowlist"] = ["controller-private-key"]
    for key in available_backends():
        backend = get_backend(key)
        with pytest.raises(PolicyRejected):
            backend.provision(ProvisionRequest(runtime_policy=dirty, run_id=f"dirty-{key}"))


def test_every_registered_backend_rejects_a_non_mapping_record():
    for key in available_backends():
        backend = get_backend(key)
        with pytest.raises(PolicyRejected):
            backend.provision(ProvisionRequest(runtime_policy=[], run_id=f"nonmap-{key}"))  # type: ignore[arg-type]


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
