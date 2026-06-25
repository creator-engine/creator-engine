"""Unit tests for the Gate 3 governed lane-launch runtime (RV1-030/031/032).

These exercise ``lane_runtime`` directly with a tmux test double. The full
CLI surface and a real-tmux launch are covered by the CLI / integration
suites. No production worktree, ledger, or tmux session is mutated; all
state lives under pytest ``tmp_path``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, lane_runtime
from creator_engine_validator.checks.pane_registry import validate_pane_registry_record
from creator_engine_validator.tmux_adapter import TmuxPane


# ---------------------------------------------------------------------------
# Test doubles + fixtures
# ---------------------------------------------------------------------------

_FULL_CAP = "000001ffffffffff"
_DROPPED_CAP = "00000000a80425fb"


class FakeAdapter:
    """In-memory tmux adapter double: records spawns, never touches tmux."""

    kind = "tmux"

    def __init__(self, *, available: bool = True):
        self._available = available
        self.spawned: list[tuple[str, str, list[str]]] = []
        self.last_env = None

    def is_available(self) -> bool:
        return self._available

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command)))
        self.last_cwd = cwd
        self.last_env = dict(env) if env else None
        return TmuxPane(
            session_id="$1",
            window_id="@2",
            pane_id="%3",
            pane_tty="/dev/pts/9",
            pane_pid=4242,
            pane_cwd=(str(cwd) if cwd else None),
        )


class FakeContainerRunner:
    def __init__(
        self,
        *,
        available: bool = True,
        egress_enforceable: bool = True,
        runtime_probe_pid: int | None = None,
    ):
        self._available = available
        self._egress = egress_enforceable
        self._runtime_probe_pid = runtime_probe_pid

    def available(self) -> bool:
        return self._available

    def egress_enforceable(self) -> bool:
        return self._egress

    def run(self, argv, input_text=None):  # pragma: no cover - bridge must not call it
        raise AssertionError("visible bridge should route runsc argv through tmux")

    def runtime_probe(self, *, run_id, argv, surface):
        if self._runtime_probe_pid is None:
            return None
        return {
            "pid": self._runtime_probe_pid,
            "run_id": run_id,
            "source": "fake-container-runner",
        }


def _write_prompt(tmp_path: Path, text: str = "governed gate prompt body\n") -> tuple[Path, str]:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(prompt.read_bytes()).hexdigest()
    return prompt, sha


def _write_brain_ledger(state_root: Path, *, object_value: str = "ready") -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-lane-runtime-0001",
        claim={"subject": "lane", "predicate": "bootstrap", "object": object_value},
        scope="global",
        evidence_ref="validators/tests/unit/test_lane_runtime.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def _ledger_root(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_claim(
    ledger_root: Path,
    controller_id: str,
    lane_id: str,
    *,
    worktree_path: str = "/worktrees/gate3-lane",
    branch: str = "implementer/gate3-lane",
    envelope_ref: str = "envelopes/gate3.md",
    released: bool = False,
) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_timestamp": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "worktree_path": worktree_path,
        "envelope_ref": envelope_ref,
        "branch": branch,
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
    }
    if released:
        record["released_at"] = "2026-05-25T04:05:00Z"
        record["release_reason"] = "completed"
    path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _write_runtime_policy(tmp_path: Path, *, backend: str = "gvisor-proxy") -> Path:
    policy = {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": "a" * 64,
        "role": "implementer",
        "isolation_backend": backend,
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
    path = tmp_path / "runtime-policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=True), encoding="utf-8")
    return path


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
) -> None:
    base = tmp_path / pid
    for name, ident in ns.items():
        _write(base / "ns" / name, ident)
    _write(base / "cgroup", cgroup)
    _write(base / "status", status)
    _write(base / "root", root)


def _contained_proc(tmp_path: Path, pid: str) -> None:
    _make_proc(
        tmp_path,
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
    _make_proc(
        tmp_path,
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
    )


def _gvisor_plan_kwargs() -> dict:
    return {
        "uid": 1001,
        "gid": 1002,
        "host_codex_home": "/host/codex-home",
        "host_codex_bin": "/host/codex-bin/codex",
        "container_workdir": "/runtime/worktree",
    }


def _wrapper_inner_argv(result):
    """Recover the EXACT step-6c output argv embedded in the seat-sentinel wrapper.

    ce-ops#26: the pane command is now ``["/bin/sh", <wrapper>]``; the governed +
    bounded argv runs FOREGROUND inside the wrapper (the line just before
    ``code=$?``), shlex-quoted — these are the ordering teeth.
    """
    import shlex
    from pathlib import Path

    wrapper = Path(result.events_ref).parent / "sentinel-wrapper.sh"
    lines = wrapper.read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    return shlex.split(lines[idx - 1])


def _launch(tmp_path, **overrides):
    prompt, sha = overrides.pop("prompt_and_sha", _write_prompt(tmp_path))
    ledger = overrides.pop("ledger_root", _ledger_root(tmp_path))
    brain_ledger = overrides.pop("brain_ledger", True)
    state_root = Path(overrides.get("state_root", tmp_path / ".ce" / "state"))
    if brain_ledger:
        _write_brain_ledger(state_root)
    kwargs = dict(
        controller_id="hermes-primary",
        lane_id="gate3-lane",
        role="implementer",
        prompt=prompt,
        prompt_sha=sha,
        repo_root=tmp_path,
        ledger_root=ledger,
        tmux_adapter=FakeAdapter(),
    )
    kwargs.update(overrides)
    return lane_runtime.launch(**kwargs)


# ---------------------------------------------------------------------------
# Success path: pane record bound to a live claim
# ---------------------------------------------------------------------------


def test_launch_writes_pane_record_bound_to_live_claim(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(tmp_path, ledger_root=ledger)

    pane_path = ledger / "panes" / "hermes-primary" / "gate3-lane.yaml"
    assert pane_path.is_file()
    assert result.pane_path == pane_path
    record = yaml.safe_load(pane_path.read_text(encoding="utf-8"))
    assert record["kind"] == "pane-registry-record"
    assert record["controller_id"] == "hermes-primary"
    assert record["lane_id"] == "gate3-lane"
    assert record["role"] == "implementer"
    assert record["visibility"] == "operator_visible"
    assert record["terminal"]["kind"] == "tmux"
    assert record["terminal"]["session_id"] == "$1"
    assert record["terminal"]["window_id"] == "@2"
    assert record["terminal"]["pane_id"] == "%3"
    # bound to the claim
    assert record["claim_ref"] == "claims/hermes-primary/gate3-lane.yaml"
    assert record["worktree_path"] == "/worktrees/gate3-lane"
    assert record["branch"] == "implementer/gate3-lane"
    assert record["envelope_ref"] == "envelopes/gate3.md"


def test_launch_backend_gvisor_spawns_visible_docker_runsc_path(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    proc_root = tmp_path / "proc"
    _contained_proc(proc_root, "4242")
    adapter = FakeAdapter()
    policy = _write_runtime_policy(tmp_path)

    result = _launch(
        tmp_path,
        ledger_root=ledger,
        tmux_adapter=adapter,
        runtime_policy=policy,
        backend="gvisor",
        container_runner=FakeContainerRunner(runtime_probe_pid=4242),
        gvisor_plan_kwargs=_gvisor_plan_kwargs(),
        containment_proc_root=proc_root,
    )

    assert result.runtime_policy["resolved_backend"] == "gvisor-proxy"
    assert result.runner_runtime["backend_key"] == "gvisor-proxy"
    assert result.runner_runtime["containment_attestation"]["contained"] is True
    argv = result.runner_runtime["argv"]
    assert argv[:3] == ["docker", "run", "--rm"]
    assert "--runtime=runsc-gvproxy-ptrace" in argv
    assert "registry.example/creator-engine/implementer@sha256:" + "b" * 64 in argv
    assert adapter.spawned and adapter.spawned[0][2] == argv
    sidecar = ledger / "panes" / "hermes-primary" / "gate3-lane.claude-governance.json"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["runner_runtime"]["backend_key"] == "gvisor-proxy"
    assert payload["runner_runtime"]["containment_attestation"]["contained"] is True


def test_launch_backend_unavailable_refuses_without_raw_tmux(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    policy = _write_runtime_policy(tmp_path)

    with pytest.raises(lane_runtime.RuntimePolicyRefused, match="not available"):
        _launch(
            tmp_path,
            ledger_root=ledger,
            tmux_adapter=adapter,
            runtime_policy=policy,
            backend="gvisor",
            container_runner=FakeContainerRunner(available=False),
            gvisor_plan_kwargs=_gvisor_plan_kwargs(),
        )

    assert adapter.spawned == []
    _assert_no_pane(ledger)


def test_launch_writes_pane_registry_and_seat_lifecycle_record(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        host_id="ce-dev-2",
        purpose="creator-engine/ce-ops#95",
    )

    assert result.pane_path == ledger / "panes" / "hermes-primary" / "gate3-lane.yaml"
    assert result.pane_path.is_file()
    assert result.seat_lifecycle_state == "alive"
    assert result.seat_record_ref is not None
    record_path = Path(result.seat_record_ref)
    assert record_path == ledger / "seats" / "ce-dev-2" / "gate3-lane.yaml"
    lifecycle = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    assert lifecycle["seat"]["seat_id"] == "gate3-lane"
    assert lifecycle["seat"]["owner_controller_id"] == "hermes-primary"
    assert lifecycle["seat"]["launch_surface"] == "ce_lane_launch"
    assert lifecycle["seat"]["purpose"] == "creator-engine/ce-ops#95"
    assert lifecycle["work"]["pco_claim_ref"] == "claims/hermes-primary/gate3-lane.yaml"
    assert lifecycle["work"]["pco_lease_ref"] == "leases/hermes-primary/gate3-lane.yaml"
    assert lifecycle["work"]["worktree_path"] == "/worktrees/gate3-lane"
    assert lifecycle["dispatch"]["pane_registry_ref"] == str(result.pane_path)
    assert lifecycle["terminal"]["pane_pid"] == 4242
    assert lifecycle["policy"]["policy_id"] == "default-governed-seat-v1"
    event_path = ledger / "seat-events" / "ce-dev-2" / "gate3-lane.ndjson"
    events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
    assert events[0]["event"] == "registered"
    assert events[0]["seat_id"] == "gate3-lane"
    assert events[0]["state"] == "alive"
    assert events[0]["record_ref"] == str(record_path)


def test_written_pane_record_passes_pane_registry_schema(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(tmp_path, ledger_root=ledger)
    errors = validate_pane_registry_record(result.record, result.pane_path)
    assert errors == [], [e.format() for e in errors]


def test_no_tmp_artifact_left_after_pane_write(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    leftover = list((ledger / "panes").rglob("*.tmp.*"))
    assert leftover == []


# ---------------------------------------------------------------------------
# Refusals BEFORE side effects (no pane file, no tmux spawn)
# ---------------------------------------------------------------------------


def _assert_no_pane(ledger: Path, controller="hermes-primary", lane="gate3-lane"):
    assert not (ledger / "panes" / controller / f"{lane}.yaml").exists()


def test_launch_refuses_prompt_sha_mismatch_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    prompt, _ = _write_prompt(tmp_path)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.PromptShaMismatch):
        _launch(
            tmp_path,
            ledger_root=ledger,
            prompt_and_sha=(prompt, "0" * 64),
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_missing_prompt_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.PromptMissing):
        _launch(
            tmp_path,
            ledger_root=ledger,
            prompt_and_sha=(tmp_path / "does-not-exist.md", "0" * 64),
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_missing_live_claim_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)  # no claim written
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaimMissing):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_released_claim_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane", released=True)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaimReleased):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_controller_lane_mismatch_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    # claim file path matches lane but records a different lane_id internally
    path = ledger / "claims" / "hermes-primary" / "gate3-lane.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "some-other-lane",
        "record_timestamp": "2026-05-25T04:00:00Z",
        "worktree_path": "/worktrees/x",
        "envelope_ref": "none",
        "lease_seconds": 3600,
        "claimed_at": "2026-05-25T04:00:00Z",
        "last_heartbeat_at": "2026-05-25T04:00:00Z",
    }
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaimMismatch):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_unknown_terminal_kind_for_visibility_required_role(tmp_path):
    # ce-ops#207 W2′: the C1 gate now refuses an *unknown / non-satisfying*
    # surface (not "anything but tmux"). An unregistered kind is still refused
    # before any side effect — the load-bearing refusal survives.
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.VisibilityRefused):
        _launch(
            tmp_path,
            ledger_root=ledger,
            terminal_kind="not-a-real-surface",
            tmux_adapter=None,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_herdr_lane_launches_with_no_tmux_to_valid_record_and_events(tmp_path):
    """ce-ops#217 U3 headline acceptance.

    A visibility-required WORKER lane launches on the herdr
    operator_inspectable backend and produces a schema-valid Pane Registry record
    + events.jsonl lifecycle. tmux is never consulted.
    """
    from creator_engine_validator import visibility_backend as vb
    from creator_engine_validator.runner.herdr_session import HerdrPane

    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")

    class FakeHerdrBackend:
        terminal_kind = "herdr"
        visibility_class = vb.OPERATOR_INSPECTABLE

        def is_available(self):
            return True

        def ensure_surface(self, *, session, window, command, cwd=None, env=None, seat_dir=None):
            Path(seat_dir, "events.jsonl").write_text(
                '{"event":"launched","seat_id":"gate3-lane"}\n',
                encoding="utf-8",
            )
            return vb.SurfaceHandle(
                visibility_class=self.visibility_class,
                terminal={
                    "kind": "herdr",
                    "surface_ref": "herdr-surface-918aa1506d296ee1a72da70227854392",
                    "pane_id": "pane-1",
                    "pid": 4242,
                },
                native=HerdrPane(
                    pane_id="pane-1",
                    surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
                    pid=4242,
                    workspace_id="workspace-1",
                ),
            )

    result = _launch(
        tmp_path,
        ledger_root=ledger,
        terminal_kind="herdr",
        tmux_adapter=None,  # no tmux anywhere
        visibility_backend=FakeHerdrBackend(),
        command=["sh", "-c", "printf ce-herdr-live"],
    )

    # The lane reached LAUNCHED: a record was written for herdr, not tmux.
    record = result.record
    assert record["visibility"] == "operator_inspectable"
    assert record["terminal"]["kind"] == "herdr"
    assert record["terminal"]["surface_ref"] == "herdr-surface-918aa1506d296ee1a72da70227854392"
    assert "/run/ce/herdr/control.sock" not in repr(record["terminal"])
    assert record["terminal"]["pane_id"] == "pane-1"
    assert record["terminal"]["pid"] == 4242
    assert "session_id" not in record["terminal"]  # no tmux pane identity
    assert isinstance(result.pane, HerdrPane)

    # The written record passes the Pane Registry schema + validator (C3).
    errors = validate_pane_registry_record(record, Path(result.pane_path))
    assert errors == [], [e.format() for e in errors]

    # The events.jsonl lifecycle surface exists (witnessability, tmux-free).
    events_path = Path(result.events_ref)
    assert events_path.is_file()


def test_herdr_lane_record_uses_injected_backend(tmp_path):
    """Deterministic record shape via an injected fake herdr backend."""
    from creator_engine_validator import visibility_backend as vb
    from creator_engine_validator.runner.herdr_session import HerdrPane

    class FakeHerdrBackend:
        terminal_kind = "herdr"
        visibility_class = vb.OPERATOR_INSPECTABLE

        def is_available(self):
            return True

        def ensure_surface(self, *, session, window, command, cwd=None, env=None, seat_dir=None):
            return vb.SurfaceHandle(
                visibility_class=self.visibility_class,
                terminal={
                    "kind": "herdr",
                    "surface_ref": "herdr-surface-opaque",
                    "pane_id": "pane-51",
                    "pid": 5151,
                },
                native=HerdrPane("pane-51", "herdr-surface-opaque", 5151),
            )

    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")

    result = _launch(
        tmp_path,
        ledger_root=ledger,
        terminal_kind="herdr",
        tmux_adapter=None,
        visibility_backend=FakeHerdrBackend(),
    )
    assert result.record["visibility"] == "operator_inspectable"
    assert result.record["terminal"]["kind"] == "herdr"
    assert result.record["terminal"]["pane_id"] == "pane-51"
    assert result.record["terminal"]["pid"] == 5151
    errors = validate_pane_registry_record(result.record, Path(result.pane_path))
    assert errors == [], [e.format() for e in errors]


def test_headless_lane_launches_with_no_tmux_to_logged_surface(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        terminal_kind="headless",
        tmux_adapter=None,
        command=["true"],
    )
    assert result.pane.wait(timeout=5) == 0
    assert result.record["visibility"] == "operator_inspectable"
    assert result.record["terminal"]["kind"] == "headless"
    assert "session_id" not in result.record["terminal"]
    surface_ref = Path(result.record["terminal"]["surface_ref"])
    assert surface_ref.is_file()
    manifest = json.loads(surface_ref.read_text(encoding="utf-8"))
    assert manifest["surface_ref"] == str(surface_ref)
    assert Path(manifest["stream_ref"]).is_file()
    errors = validate_pane_registry_record(result.record, Path(result.pane_path))
    assert errors == [], [e.format() for e in errors]


def test_launch_refuses_tmux_unavailable_before_pane_write(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter(available=False)
    with pytest.raises(lane_runtime.TmuxUnavailableError):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_on_conflict_guard_before_pane_write(tmp_path):
    ledger = _ledger_root(tmp_path)
    # Two live claims, different controllers, same worktree_path -> PCO-010 conflict.
    _write_claim(ledger, "hermes-primary", "gate3-lane", worktree_path="/worktrees/shared")
    _write_claim(ledger, "other-controller", "other-lane", worktree_path="/worktrees/shared")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ConflictGuardRefused):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_nondir_worktree_path_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.WorktreePathInvalid):
        _launch(
            tmp_path,
            ledger_root=ledger,
            worktree_path=str(tmp_path / "no-such-worktree"),
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_missing_brain_ledger_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()

    with pytest.raises(lane_runtime.BrainBootstrapLaneRefused):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter, brain_ledger=False)

    _assert_no_pane(ledger)
    assert adapter.spawned == []
    assert not (tmp_path / ".ce" / "state" / "dispatches").exists()


def test_launch_refuses_tampered_brain_ledger_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    state_root = tmp_path / ".ce" / "state"
    _write_brain_ledger(state_root)
    path = brain_runtime.ledger_path(state_root)
    path.write_text(path.read_text(encoding="utf-8").replace("ready", "tampered"), encoding="utf-8")
    adapter = FakeAdapter()

    with pytest.raises(lane_runtime.BrainBootstrapLaneRefused):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter, brain_ledger=False)

    _assert_no_pane(ledger)
    assert adapter.spawned == []
    assert not (tmp_path / ".ce" / "state" / "dispatches").exists()


def test_launch_enforces_explicit_worktree_as_pane_cwd(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    wt = tmp_path / "wt"
    wt.mkdir()
    adapter = FakeAdapter()
    _launch(tmp_path, ledger_root=ledger, worktree_path=str(wt), tmux_adapter=adapter)
    assert adapter.last_cwd == str(wt)


def test_launch_refuses_handoff_sha_mismatch_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    handoff = tmp_path / "handoff.md"
    handoff.write_text("handoff body\n", encoding="utf-8")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.HandoffShaMismatch):
        _launch(
            tmp_path,
            ledger_root=ledger,
            handoff=handoff,
            handoff_sha="0" * 64,
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_does_not_launch_provider_by_default(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    assert adapter.spawned, "a pane should have been spawned"
    _, _, command = adapter.spawned[0]
    joined = " ".join(command).lower()
    for forbidden in ("claude", "openai", "gpt", "anthropic", "codex", "--api-key"):
        assert forbidden not in joined


# ---------------------------------------------------------------------------
# status / verify
# ---------------------------------------------------------------------------


def test_status_reads_live_pane_record(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    info = lane_runtime.status(
        controller_id="hermes-primary", lane_id="gate3-lane", ledger_root=ledger
    )
    assert info["record"]["status"] in lane_runtime.LIVE_STATUSES
    assert info["record"]["terminal"]["kind"] == "tmux"


def test_status_missing_record_raises(tmp_path):
    ledger = _ledger_root(tmp_path)
    with pytest.raises(lane_runtime.LaneStatusError):
        lane_runtime.status(
            controller_id="hermes-primary", lane_id="absent-lane", ledger_root=ledger
        )


def test_verify_ok_when_stop_line_present(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    transcript = tmp_path / "transcript.txt"
    stop = "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION"
    transcript.write_text(f"...work...\n{stop}\n", encoding="utf-8")
    result = lane_runtime.verify(
        controller_id="hermes-primary",
        lane_id="gate3-lane",
        ledger_root=ledger,
        transcript=transcript,
        stop_line=stop,
    )
    assert result["ok"] is True


def test_verify_refuses_missing_stop_line(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("work happened but no terminal line\n", encoding="utf-8")
    with pytest.raises(lane_runtime.LaneVerifyError):
        lane_runtime.verify(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            ledger_root=ledger,
            transcript=transcript,
            stop_line="CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION",
        )


def test_verify_refuses_missing_transcript(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    with pytest.raises(lane_runtime.LaneVerifyError):
        lane_runtime.verify(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            ledger_root=ledger,
            transcript=tmp_path / "missing.txt",
            stop_line="X",
        )


def test_verify_refuses_missing_pane_record(tmp_path):
    ledger = _ledger_root(tmp_path)
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("STOP\n", encoding="utf-8")
    with pytest.raises(lane_runtime.LaneVerifyError):
        lane_runtime.verify(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            ledger_root=ledger,
            transcript=transcript,
            stop_line="STOP",
        )


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 Claude refusal + governed command in `ce lane launch`
# ---------------------------------------------------------------------------


def test_lane_launch_refuses_claude_skip_perms_without_pack(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: False)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaudeLaunchRefused) as exc:
        _launch(
            tmp_path,
            ledger_root=ledger,
            command=["claude", "--dangerously-skip-permissions"],
            tmux_adapter=adapter,
        )
    assert exc.value.code == "G3-CLAUDE-REFUSED"
    assert "CC-D-6" in str(exc.value)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_lane_launch_refuses_claude_bare_even_with_pack(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaudeLaunchRefused):
        _launch(tmp_path, ledger_root=ledger, command=["claude", "--bare"], tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_lane_launch_pins_governed_command_for_claude(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    adapter = FakeAdapter()
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        command=["claude", "--model", "claude-opus-4-7"],
        tmux_adapter=adapter,
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    # ce-ops#26: the pane runs the sentinel wrapper; the governed argv is INSIDE it.
    assert cmd == ["/bin/sh", str(Path(result.events_ref).parent / "sentinel-wrapper.sh")]
    inner = _wrapper_inner_argv(result)
    assert inner[0] == "claude"
    assert "--setting-sources" in inner and "project" in inner and "--strict-mcp-config" in inner
    assert "--model" in inner and "claude-opus-4-7" in inner
    # The written pane record stays schema-clean (no extra CC-G-D fields).
    assert validate_pane_registry_record(result.record, result.pane_path) == []


def test_lane_launch_non_claude_command_unchanged(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        command=["sh", "-c", "echo hi"],
        tmux_adapter=adapter,
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    # ce-ops#26: non-claude commands pass through byte-identical INSIDE the wrapper.
    assert cmd == ["/bin/sh", str(Path(result.events_ref).parent / "sentinel-wrapper.sh")]
    assert _wrapper_inner_argv(result) == ["sh", "-c", "echo hi"]


def test_lane_launch_stamps_events_ref_into_sidecar(tmp_path):
    # ce-ops#26: the events surface is recorded in the ignored governance sidecar
    # (never the schema-locked pane record) and on the LaunchResult.
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(
        tmp_path, ledger_root=ledger, command=["sh", "-c", "echo hi"], tmux_adapter=FakeAdapter()
    )
    expected = str(tmp_path / ".ce" / "state" / "dispatches" / "gate3-lane" / "events.jsonl")
    assert result.events_ref == expected
    sidecar = lane_runtime._governance_sidecar_path(ledger, "hermes-primary", "gate3-lane")
    assert json.loads(sidecar.read_text())["events_ref"] == expected
    # the pane record itself stays schema-clean (events_ref rides the sidecar only)
    assert "events_ref" not in result.record


def test_lane_launch_injects_brain_bootstrap_ref_into_wrapper_and_sidecar(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        role="reviewer",
        lane_kind="review",
        command=["sh", "-c", "echo hi"],
        tmux_adapter=FakeAdapter(),
    )

    ref = Path(result.brain_bootstrap_ref)
    assert ref.is_file()
    payload = json.loads(ref.read_text(encoding="utf-8"))
    assert payload["kind"] == "brain-bootstrap-context"
    assert payload["context"]["role"] == "reviewer"
    assert payload["context"]["seat_class"] == "worker"
    wrapper = (Path(result.events_ref).parent / "sentinel-wrapper.sh").read_text(encoding="utf-8")
    assert f"export CE_BRAIN_BOOTSTRAP_REF={ref}" in wrapper
    assert f"export CE_BRAIN_BOOTSTRAP_SHA256={result.brain_bootstrap_sha256}" in wrapper
    sidecar = lane_runtime._governance_sidecar_path(ledger, "hermes-primary", "gate3-lane")
    written = json.loads(sidecar.read_text(encoding="utf-8"))
    assert written["brain_bootstrap_ref"] == str(ref)
    assert written["brain_bootstrap_sha256"] == result.brain_bootstrap_sha256
    assert "brain_bootstrap_ref" not in result.record


def test_lane_launch_refusal_precedes_any_sentinel_side_effect(tmp_path):
    # A refusal (missing claim) must raise BEFORE any wrapper/events write — no
    # dispatches dir is created for the would-be seat.
    with pytest.raises(lane_runtime.ClaimMissing):
        _launch(tmp_path, command=["claude"], tmux_adapter=FakeAdapter())
    assert not (tmp_path / ".ce" / "state" / "dispatches").exists()


# ---------------------------------------------------------------------------
# CC-G-D — Task 8: closeout pointer injection + Ring 0 closeout verification
# ---------------------------------------------------------------------------


def test_launch_writes_closeout_pointer_sidecar(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        command=["claude", "--setting-sources", "project"],
        completion_report_ref="reports/cc-g-d.yaml",
        closeout_file=".hermes/x/closeout.md",
        tmux_adapter=FakeAdapter(),
    )
    # Deterministic pointers ride the result.
    assert result.claude_governance["completion_report_ref"] == "reports/cc-g-d.yaml"
    assert result.claude_governance["closeout_ref"] == ".hermes/x/closeout.md"
    # ... and are persisted to an ignored sidecar (NOT the schema-validated record).
    sidecar = lane_runtime._governance_sidecar_path(ledger, "hermes-primary", "gate3-lane")
    assert sidecar.is_file()
    written = json.loads(sidecar.read_text(encoding="utf-8"))
    assert written["completion_report_ref"] == "reports/cc-g-d.yaml"
    # The tracked-shape pane record stays schema-clean.
    assert validate_pane_registry_record(result.record, result.pane_path) == []


def test_verify_closeout_blocks_on_missing_terminal_sections(tmp_path):
    bad = tmp_path / "closeout.md"
    bad.write_text("done.\n", encoding="utf-8")
    decision = lane_runtime.verify_closeout(
        closeout_file=str(bad), completion_report=None, posture="governed"
    )
    assert decision["decision"] == "block"  # Ring 0 fact; committed hook stays advisory


def test_verify_closeout_allows_complete_closeout(tmp_path):
    good = tmp_path / "closeout.md"
    good.write_text(
        "## Summary\nwork done\n\n"
        "## Recommended immediate next step\nratify\n\n"
        "## Exact next Source prompt pointer+SHA256\npath + sha\n",
        encoding="utf-8",
    )
    decision = lane_runtime.verify_closeout(
        closeout_file=str(good), completion_report=None, posture="governed"
    )
    assert decision.get("decision") != "block"


def test_verify_closeout_ungoverned_never_blocks(tmp_path):
    bad = tmp_path / "closeout.md"
    bad.write_text("done.\n", encoding="utf-8")
    decision = lane_runtime.verify_closeout(
        closeout_file=str(bad), completion_report=None, posture="ungoverned"
    )
    assert decision.get("decision") != "block"


# ---------------------------------------------------------------------------
# G2.002.1 operating-mode runtime carriers: ce lane launch default + refusals
# ---------------------------------------------------------------------------


def _write_tenant_policy(tmp_path, body: str, name: str = "tenant-policy.ce.yml"):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


VALID_AUTO_TENANT_POLICY = """
operating_mode_policy:
  operating_mode: auto
  autonomy_class: operator_ratified_privileged
  default_for_migrated_v1_tenants: strict
  operator_policy_ref:
    ratified_prompt: .hermes/research/example/OPERATOR_AUTO.md
    sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  privileged_floor:
    privileged_mutation_classes: [governance, security]
    required_ratifier_role: operator
    agent_reviewer: advisory_only
    agent_ratifier:
      status: reserved-inactive
      active_authority: none
  policy_authority:
    ratification_required_for_modes: [auto, transcendence]
    activation_record_required: true
  risk_coverage:
    required_validation_refs: [VAL-AUTO-REQUIRES-OPERATOR-POLICY]
