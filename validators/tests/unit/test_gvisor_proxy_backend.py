"""Unit tests for the v3 G-1.2 gVisor runner backend.

Translate-vs-execute split: the translation is pure and fully tested here; the
backend's live work goes through an injected fake ``ContainerRunner`` so these
tests perform ZERO live subprocess. Non-empty egress allowlists fail closed
unless the runner proves a real allowlist enforcement primitive.
"""

import subprocess
import shutil

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
    RunscPlanRejected,
    SubprocessContainerRunner,
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
            {"path": "/runtime/governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "port": 443, "protocol": "https", "assurance": ["l4"]},
            {"host": "pkg.example", "protocol": "https", "assurance": ["l7"], "tls_terminated": True},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def plan_inputs(**overrides) -> dict:
    inputs = {
        "uid": 1001,
        "gid": 1002,
        "runtime_name": "runsc-gvproxy-ptrace",
        "host_codex_home": "/host/codex-home",
        "host_codex_bin": "/host/codex-bin/codex",
        "container_home": "/home/cedev4",
        "container_codex_home": "/home/cedev4/.codex",
        "container_workdir": "/runtime/worktree",
        "codex_home_mode": "rw",
    }
    inputs.update(overrides)
    return inputs


def plan_from(policy: dict | None = None, **overrides) -> RunscPlan:
    return translate_to_runsc_plan(policy or valid_policy(), **plan_inputs(**overrides))


def backend_with_inputs(runner=None, **overrides) -> GvisorProxyBackend:
    return GvisorProxyBackend(runner=runner or FakeRunner(), **plan_inputs(**overrides))


class FakeRunner:
    """An injected ContainerRunner — records calls; never touches a real runtime."""

    def __init__(self, available=True, egress_enforceable=True, returncode=0, stdout="ok", stderr=""):
        self._available = available
        self._egress = egress_enforceable
        self._rc = returncode
        self._out = stdout
        self._err = stderr
        self.calls: list[tuple[str, list[str] | None]] = []

    def available(self) -> bool:
        self.calls.append(("available", None))
        return self._available

    def egress_enforceable(self) -> bool:
        self.calls.append(("egress_enforceable", None))
        return self._egress

    def run(self, argv, input_text=None) -> subprocess.CompletedProcess:
        self.calls.append(("run", list(argv)))
        return subprocess.CompletedProcess(list(argv), self._rc, stdout=self._out, stderr=self._err)

    @property
    def run_calls(self) -> list[list[str]]:
        return [argv for name, argv in self.calls if name == "run" and argv is not None]


def subprocess_runner_with_docker_info(monkeypatch, stdout: str, returncode: int = 0) -> SubprocessContainerRunner:
    monkeypatch.setattr(shutil, "which", lambda binary: f"/usr/bin/{binary}")

    def docker_info(argv, **_kwargs):
        assert argv == ["docker", "info", "--format", "{{json .Runtimes}}"]
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", docker_info)
    return SubprocessContainerRunner(required_runtime="runsc-gvproxy-ptrace")


# ---------------------------------------------------------------------------
# Pure translation
# ---------------------------------------------------------------------------
def test_translate_runsc_plan_hardened():
    plan = plan_from()
    assert isinstance(plan, RunscPlan)
    assert plan.docker_binary == "docker"
    assert plan.runtime_name == "runsc-gvproxy-ptrace"
    assert plan.image_ref == f"registry.example/creator-engine/implementer@{_IMAGE_SHA}"
    assert plan.uid == 1001 and plan.gid == 1002 and plan.user_spec == "1001:1002"
    assert plan.no_new_privileges and plan.drop_all_capabilities
    assert plan.network == "proxy"  # has egress
    assert plan.host_codex_home == "/host/codex-home"
    assert plan.host_codex_bin == "/host/codex-bin/codex"
    modes = {(m.source, m.target, m.mode) for m in plan.mounts}
    assert ("/runtime/worktree", "/runtime/worktree", "rw") in modes
    assert ("/runtime/governance", "/runtime/governance", "ro") in modes


def test_translate_docker_argv_carries_dgx_runsc_shape():
    argv = plan_from().docker_argv(("/usr/local/bin/codex", "exec", "hello"))
    assert argv[:3] == ("docker", "run", "--rm")
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "--cap-drop=ALL" in argv
    assert "--user" in argv and argv[argv.index("--user") + 1] == "1001:1002"
    assert "--workdir" in argv and argv[argv.index("--workdir") + 1] == "/runtime/worktree"
    assert "HOME=/home/cedev4" in argv
    assert "CODEX_HOME=/home/cedev4/.codex" in argv
    assert "type=bind,source=/host/codex-home,target=/home/cedev4/.codex" in argv
    assert "type=bind,source=/host/codex-bin/codex,target=/usr/local/bin/codex,readonly" in argv
    assert "type=bind,source=/runtime/governance,target=/runtime/governance,readonly" in argv
    assert not any(arg.startswith("--network=") for arg in argv)
    assert argv[-4:] == (
        f"registry.example/creator-engine/implementer@{_IMAGE_SHA}",
        "/usr/local/bin/codex",
        "exec",
        "hello",
    )


def test_runsc_argv_alias_renders_docker_shape_for_existing_callers():
    assert plan_from().runsc_argv(("echo", "hi")) == plan_from().docker_argv(("echo", "hi"))


def test_translate_docker_argv_supports_uid_without_gid():
    argv = plan_from(gid=None).docker_argv(("echo", "hi"))
    assert "--user" in argv and argv[argv.index("--user") + 1] == "1001"


def test_translate_no_egress_network_none():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    assert plan_from(policy).network == "none"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"uid": None}, "uid is required"),
        ({"uid": -1}, "uid must be a non-negative integer"),
        ({"runtime_name": "runsc"}, "runtime_name must use the DGX ptrace runtime"),
        ({"runtime_name": "runsc-gvproxy"}, "runtime_name must use the DGX ptrace runtime"),
        ({"host_codex_home": None}, "host_codex_home is required"),
        ({"host_codex_home": "relative/.codex"}, "host_codex_home must be"),
        ({"host_codex_bin": ""}, "host_codex_bin is required"),
        ({"codex_home_mode": "bad"}, "codex_home_mode must be"),
        ({"docker_network": "bridge"}, "docker_network must be omitted"),
    ],
)
def test_translate_runsc_plan_rejects_missing_or_unsafe_required_inputs(overrides, message):
    with pytest.raises(RunscPlanRejected, match=message):
        translate_to_runsc_plan(valid_policy(), **plan_inputs(**overrides))


