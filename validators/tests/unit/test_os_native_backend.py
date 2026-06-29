"""Fail-closed tests for the OQ-1 Option A os-native runner backend."""

import subprocess

import pytest

from creator_engine_validator.runner import BackendUnavailable, ProvisionRequest, ProvisionedHandle, RunRequest
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

    with pytest.raises(BackendUnavailable, match="restrictive seccomp policy"):
        backend.provision(ProvisionRequest(policy(str(worktree), egress=True), run_id="run-egress"))

    assert runner.calls == []


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
    runner = FakeNativeRunner()
    backend = OsNativeBackend(capability_probe=capability, runner=runner)
    handle = ProvisionedHandle("os-native", "run-unknown", _POLICY_SHA, "os-native:unknown")

    with pytest.raises(BackendUnavailable, match="no provisioned os-native sandbox plan"):
        backend.run(handle, RunRequest(command=("echo", "hi")))

    assert runner.calls == []


def test_subprocess_os_native_runner_requires_probed_paths_to_exist(tmp_path):
    bwrap = tmp_path / "bwrap"
    proxy = tmp_path / "proxy"
    bwrap.write_text("#!/bin/sh\n", encoding="utf-8")
    runner = SubprocessOsNativeRunner()
    cap = OsNativeCapability("Linux", str(bwrap), 4, True, str(proxy), ())

    assert runner.available(cap) is False