"""

AGENT_RATIFIER_ACTIVE_TENANT_POLICY = VALID_AUTO_TENANT_POLICY.replace(
    "active_authority: none", "active_authority: privileged_governance"
)

ADVISORY_AS_RATIFIER_TENANT_POLICY = VALID_AUTO_TENANT_POLICY.replace(
    "required_ratifier_role: operator", "required_ratifier_role: agent_reviewer"
)


def test_launch_defaults_to_strict_operating_mode(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(tmp_path, ledger_root=ledger)
    assert result.operating_mode == "strict"


def test_launch_accepts_explicit_strict_and_carrier_fields(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        operating_mode="strict",
        autonomy_class="operator_ratified_privileged",
        lane_kind="implementation",
    )
    assert result.operating_mode == "strict"
    assert result.lane_kind == "implementation"


def test_launch_refuses_invalid_operating_mode_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.OperatingModeInvalid) as exc:
        _launch(tmp_path, ledger_root=ledger, operating_mode="permissive", tmux_adapter=adapter)
    assert exc.value.code == "G2-OPERATING-MODE-INVALID"
    assert adapter.spawned == []


def test_launch_refuses_invalid_lane_kind_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.LaneKindInvalid):
        _launch(tmp_path, ledger_root=ledger, lane_kind="deploy-and-merge", tmux_adapter=adapter)
    assert adapter.spawned == []


def test_launch_refuses_reserved_autonomy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ReservedAutonomyActive):
        _launch(
            tmp_path,
            ledger_root=ledger,
            autonomy_class="reserved_future_agent_ratification",
            tmux_adapter=adapter,
        )
    assert adapter.spawned == []


def test_launch_refuses_auto_without_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.AutoWithoutOperatorPolicy) as exc:
        _launch(tmp_path, ledger_root=ledger, operating_mode="auto", tmux_adapter=adapter)
    assert exc.value.code == "G2-AUTO-WITHOUT-OPERATOR-POLICY"
    assert adapter.spawned == []


def test_launch_refuses_transcendence_without_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.TranscendenceWithoutOperatorPolicy):
        _launch(tmp_path, ledger_root=ledger, operating_mode="transcendence", tmux_adapter=adapter)
    assert adapter.spawned == []


def test_launch_allows_auto_with_operator_ratified_tenant_policy(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    policy = _write_tenant_policy(tmp_path, VALID_AUTO_TENANT_POLICY)
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        operating_mode="auto",
        autonomy_class="operator_ratified_privileged",
        tenant_policy=policy,
    )
    assert result.operating_mode == "auto"


def test_launch_refuses_agent_ratifier_active_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    policy = _write_tenant_policy(tmp_path, AGENT_RATIFIER_ACTIVE_TENANT_POLICY)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.AgentRatifierActive) as exc:
        _launch(
            tmp_path,
            ledger_root=ledger,
            operating_mode="auto",
            tenant_policy=policy,
            tmux_adapter=adapter,
        )
    assert exc.value.code == "G2-AGENT-RATIFIER-ACTIVE"
    assert adapter.spawned == []


def test_launch_refuses_advisory_role_as_ratifier_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    policy = _write_tenant_policy(tmp_path, ADVISORY_AS_RATIFIER_TENANT_POLICY)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.PrivilegedRatifierInvalid):
        _launch(
            tmp_path,
            ledger_root=ledger,
            operating_mode="auto",
            tenant_policy=policy,
            tmux_adapter=adapter,
        )
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# G2.007.4: launch auto-provisions the strict lane MCP config in the worktree
# ---------------------------------------------------------------------------


def test_lane_launch_autoprovisions_mcp_config_when_missing(tmp_path, monkeypatch):
    """A governed Claude lane gets its strict MCP config written into the worktree."""
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    wt = tmp_path / "wt"
    wt.mkdir()
    _launch(
        tmp_path,
        ledger_root=ledger,
        command=["claude", "--model", "claude-opus-4-7"],
        worktree_path=str(wt),
        tmux_adapter=FakeAdapter(),
    )
    target = wt / ".hermes" / "gate3-lane" / "mcp" / "ce-mcp.json"
    assert target.is_file(), "launch must auto-provision the strict lane MCP config"
    assert json.loads(target.read_text(encoding="utf-8")) == {"mcpServers": {}}
    # byte-exact: indent=2, sort_keys, trailing newline (matches init_runtime writer)
    assert (
        target.read_text(encoding="utf-8")
        == json.dumps({"mcpServers": {}}, indent=2, sort_keys=True) + "\n"
    )


def test_lane_launch_does_not_overwrite_existing_mcp_config(tmp_path, monkeypatch):
    """An Operator/launcher-supplied MCP config is never clobbered."""
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    wt = tmp_path / "wt"
    target = wt / ".hermes" / "gate3-lane" / "mcp" / "ce-mcp.json"
    target.parent.mkdir(parents=True)
    preexisting = '{"mcpServers": {"keep": {"command": "x"}}}\n'
    target.write_text(preexisting, encoding="utf-8")
    _launch(
        tmp_path,
        ledger_root=ledger,
        command=["claude", "--model", "claude-opus-4-7"],
        worktree_path=str(wt),
        tmux_adapter=FakeAdapter(),
    )
    assert target.read_text(encoding="utf-8") == preexisting


def test_lane_launch_refuses_nonfile_mcp_target_before_side_effects(tmp_path, monkeypatch):
    """A non-regular-file at the MCP target is a fail-closed refusal (no spawn/pane)."""
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    wt = tmp_path / "wt"
    target = wt / ".hermes" / "gate3-lane" / "mcp" / "ce-mcp.json"
    target.mkdir(parents=True)  # a DIRECTORY where the config file must go
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaudeLaunchRefused):
        _launch(
            tmp_path,
            ledger_root=ledger,
            command=["claude", "--model", "claude-opus-4-7"],
            worktree_path=str(wt),
            tmux_adapter=adapter,
        )
    assert adapter.spawned == []
    assert not (ledger / "panes" / "hermes-primary" / "gate3-lane.yaml").exists()


def test_ensure_lane_mcp_config_public_name_and_deprecation_alias():
    """v3.1-G1 promoted the helper to public; the private alias must still resolve.

    ``launch_runtime`` reuses ``ensure_lane_mcp_config`` to fix the plain-launch
    MCP-provisioning defect; the legacy ``_ensure_lane_mcp_config`` name stays as a
    deprecation alias to the identical callable.
    """
    assert callable(lane_runtime.ensure_lane_mcp_config)
    assert lane_runtime._ensure_lane_mcp_config is lane_runtime.ensure_lane_mcp_config


def test_ensure_lane_mcp_config_writes_default_payload(tmp_path):
    """The public helper writes the byte-exact default payload when nothing is there."""
    target = tmp_path / "nested" / "ce-mcp.json"
    lane_runtime.ensure_lane_mcp_config(target)
    assert target.is_file()
    assert (
        target.read_text(encoding="utf-8")
        == json.dumps({"mcpServers": {}}, indent=2, sort_keys=True) + "\n"
    )


def test_lane_launch_non_claude_command_does_not_provision_mcp(tmp_path):
    """Non-Claude lanes never get an MCP config written (the branch is Claude-only)."""
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    wt = tmp_path / "wt"
    wt.mkdir()
    _launch(
        tmp_path,
        ledger_root=ledger,
        command=["sh", "-c", "echo hi"],
        worktree_path=str(wt),
        tmux_adapter=FakeAdapter(),
    )
    assert not (wt / ".hermes" / "gate3-lane" / "mcp" / "ce-mcp.json").exists()