def test_translate_runsc_plan_rejects_unpinned_image_directly():
    bad = valid_policy()
    bad["image_ref"]["sha"] = "latest"
    with pytest.raises(RunscPlanRejected, match="image_ref.sha"):
        translate_to_runsc_plan(bad, **plan_inputs())


def test_translate_runsc_plan_rejects_relative_docker_mount_directly():
    bad = valid_policy()
    bad["mount_manifest"][0]["path"] = "relative-worktree"
    with pytest.raises(RunscPlanRejected, match=r"mount_manifest\[0\].path"):
        translate_to_runsc_plan(bad, **plan_inputs())


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


def test_translate_non_empty_allowlist_is_config_not_enforcement_proof():
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
    backend = backend_with_inputs()
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    assert isinstance(handle, ProvisionedHandle)
    assert handle.backend_key == "gvisor-proxy"
    assert handle.policy_sha == _POLICY_SHA
    assert handle.ref.startswith("gvisor:")


def test_provision_rejects_controller_key_secret():
    backend = backend_with_inputs()
    bad = valid_policy()
    bad["secret_allowlist"] = ["controller-private-key"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-2"))


def test_provision_rejects_unpinned_image():
    backend = backend_with_inputs()
    bad = valid_policy()
    del bad["image_ref"]["sha"]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-3"))


def test_provision_unavailable_runtime_refuses():
    fake = FakeRunner(available=False)
    backend = backend_with_inputs(fake)
    with pytest.raises(BackendUnavailable):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-4"))
    assert fake.calls == [("egress_enforceable", None), ("available", None)]


def test_subprocess_runner_unavailable_when_docker_lacks_required_runsc_runtime(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda binary: f"/usr/bin/{binary}")

    def docker_info_without_runsc(argv, **_kwargs):
        assert argv == ["docker", "info", "--format", "{{json .Runtimes}}"]
        return subprocess.CompletedProcess(argv, 0, stdout='{"runc": {"path": "runc"}}', stderr="")

    monkeypatch.setattr(subprocess, "run", docker_info_without_runsc)

    runner = SubprocessContainerRunner(required_runtime="runsc-gvproxy-ptrace")

    assert runner.available() is False


def test_subprocess_runner_available_when_required_runsc_runtime_registered(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda binary: f"/usr/bin/{binary}")

    def docker_info_with_runsc(argv, **_kwargs):
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"runc": {"path": "runc"}, "runsc-gvproxy-ptrace": {"path": "runsc"}}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", docker_info_with_runsc)

    runner = SubprocessContainerRunner(required_runtime="runsc-gvproxy-ptrace")

    assert runner.available() is True


def test_subprocess_runner_egress_not_enforceable_with_host_network(monkeypatch):
    runner = subprocess_runner_with_docker_info(
        monkeypatch,
        (
            '{"runsc-gvproxy-ptrace": {"path": "runsc", '
            '"runtimeArgs": ["--network=host", "--egress-proxy=/usr/local/bin/gvproxy"]}}'
        ),
    )

    assert runner.egress_enforceable() is False


