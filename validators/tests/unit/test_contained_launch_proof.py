"""ce-ops#128/#221 contained-launch proof tests.

These tests join the launch-runner integration seam to the containment-probe
seam with mocked runtime and /proc evidence. CI does not need Docker, runsc, or
live namespace creation; the proof is that launch routes the seat through the
gVisor runner path and the containment verdict comes from positive kernel-style
evidence instead of a launch assertion.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator.tmux_adapter import TmuxPane


_FULL_CAP = "000001ffffffffff"
_DROPPED_CAP = "00000000a80425fb"


class ProofTmuxAdapter:
    kind = "tmux"

    def __init__(self, *, pane_pid: int = 5151, available: bool = True):
        self._available = available
        self._pane_pid = pane_pid
        self.spawned: list[dict] = []

    def is_available(self) -> bool:
        return self._available

    def session_exists(self, session: str) -> bool:
        return False

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append(
            {
                "session": session,
                "window": window,
                "command": list(command),
                "cwd": cwd,
                "env": dict(env) if env is not None else None,
            }
        )
        return TmuxPane(
            session_id="$proof",
            window_id="@proof",
            pane_id="%proof",
            pane_pid=self._pane_pid,
        )


class ProofContainerRunner:
    def __init__(
        self,
        *,
        available: bool = True,
        egress_enforceable: bool = True,
        runtime_probe_pid: int | None = None,
        runtime_probe_run_id: str | None = None,
    ):
        self._available = available
        self._egress_enforceable = egress_enforceable
        self._runtime_probe_pid = runtime_probe_pid
        self._runtime_probe_run_id = runtime_probe_run_id
        self.available_calls = 0
        self.egress_calls = 0
        self.raw_run_calls = 0
        self.runtime_probe_calls = 0

    def available(self) -> bool:
        self.available_calls += 1
        return self._available

    def egress_enforceable(self) -> bool:
        self.egress_calls += 1
        return self._egress_enforceable

    def run(self, argv, input_text=None):
        self.raw_run_calls += 1
        raise AssertionError("runtime bridge must start runsc argv on the visibility backend")

    def runtime_probe(self, *, run_id, argv, surface):
        self.runtime_probe_calls += 1
        if self._runtime_probe_pid is None:
            return None
        return {
            "pid": self._runtime_probe_pid,
            "run_id": self._runtime_probe_run_id or run_id,
            "source": "proof-container-runner",
        }


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _status(cap_eff: str, cap_bnd: str, nnp: str = "0") -> str:
    return (
        "Name:\tproof\n"
        f"NoNewPrivs:\t{nnp}\n"
        f"CapEff:\t{cap_eff}\n"
        f"CapBnd:\t{cap_bnd}\n"
    )


def _make_proc(
    tmp_path: Path,
    pid: str,
    *,
    ns: dict[str, str],
    cgroup: str,
    status: str,
    root: str,
    cmdline: str | None = None,
    comm: str | None = None,
) -> None:
    base = tmp_path / pid
    for name, ident in ns.items():
        _write(base / "ns" / name, ident)
    _write(base / "cgroup", cgroup)
    _write(base / "status", status)
    _write(base / "root", root)
    if cmdline is not None:
        _write(base / "cmdline", "\0".join(cmdline.split(" ")) + "\0")
    if comm is not None:
        _write(base / "comm", comm + "\n")


def _host_proc(proc_root: Path) -> None:
    _make_proc(
        proc_root,
        "1",
        ns={
            "mnt": "mnt:[4026531840]",
            "pid": "pid:[4026531836]",
            "net": "net:[4026531992]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/init.scope\n",
        status=_status(_FULL_CAP, _FULL_CAP),
        root="/",
    )


def _gvisor_proc(proc_root: Path, pid: str) -> None:
    _make_proc(
        proc_root,
        pid,
        ns={
            "mnt": "mnt:[4026532500]",
            "pid": "pid:[4026532501]",
            "net": "net:[4026532502]",
            "user": "user:[4026532503]",
        },
        cgroup="0::/system.slice/runsc-sandbox-proof.scope/runsc/container\n",
        status=_status(_DROPPED_CAP, _DROPPED_CAP, nnp="1"),
        root="/run/runsc/proof/rootfs",
        cmdline="runsc-sandbox --platform=ptrace --root=/var/run/docker/runsc boot",
        comm="runsc-sandbox",
    )


def _raw_host_proc(proc_root: Path, pid: str) -> None:
    _make_proc(
        proc_root,
        pid,
        ns={
            "mnt": "mnt:[4026531840]",
            "pid": "pid:[4026531836]",
            "net": "net:[4026531992]",
            "user": "user:[4026531837]",
        },
        cgroup="0::/user.slice/user-1000.slice/session-3.scope\n",
        status=_status(_FULL_CAP, _FULL_CAP),
        root="/",
    )


def _write_runtime_policy(tmp_path: Path, *, backend: str | None = "gvisor-proxy") -> Path:
    policy = {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "contained-launch-proof",
        "policy_sha": "a" * 64,
        "role": "implementer",
        "image_ref": {
            "name": "registry.example/creator-engine/implementer",
            "sha": "sha256:" + "b" * 64,
        },
        "mount_manifest": [
            {
                "path": "/runtime/worktree",
                "mode": "rw",
                "write_justification": "allocated worktree for this seat",
            },
            {"path": "/runtime/governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "protocol": "https", "assurance": ["l4"]},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }
    if backend is not None:
        policy["isolation_backend"] = backend
    path = tmp_path / "runtime-policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=True), encoding="utf-8")
    return path


def _gvisor_plan_kwargs() -> dict:
    return {
        "uid": 1001,
        "gid": 1002,
        "host_codex_home": "/host/codex-home",
        "host_codex_bin": "/host/codex-bin/codex",
        "container_workdir": "/runtime/worktree",
    }


def _disable_brain_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr(ce_cli.launch_runtime, "_build_controller_brain_bootstrap", lambda _root: None)


def _probe_json(pid: int, proc_root: Path, capsys) -> tuple[int, dict]:
    rc = ce_cli.main(
        [
            "containment-probe",
            str(pid),
            "--proc-root",
            str(proc_root),
            "--host-pid",
            "1",
            "--json",
        ]
    )
    return rc, json.loads(capsys.readouterr().out)


def test_gvisor_launch_spawns_harness_inside_runsc_and_probe_proves_containment(
    tmp_path, monkeypatch, capsys
):
    _disable_brain_bootstrap(monkeypatch)
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _gvisor_proc(proc_root, "5151")
    policy = _write_runtime_policy(tmp_path)
    adapter = ProofTmuxAdapter(pane_pid=4242)
    runner = ProofContainerRunner(runtime_probe_pid=5151)

    result = ce_cli.launch_runtime.launch(
        harness="hermes",
        session="proof",
        window="seat",
        runtime_policy=policy,
        backend="gvisor",
        repo_root=tmp_path,
        tmux_adapter=adapter,
        container_runner=runner,
        gvisor_plan_kwargs=_gvisor_plan_kwargs(),
        containment_proc_root=proc_root,
    )

    assert result.spawned is True
    assert result.terminal["pane_pid"] == 4242
    assert result.runner_runtime["backend_key"] == "gvisor-proxy"
    assert result.runner_runtime["runtime_probe"]["pid"] == 5151
    assert runner.available_calls == 1
    assert runner.egress_calls == 1
    assert runner.raw_run_calls == 0
    assert runner.runtime_probe_calls == 1

    assert len(adapter.spawned) == 1
    docker_argv = adapter.spawned[0]["command"]
    assert docker_argv[:3] == ["docker", "run", "--rm"]
    assert "--runtime=runsc-gvproxy-ptrace" in docker_argv
    image_ref = "registry.example/creator-engine/implementer@sha256:" + "b" * 64
    image_index = docker_argv.index(image_ref)
    assert docker_argv[image_index + 1] == "/bin/sh"
    assert result.plan.command[0] == "hermes"
    assert docker_argv[image_index + 1 :] != result.plan.command

    rc, verdict = _probe_json(5151, proc_root, capsys)
    assert rc == 0
    assert verdict["contained"] is True
    assert verdict["backend"] == "gvisor"
    assert verdict["isolation"]["mnt"] is True
    assert verdict["isolation"]["caps"] is True


def test_raw_launch_probe_fails_closed_on_uncontained_host_process(tmp_path, monkeypatch, capsys):
    _disable_brain_bootstrap(monkeypatch)
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _raw_host_proc(proc_root, "4242")
    adapter = ProofTmuxAdapter(pane_pid=5151)

    result = ce_cli.launch_runtime.launch(
        harness="hermes",
        session="raw-proof",
        window="seat",
        repo_root=tmp_path,
        tmux_adapter=adapter,
    )

    assert result.spawned is True
    assert result.runner_runtime is None
    assert adapter.spawned[0]["command"][0] == "/bin/sh"

    rc, verdict = _probe_json(4242, proc_root, capsys)
    assert rc == 1
    assert verdict["contained"] is False
    assert verdict["backend"] == "none"
    assert "fail-closed" in verdict["reason"]


def test_gvisor_launch_refuses_unhonored_backend_before_raw_visibility_spawn(
    tmp_path, monkeypatch
):
    _disable_brain_bootstrap(monkeypatch)
    policy = _write_runtime_policy(tmp_path)
    adapter = ProofTmuxAdapter()
    runner = ProofContainerRunner(available=False)

    try:
        ce_cli.launch_runtime.launch(
            harness="hermes",
            session="proof-refusal",
            window="seat",
            runtime_policy=policy,
            backend="gvisor",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=runner,
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
        )
    except ce_cli.launch_runtime.RuntimePolicyRefused as exc:
        assert "not available" in str(exc)
    else:  # pragma: no cover - the assertion above is the proof
        raise AssertionError("gVisor launch must refuse when the backend is unavailable")

    assert runner.available_calls == 1
    assert runner.raw_run_calls == 0
    assert adapter.spawned == []


def test_gvisor_launch_refuses_when_post_launch_probe_sees_raw_host_pid(
    tmp_path, monkeypatch
):
    _disable_brain_bootstrap(monkeypatch)
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _raw_host_proc(proc_root, "4242")
    _gvisor_proc(proc_root, "5151")
    policy = _write_runtime_policy(tmp_path)
    adapter = ProofTmuxAdapter(pane_pid=5151)
    runner = ProofContainerRunner(runtime_probe_pid=4242)

    try:
        ce_cli.launch_runtime.launch(
            harness="hermes",
            session="proof-raw-refusal",
            window="seat",
            runtime_policy=policy,
            backend="gvisor",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=runner,
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
            containment_proc_root=proc_root,
        )
    except ce_cli.launch_runtime.RuntimePolicyRefused as exc:
        text = str(exc)
        assert "failed containment probe" in text
        assert "mnt namespace shared with host" in text
    else:  # pragma: no cover - assertion above is the proof
        raise AssertionError("contained launch must refuse a raw host pid")

    assert runner.available_calls == 1
    assert runner.egress_calls == 1
    assert runner.raw_run_calls == 0
    assert adapter.spawned


def test_gvisor_launch_refuses_when_detached_pane_pid_has_no_launch_owned_probe(
    tmp_path, monkeypatch
):
    _disable_brain_bootstrap(monkeypatch)
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _gvisor_proc(proc_root, "5151")
    policy = _write_runtime_policy(tmp_path)
    adapter = ProofTmuxAdapter(pane_pid=5151)
    runner = ProofContainerRunner()

    try:
        ce_cli.launch_runtime.launch(
            harness="hermes",
            session="proof-detached-pid-refusal",
            window="seat",
            runtime_policy=policy,
            backend="gvisor",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=runner,
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
            containment_proc_root=proc_root,
        )
    except ce_cli.launch_runtime.RuntimePolicyRefused as exc:
        assert "no launch-owned runtime probe pid" in str(exc)
    else:  # pragma: no cover - assertion above is the proof
        raise AssertionError("contained launch must refuse detached pane_pid proof")

    assert runner.available_calls == 1
    assert runner.egress_calls == 1
    assert runner.raw_run_calls == 0
    assert runner.runtime_probe_calls == 1
    assert adapter.spawned


def test_gvisor_launch_refuses_unprobeable_proc_data(
    tmp_path, monkeypatch
):
    _disable_brain_bootstrap(monkeypatch)
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    policy = _write_runtime_policy(tmp_path)
    adapter = ProofTmuxAdapter(pane_pid=7373)
    runner = ProofContainerRunner(runtime_probe_pid=7373)

    try:
        ce_cli.launch_runtime.launch(
            harness="hermes",
            session="proof-unprobeable-refusal",
            window="seat",
            runtime_policy=policy,
            backend="gvisor",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=runner,
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
            containment_proc_root=proc_root,
        )
    except ce_cli.launch_runtime.RuntimePolicyRefused as exc:
        text = str(exc)
        assert "failed containment probe" in text
        assert "mnt-namespace undeterminable" in text
    else:  # pragma: no cover - assertion above is the proof
        raise AssertionError("contained launch must refuse unprobeable proc data")

    assert runner.available_calls == 1
    assert runner.egress_calls == 1
    assert runner.raw_run_calls == 0
    assert runner.runtime_probe_calls == 1
    assert adapter.spawned


def test_gvisor_launch_refuses_runtime_probe_bound_to_wrong_run_id(
    tmp_path, monkeypatch
):
    _disable_brain_bootstrap(monkeypatch)
    proc_root = tmp_path / "proc"
    _host_proc(proc_root)
    _gvisor_proc(proc_root, "5151")
    policy = _write_runtime_policy(tmp_path)
    adapter = ProofTmuxAdapter(pane_pid=5151)
    runner = ProofContainerRunner(runtime_probe_pid=5151, runtime_probe_run_id="other-run")

    try:
        ce_cli.launch_runtime.launch(
            harness="hermes",
            session="proof-wrong-run-refusal",
            window="seat",
            runtime_policy=policy,
            backend="gvisor",
            repo_root=tmp_path,
            tmux_adapter=adapter,
            container_runner=runner,
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
            containment_proc_root=proc_root,
        )
    except ce_cli.launch_runtime.RuntimePolicyRefused as exc:
        assert "not bound to run_id" in str(exc)
    else:  # pragma: no cover - assertion above is the proof
        raise AssertionError("contained launch must refuse a mismatched runtime probe")

    assert runner.available_calls == 1
    assert runner.egress_calls == 1
    assert runner.raw_run_calls == 0
    assert runner.runtime_probe_calls == 1
    assert adapter.spawned
