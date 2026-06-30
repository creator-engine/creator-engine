"""Fail-closed tests for the OQ-1 Option A os-native runner backend."""

import subprocess

import pytest

from creator_engine_validator import fs_mediation as fm
from creator_engine_validator.runner import (
    BackendUnavailable,
    FakeSandboxClient,
    OpenShellBackend,
    ProvisionRequest,
    ProvisionedHandle,
    RunRequest,
)
from creator_engine_validator.runner import openshell_backend as ob
from creator_engine_validator.runner import os_native_backend as osn
from creator_engine_validator.runner.os_native_backend import (
    OsNativeBackend,
    OsNativeCapability,
    SubprocessOsNativeRunner,
)

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def capability() -> OsNativeCapability:
    return OsNativeCapability(
        platform_name="Linux",
        bwrap_path="/usr/bin/bwrap",
        landlock_abi=4,
        seccomp_available=True,
        proxy_path="/usr/bin/proxy",
        missing=(),
    )


def policy(worktree: str, *, egress: bool = False) -> dict:
    allowlist = []
    if egress:
        allowlist = [
            {"host": "api.example", "port": 443, "protocol": "https", "assurance": ["l4"]}
        ]
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "os-native-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "os-native",
        "image_ref": {
            "name": "registry.example/creator-engine/implementer",
            "sha": _IMAGE_SHA,
        },
        "mount_manifest": [
            {"path": worktree, "mode": "rw", "write_justification": "allocated worktree"},
        ],
        "egress_allowlist": allowlist,
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


@pytest.fixture(autouse=True)
def _openshell_test_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    shim_parent = tmp_path / "ring1-shim-parent"
    shim_parent.mkdir(mode=0o700)
    monkeypatch.setattr(ob, "DEFAULT_RING1_SHIM_DIR", str(shim_parent / "shim"))


class FakeNativeRunner:
    def __init__(self, *, available: bool = True):
        self._available = available
        self.calls: list[tuple[str, object]] = []

    def available(self, cap: OsNativeCapability) -> bool:
        self.calls.append(("available", cap))
        return self._available

    def run(self, argv, *, preexec_fn, pass_fds):
        self.calls.append(("run", list(argv)))
        return subprocess.CompletedProcess(list(argv), 0, stdout="should-not-run", stderr="")


