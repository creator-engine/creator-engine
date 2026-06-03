"""Unit tests for the v3 G-1.2 gVisor + capability-separation egress-proxy backend.

Translate-vs-execute split: the translation is pure and fully tested here; the
backend's live work goes through an injected fake ``ContainerRunner`` so these
tests perform ZERO live subprocess. Fixes the in-repo egress stub: a non-empty
allowlist yields an enforceable deny-by-default proxy config, not a refusal.
"""

import subprocess

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.runner import (
    BackendUnavailable,
    EgressNotEnforceable,
    EgressProxyConfig,
    GVISOR_PROXY_BACKEND_KEY,
    GvisorProxyBackend,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunRequest,
    RunResult,
    RunnerBackend,
    RunscPlan,
    available_backends,
    get_backend,
    translate_to_egress_proxy_config,
    translate_to_runsc_plan,
)

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


class FakeRunner:
    """An injected ContainerRunner — records calls; never touches a real runtime."""

    def __init__(self, available=True, egress_enforceable=True, returncode=0, stdout="ok", stderr=""):
        self._available = available
        self._egress = egress_enforceable
        self._rc = returncode
        self._out = stdout
        self._err = stderr
        self.calls: list[list[str]] = []

    def available(self) -> bool:
        return self._available

    def egress_enforceable(self) -> bool:
        return self._egress

    def run(self, argv, input_text=None) -> subprocess.CompletedProcess:
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), self._rc, stdout=self._out, stderr=self._err)


# ---------------------------------------------------------------------------
# Pure translation
# ---------------------------------------------------------------------------
def test_translate_runsc_plan_hardened():
    plan = translate_to_runsc_plan(valid_policy())
    assert isinstance(plan, RunscPlan)
    assert plan.runtime == "runsc"
    assert plan.platform == "systrap"  # no KVM
    assert plan.image_ref == f"registry.example/creator-engine/implementer@{_IMAGE_SHA}"
    assert plan.read_only_root and plan.no_new_privileges and plan.drop_all_capabilities
    assert plan.network == "proxy"  # has egress
    modes = {(m.source, m.mode) for m in plan.mounts}
    assert ("/runtime/worktree", "rw") in modes and ("governance", "ro") in modes


def test_translate_runsc_argv_carries_hardening():
    argv = translate_to_runsc_plan(valid_policy()).runsc_argv(("echo", "hi"))
    assert "--platform=systrap" in argv
    assert "--network=proxy" in argv
    assert "--read-only" in argv
    assert "--no-new-privs" in argv
    assert "--drop-caps=all" in argv
    assert argv[-2:] == ("echo", "hi")


def test_translate_no_egress_network_none():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    assert translate_to_runsc_plan(policy).network == "none"


def test_translate_egress_proxy_deny_by_default():
    cfg = translate_to_egress_proxy_config(valid_policy())
    assert isinstance(cfg, EgressProxyConfig)
    assert cfg.deny_by_default is True
    assert not cfg.no_egress
    assert len(cfg.rules) == 2
    l7 = [r for r in cfg.rules if "l7" in r.assurance][0]
    assert l7.tls_terminated is True
    l4 = [r for r in cfg.rules if "l4" in r.assurance][0]
    assert l4.host == "model-provider.example" and l4.port == 443


def test_translate_empty_allowlist_is_no_egress():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    cfg = translate_to_egress_proxy_config(policy)
    assert cfg.deny_by_default is True
    assert cfg.no_egress is True
    assert cfg.rules == ()


def test_egress_stub_fixed_non_empty_allowlist_is_enforceable_not_refused():
    # The v2 worker_runtime path REFUSES a non-empty allowlist (no primitive).
    # The v3 translation yields an enforceable deny-by-default config instead.
    cfg = translate_to_egress_proxy_config(valid_policy())
    assert cfg.rules and cfg.deny_by_default is True


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def test_gvisor_proxy_registered_alongside_local_noop():
    assert GVISOR_PROXY_BACKEND_KEY == "gvisor-proxy"
    backends = available_backends()
    assert "gvisor-proxy" in backends
    assert "local-noop" in backends  # G-1.1 backend still works
    backend = get_backend("gvisor-proxy")
    assert isinstance(backend, GvisorProxyBackend)
    assert isinstance(backend, RunnerBackend)


# ---------------------------------------------------------------------------
# Backend — deny-guard, availability gate, egress enforceability
# ---------------------------------------------------------------------------
def test_provision_clean_policy_binds_policy_sha():
    backend = GvisorProxyBackend(runner=FakeRunner())
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    assert isinstance(handle, ProvisionedHandle)
    assert handle.backend_key == "gvisor-proxy"
    assert handle.policy_sha == _POLICY_SHA
    assert handle.ref.startswith("gvisor:")


def test_provision_rejects_controller_key_secret():
    backend = GvisorProxyBackend(runner=FakeRunner())
    bad = valid_policy()
    bad["secret_allowlist"] = ["controller-private-key"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-2"))


def test_provision_rejects_unpinned_image():
    backend = GvisorProxyBackend(runner=FakeRunner())
    bad = valid_policy()
    del bad["image_ref"]["sha"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-3"))


def test_provision_unavailable_runtime_refuses():
    backend = GvisorProxyBackend(runner=FakeRunner(available=False))
    with pytest.raises(BackendUnavailable):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-4"))


def test_provision_non_empty_egress_without_proxy_refuses():
    backend = GvisorProxyBackend(runner=FakeRunner(available=True, egress_enforceable=False))
    with pytest.raises(EgressNotEnforceable):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-5"))
    assert issubclass(EgressNotEnforceable, BackendUnavailable)


def test_provision_empty_egress_without_proxy_is_allowed():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    backend = GvisorProxyBackend(runner=FakeRunner(available=True, egress_enforceable=False))
    handle = backend.provision(ProvisionRequest(runtime_policy=policy, run_id="run-6"))
    assert handle.ref.startswith("gvisor:")  # no egress to enforce → provisions fine


# ---------------------------------------------------------------------------
# Lifecycle through the injected runner
# ---------------------------------------------------------------------------
def test_full_lifecycle_through_injected_runner():
    fake = FakeRunner(returncode=0, stdout="hello")
    backend = GvisorProxyBackend(runner=fake)
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-7"))
    result = backend.run(handle, RunRequest(command=("echo", "hi")))
    assert isinstance(result, RunResult)
    assert result.exit_code == 0 and result.stdout == "hello"
    assert fake.calls and fake.calls[0][0] == "runsc"  # the injected runner saw a runsc argv
    assert "--platform=systrap" in fake.calls[0]
    evidence = backend.collect(handle)
    assert evidence.handle_ref == handle.ref
    teardown = backend.teardown(handle)
    assert teardown.released is True


def test_no_live_subprocess(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("G-1.2 backend must not invoke a live subprocess in CI")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    backend = GvisorProxyBackend(runner=FakeRunner())
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-8"))
    backend.run(handle, RunRequest(command=("echo", "hi")))
    backend.collect(handle)
    backend.teardown(handle)


# ---------------------------------------------------------------------------
# Importing the adapter registers no validator check
# ---------------------------------------------------------------------------
def test_importing_runner_registers_no_check():
    names = set(registered_checks())
    assert "ce_runtime_policy" in names
    assert not any("runner" in n or "backend" in n or "gvisor" in n for n in names)