def test_subprocess_runner_egress_not_enforceable_without_proxy(monkeypatch):
    runner = subprocess_runner_with_docker_info(
        monkeypatch,
        '{"runsc-gvproxy-ptrace": {"path": "runsc", "runtimeArgs": ["--platform=ptrace"]}}',
    )

    assert runner.egress_enforceable() is False


def test_subprocess_runner_egress_not_enforceable_with_gvproxy_runtime_metadata(monkeypatch):
    runner = subprocess_runner_with_docker_info(
        monkeypatch,
        (
            '{"runsc-gvproxy-ptrace": {"path": "runsc", '
            '"runtimeArgs": ["--platform=ptrace", "--egress-proxy=/usr/local/bin/gvproxy"]}}'
        ),
    )

    assert runner.egress_enforceable() is False


def test_subprocess_runner_egress_not_enforceable_with_policy_metadata_only(monkeypatch):
    runner = subprocess_runner_with_docker_info(
        monkeypatch,
        (
            '{"runsc-gvproxy-ptrace": {"path": "runsc", "network": "isolated", '
            '"egressPolicy": "/etc/creator-engine/egress-policy.json"}}'
        ),
    )

    assert runner.egress_enforceable() is False


@pytest.mark.parametrize(
    ("stdout", "returncode"),
    [
        ("not-json", 0),
        ('{"runc": {"path": "runc"}}', 0),
        ('{"runsc-gvproxy-ptrace": {"path": "runsc"}}', 1),
    ],
)
def test_subprocess_runner_egress_unprobeable_fails_closed(monkeypatch, stdout, returncode):
    runner = subprocess_runner_with_docker_info(monkeypatch, stdout, returncode=returncode)

    assert runner.egress_enforceable() is False


def test_provision_missing_docker_runsc_inputs_refuses_before_availability_probe():
    fake = FakeRunner(available=True)
    backend = GvisorProxyBackend(runner=fake)
    with pytest.raises(BackendUnavailable, match="invalid Docker/runsc plan"):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-missing-inputs"))
    assert fake.calls == []


def test_provision_non_empty_egress_without_proxy_refuses():
    fake = FakeRunner(available=True, egress_enforceable=False)
    backend = backend_with_inputs(fake)
    with pytest.raises(EgressNotEnforceable, match="no allowlist enforcement primitive is proven"):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-5"))
    assert issubclass(EgressNotEnforceable, BackendUnavailable)
    assert fake.calls == [("egress_enforceable", None)]


def test_provision_non_empty_egress_without_primitive_runs_no_command():
    fake = FakeRunner(available=True, egress_enforceable=False)
    backend = backend_with_inputs(fake)

    with pytest.raises(EgressNotEnforceable, match="refusing before container start"):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-no-primitive"))

    assert fake.calls == [("egress_enforceable", None)]


def test_provision_empty_egress_without_proxy_is_allowed():
    policy = valid_policy()
    policy["egress_allowlist"] = []
    fake = FakeRunner(available=True, egress_enforceable=False)
    backend = backend_with_inputs(fake)
    handle = backend.provision(ProvisionRequest(runtime_policy=policy, run_id="run-6"))
    assert handle.ref.startswith("gvisor:")  # no egress to enforce → provisions fine
    assert fake.calls == [("available", None)]


# ---------------------------------------------------------------------------
# Lifecycle through the injected runner
# ---------------------------------------------------------------------------
def test_full_lifecycle_through_injected_runner():
    fake = FakeRunner(returncode=0, stdout="hello")
    backend = backend_with_inputs(fake)
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-7"))
    result = backend.run(handle, RunRequest(command=("echo", "hi")))
    assert isinstance(result, RunResult)
    assert result.exit_code == 0 and result.stdout == "hello"
    run_argv = fake.run_calls[0]
    assert run_argv[0] == "docker"  # the injected runner saw a Docker argv
    assert "--runtime=runsc-gvproxy-ptrace" in run_argv
    assert run_argv[-2:] == ["echo", "hi"]
    evidence = backend.collect(handle)
    assert evidence.handle_ref == handle.ref
    teardown = backend.teardown(handle)
    assert teardown.released is True


def test_run_unknown_handle_refuses_without_docker_exec_fallback():
    fake = FakeRunner(returncode=0, stdout="should-not-run")
    backend = backend_with_inputs(fake)
    handle = ProvisionedHandle(
        backend_key=GVISOR_PROXY_BACKEND_KEY,
        run_id="run-unknown",
        policy_sha=_POLICY_SHA,
        ref="gvisor:unknown",
    )

    with pytest.raises(BackendUnavailable, match="no provisioned Docker/runsc plan"):
        backend.run(handle, RunRequest(command=("echo", "hi")))

    assert fake.calls == []


def test_no_live_subprocess(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("G-1.2 backend must not invoke a live subprocess in CI")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    backend = backend_with_inputs()
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