def test_os_native_probe_passes_but_execution_contract_missing_refuses_before_side_effects(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    runner = FakeNativeRunner()
    backend = OsNativeBackend(capability_probe=capability, runner=runner)

    with pytest.raises(BackendUnavailable, match="no concrete deny-by-default host-proxy"):
        backend.provision(ProvisionRequest(policy(str(worktree)), run_id="run-osn"))

    assert runner.calls == []


def test_os_native_non_empty_egress_also_refuses_before_runner_probe(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    runner = FakeNativeRunner()
    backend = OsNativeBackend(capability_probe=capability, runner=runner)

    with pytest.raises(BackendUnavailable, match="OpenShell CLI is not available"):
        backend.provision(ProvisionRequest(policy(str(worktree), egress=True), run_id="run-egress"))

    assert runner.calls == []


def test_os_native_egress_delegates_to_openshell_and_verifies_p3_before_user_run(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    p3_records = (
        {
            "event_type": "NET:OPEN",
            "severity": "MED",
            "disposition": "DENIED",
            "actor": "/usr/bin/python3(42)",
            "target": osn._P3_BLOCKED_TARGET,
            "policy": "-",
            "engine": "opa",
            "reason": "endpoint is not allowed by any policy",
            "raw": {
                "event_type": "NET:OPEN",
                "disposition": "DENIED",
                "target": osn._P3_BLOCKED_TARGET,
            },
        },
    )
    fake = FakeSandboxClient(sandbox_id="openshell-sandbox-egress", ocsf_records=p3_records)
    runner = FakeNativeRunner()

    def forbidden_probe() -> OsNativeCapability:
        raise AssertionError("egress delegation must not run the os-native proxy probe")

    backend = OsNativeBackend(
        capability_probe=forbidden_probe,
        runner=runner,
        openshell_backend_factory=lambda: OpenShellBackend(client=fake),
    )

    handle = backend.provision(ProvisionRequest(policy(str(worktree), egress=True), run_id="run-egress"))
    assert handle.backend_key == "os-native"
    assert handle.ref == "os-native:openshell:run-egress"
    assert len(fake.created_specs) == 1
    assert fake.created_specs[0].policy.network_policies[0].endpoints[0].enforcement == "enforce"
    # Provision installs the OpenShell Ring-1 guard; the P3 probe has not yet run.
    assert len(fake.exec_calls) == 1

    result = backend.run(handle, RunRequest(command=("echo", "hi")))

    assert result.exit_code == 0
    assert result.started_ref == handle.ref
    assert runner.calls == []
    assert fake.exec_calls[-2][1] == osn._P3_BLOCKED_PROBE_COMMAND
    assert osn._P3_BLOCKED_HOST in " ".join(fake.exec_calls[-2][1])
    assert fake.exec_calls[-1] == ("openshell-sandbox-egress", ("echo", "hi"))
    evidence = backend.collect(handle)
    assert evidence.records[0]["mechanism"] == "openshell-delegated-egress"
    assert evidence.records[0]["p3_behavioral_denial_verified"] is True
    assert backend.teardown(handle).released is True
    assert fake.deleted == ["openshell-sandbox-egress"]


def test_os_native_egress_unavailable_fails_closed_without_proxy_path_probe(monkeypatch, tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    runner = FakeNativeRunner()

    def forbidden_probe() -> OsNativeCapability:
        raise AssertionError("unavailable OpenShell must not fall through to os-native probe")

    def which(name: str):
        if name == "proxy":
            raise AssertionError("proxy PATH probe must not be used for delegated egress")
        return None

    monkeypatch.setattr(osn.shutil, "which", which)
    backend = OsNativeBackend(
        capability_probe=forbidden_probe,
        runner=runner,
        openshell_backend_factory=lambda: (_ for _ in ()).throw(
            BackendUnavailable("openshell unavailable")
        ),
    )

    with pytest.raises(BackendUnavailable, match="openshell unavailable"):
        backend.provision(ProvisionRequest(policy(str(worktree), egress=True), run_id="run-no-open"))

    assert runner.calls == []


def test_os_native_no_egress_keeps_existing_fail_closed_path(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    runner = FakeNativeRunner()

    def forbidden_openshell():
        raise AssertionError("empty egress allowlist must not delegate to OpenShell")

    backend = OsNativeBackend(
        capability_probe=capability,
        runner=runner,
        openshell_backend_factory=forbidden_openshell,
    )

    with pytest.raises(BackendUnavailable, match="no concrete deny-by-default host-proxy"):
        backend.provision(ProvisionRequest(policy(str(worktree)), run_id="run-no-egress"))

    assert runner.calls == []


def test_os_native_delegated_egress_fails_closed_without_p3_denial_evidence(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    fake = FakeSandboxClient(
        sandbox_id="openshell-sandbox-egress",
        ocsf_records=(
            {
                "event_type": "NET:OPEN",
                "severity": "INFO",
                "disposition": "ALLOWED",
                "target": "api.example:443",
                "policy": "api_example_443",
                "engine": "opa",
                "raw": {"disposition": "ALLOWED", "target": "api.example:443"},
            },
        ),
    )
    backend = OsNativeBackend(
        capability_probe=lambda: (_ for _ in ()).throw(
            AssertionError("egress delegation must not probe os-native")
        ),
        openshell_backend_factory=lambda: OpenShellBackend(client=fake),
    )
    handle = backend.provision(
        ProvisionRequest(policy(str(worktree), egress=True), run_id="run-p3-missing")
    )

    with pytest.raises(BackendUnavailable, match="P3 behavioral denial probe produced no DENIED"):
        backend.run(handle, RunRequest(command=("echo", "hi")))

    assert fake.exec_calls[-1][1] == osn._P3_BLOCKED_PROBE_COMMAND
    assert ("openshell-sandbox-egress", ("echo", "hi")) not in fake.exec_calls


@pytest.mark.parametrize("missing", [("bwrap",), ("landlock",), ("seccomp",), ("proxy",)])
def test_os_native_missing_primitive_refuses_before_side_effects(tmp_path, missing):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    runner = FakeNativeRunner()

    def probe() -> OsNativeCapability:
        return OsNativeCapability(
            platform_name="Linux",
            bwrap_path=None if "bwrap" in missing else "/usr/bin/bwrap",
            landlock_abi=None if "landlock" in missing else 4,
            seccomp_available="seccomp" not in missing,
            proxy_path=None if "proxy" in missing else "/usr/bin/proxy",
            missing=missing,
        )

    backend = OsNativeBackend(capability_probe=probe, runner=runner)

    with pytest.raises(BackendUnavailable, match="missing:"):
        backend.provision(ProvisionRequest(policy(str(worktree)), run_id="run-missing"))

    assert runner.calls == []


def test_os_native_unknown_handle_has_no_unsandboxed_fallback():
    # Option C delegates; there is no native execution path. An unrecognised
    # handle (not in self._delegations) must fail closed, not fall through to
    # an unsandboxed or native bwrap execution.
    runner = FakeNativeRunner()
    backend = OsNativeBackend(capability_probe=capability, runner=runner)
    handle = ProvisionedHandle("os-native", "run-unknown", _POLICY_SHA, "os-native:unknown")

    with pytest.raises(BackendUnavailable, match="no provisioned os-native delegation"):
        backend.run(handle, RunRequest(command=("echo", "hi")))

    assert runner.calls == []


def test_subprocess_os_native_runner_requires_probed_paths_to_exist(tmp_path):
    bwrap = tmp_path / "bwrap"
    proxy = tmp_path / "proxy"
    bwrap.write_text("#!/bin/sh\n", encoding="utf-8")
    runner = SubprocessOsNativeRunner()
    cap = OsNativeCapability("Linux", str(bwrap), 4, True, str(proxy), ())

    assert runner.available(cap) is False
