"""Unit tests for the plain Docker runner backend.

The Docker backend is pure-translation plus an injected runner seam. These tests
perform no live Docker calls.
"""

from types import SimpleNamespace
import subprocess

import pytest

from creator_engine_validator import runtime_backend_bridge
from creator_engine_validator.runner import (
    BackendUnavailable,
    DOCKER_BACKEND_KEY,
    DockerBackend,
    DockerPlan,
    DockerPlanRejected,
    EgressNotEnforceable,
    PolicyRejected,
    ProvisionRequest,
    ProvisionedHandle,
    RunRequest,
    RunnerBackend,
    available_backends,
    get_backend,
    translate_to_docker_plan,
)

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy(*, egress: bool = False) -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "docker-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "docker",
        "image_ref": {"name": "registry.example/creator-engine/implementer", "sha": _IMAGE_SHA},
        "mount_manifest": [
            {"path": "/runtime/worktree", "mode": "rw", "write_justification": "allocated worktree"},
            {"path": "/runtime/governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "port": 443, "protocol": "https", "assurance": ["l4"]},
        ]
        if egress
        else [],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def plan_inputs(**overrides) -> dict:
    inputs = {
        "uid": 1001,
        "gid": 1002,
        "container_workdir": "/runtime/worktree",
    }
    inputs.update(overrides)
    return inputs


def backend_with_inputs(runner=None, **overrides) -> DockerBackend:
    return DockerBackend(runner=runner or FakeRunner(), **plan_inputs(**overrides))


class FakeRunner:
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

    def runtime_probe(self, *, run_id, argv, surface):
        return {
            "pid": "4242",
            "run_id": run_id,
            "launch_owned": True,
            "probe_contract": "ce-launch-owned-probe-v1",
            "source": "fake-docker-runner",
        }

    @property
    def run_calls(self) -> list[list[str]]:
        return [argv for name, argv in self.calls if name == "run" and argv is not None]


class FakeVisibilityBackend:
    def __init__(self):
        self.spawned: list[tuple[str, str, tuple[str, ...]]] = []

    def is_available(self) -> bool:
        return True

    def ensure_surface(self, *, session, window, command, cwd, env, seat_dir):
        del cwd, env, seat_dir
        self.spawned.append((session, window, tuple(command)))
        return SimpleNamespace(pane_pid=4242)


def test_translate_docker_plan_hardened_without_runtime_or_host_codex_binds():
    plan = translate_to_docker_plan(valid_policy(), **plan_inputs())
    assert isinstance(plan, DockerPlan)
    assert plan.image_ref == f"registry.example/creator-engine/implementer@{_IMAGE_SHA}"
    assert plan.uid == 1001 and plan.gid == 1002 and plan.user_spec == "1001:1002"
    assert plan.no_new_privileges and plan.drop_all_capabilities and plan.read_only_rootfs
    assert plan.network == "none"

    argv = plan.docker_argv(("codex", "exec", "hello"))

    assert argv[:3] == ("docker", "run", "--rm")
    assert not any(arg.startswith("--runtime") for arg in argv)
    assert "--security-opt=no-new-privileges" in argv
    assert "--cap-drop=ALL" in argv
    assert "--user" in argv and argv[argv.index("--user") + 1] == "1001:1002"
    assert "--workdir" in argv and argv[argv.index("--workdir") + 1] == "/runtime/worktree"
    assert "--read-only" in argv
    assert "--tmpfs" in argv and argv[argv.index("--tmpfs") + 1].startswith("/tmp:")
    assert "--network=none" in argv
    assert "type=bind,source=/runtime/worktree,target=/runtime/worktree" in argv
    assert "type=bind,source=/runtime/governance,target=/runtime/governance,readonly" in argv
    assert not any("/host/codex" in arg or "/usr/local/bin/codex" in arg for arg in argv)
    assert argv[-4:] == (
        f"registry.example/creator-engine/implementer@{_IMAGE_SHA}",
        "codex",
        "exec",
        "hello",
    )


def test_docker_argv_raises_on_proxy_network_fail_closed_lock():
    """Fail-closed lock: docker_argv must never render a 'proxy' network plan.

    Today this network value is unreachable via DockerBackend.provision because
    SubprocessDockerRunner.egress_enforceable() is hardcoded False, so
    provisioning refuses before a plan with network=='proxy' ever reaches
    docker_argv (see test_provision_non_empty_egress_without_primitive_refuses_before_available,
    which this test does not weaken). This test locks the latent branch directly:
    if a future runner claims egress_enforceable()=True, docker_argv must still
    refuse to render rather than silently emit a default (open) bridge network
    labeled governed.
    """
    plan = translate_to_docker_plan(valid_policy(egress=True), **plan_inputs())
    assert plan.network == "proxy"

    with pytest.raises(DockerPlanRejected, match="docker-side egress mediation is not yet implemented"):
        plan.docker_argv(("codex", "exec", "hello"))


def test_translate_docker_plan_image_ref_comes_only_from_policy():
    bad = valid_policy()
    del bad["image_ref"]["sha"]
    with pytest.raises(DockerPlanRejected, match="image_ref.sha"):
        translate_to_docker_plan(bad, **plan_inputs())


def test_translate_docker_plan_rejects_relative_mount_directly():
    bad = valid_policy()
    bad["mount_manifest"][0]["path"] = "relative-worktree"
    with pytest.raises(DockerPlanRejected, match=r"mount_manifest\[0\].path"):
        translate_to_docker_plan(bad, **plan_inputs())


def test_docker_backend_registered():
    assert DOCKER_BACKEND_KEY == "docker"
    assert "docker" in available_backends()
    backend = get_backend("docker")
    assert isinstance(backend, DockerBackend)
    assert isinstance(backend, RunnerBackend)


def test_provision_rejects_forbidden_mount_via_runtime_policy():
    backend = backend_with_inputs()
    bad = valid_policy()
    bad["mount_manifest"] = [{"path": "/var/run/docker.sock", "mode": "ro"}]
    with pytest.raises(PolicyRejected):
        backend.provision(ProvisionRequest(runtime_policy=bad, run_id="run-forbidden"))


def test_provision_non_empty_egress_without_primitive_refuses_before_available():
    fake = FakeRunner(available=True, egress_enforceable=False)
    backend = backend_with_inputs(fake)
    with pytest.raises(EgressNotEnforceable, match="no allowlist enforcement primitive is proven"):
        backend.provision(ProvisionRequest(runtime_policy=valid_policy(egress=True), run_id="run-egress"))
    assert issubclass(EgressNotEnforceable, BackendUnavailable)
    assert fake.calls == [("egress_enforceable", None)]


def test_full_lifecycle_through_injected_runner():
    fake = FakeRunner(returncode=0, stdout="hello")
    backend = backend_with_inputs(fake)
    handle = backend.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id="run-1"))
    result = backend.run(handle, RunRequest(command=("echo", "hi")))

    assert result.exit_code == 0 and result.stdout == "hello"
    run_argv = fake.run_calls[0]
    assert run_argv[0] == "docker"
    assert not any(arg.startswith("--runtime") for arg in run_argv)
    assert "--name" in run_argv
    assert run_argv[-2:] == ["echo", "hi"]
    assert backend.collect(handle).handle_ref == handle.ref
    assert backend.teardown(handle).released is True


def test_run_unknown_handle_refuses_without_fallback():
    fake = FakeRunner(returncode=0, stdout="should-not-run")
    backend = backend_with_inputs(fake)
    handle = ProvisionedHandle(
        backend_key=DOCKER_BACKEND_KEY,
        run_id="run-unknown",
        policy_sha=_POLICY_SHA,
        ref="docker:unknown",
    )

    with pytest.raises(BackendUnavailable, match="no provisioned Docker plan"):
        backend.run(handle, RunRequest(command=("echo", "hi")))

    assert fake.calls == []


def test_bridge_honors_docker_backend_without_host_codex_bind(monkeypatch):
    monkeypatch.setattr(
        runtime_backend_bridge,
        "_probe_launched_surface_containment",
        lambda *args, **kwargs: {"contained": True, "reason": "test"},
    )
    visibility = FakeVisibilityBackend()

    result = runtime_backend_bridge.run_visible_runtime(
        resolved_backend="docker",
        runtime_policy=valid_policy(),
        run_id="run-visible",
        command=("codex", "exec", "hello"),
        visibility_backend=visibility,
        session="s",
        window="w",
        container_runner=FakeRunner(),
        gvisor_plan_kwargs={
            "uid": 1001,
            "gid": 1002,
            "host_codex_home": "/host/codex-home",
            "host_codex_bin": "/host/codex-bin/codex",
            "container_workdir": "/runtime/worktree",
        },
    )

    assert result.backend_key == "docker"
    assert result.containment_attestation["contained"] is True
    assert visibility.spawned and visibility.spawned[0][2] == result.argv
    assert not any(arg.startswith("--runtime") for arg in result.argv)
    assert not any("/host/codex" in arg or "/usr/local/bin/codex" in arg for arg in result.argv)


def test_bridge_still_refuses_unknown_runtime_backend():
    with pytest.raises(runtime_backend_bridge.RuntimeBackendBridgeError, match="refusing raw fallback"):
        runtime_backend_bridge.run_visible_runtime(
            resolved_backend="local-noop",
            runtime_policy=valid_policy(),
            run_id="run-refuse",
            command=("echo", "hi"),
            visibility_backend=FakeVisibilityBackend(),
            session="s",
            window="w",
            container_runner=FakeRunner(),
            gvisor_plan_kwargs=plan_inputs(),
        )
