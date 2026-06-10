"""v3.5-F Q1 — the bounding wrap on the ``ce launch`` path.

Exercises the launch_runtime hook with a tmux double + a fake systemctl
runner: the wrap rides the OUTPUT of Ring 0 (governed tokens byte-identical),
``--dry-run`` renders the ``resource_bound`` block offline (no systemd probe),
``enforce`` refuses loudly on an unsupported host BEFORE any side effect, the
ratified opt-down launches unbounded with the ``none (advisory)`` stamp, and
launch-confirm writes ``memory.oom.group`` + applies the fleet cap.
"""
from __future__ import annotations

import json
import subprocess

import pytest
import yaml

from creator_engine_validator import launch_runtime
from creator_engine_validator.tmux_adapter import TmuxPane

OPTOUT = {"ratified_prompt_sha": "a" * 64, "approver_ref": "b" * 64}

WRAP_PREFIX_HEAD = [
    "systemd-run", "--user", "--scope", "--collect",
    "--expand-environment=no", "--unit",
]


class FakeAdapter:
    kind = "tmux"

    def __init__(self, *, available: bool = True, sessions: set[str] | None = None):
        self._available = available
        self._sessions = set(sessions or set())
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return self._available

    def session_exists(self, session: str) -> bool:
        return session in self._sessions

    def ensure_pane(self, *, session, window, command):
        self.spawned.append((session, window, list(command)))
        self._sessions.add(session)
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3", pane_pid=999)


class FakeSystemctl:
    """Scripted systemctl runner: unit-name probe + ControlGroup + set-property."""

    def __init__(self, *, cgroupfs_root, active_units: set[str] | None = None):
        self.calls: list[list[str]] = []
        self._active = set(active_units or set())
        self._root = cgroupfs_root

    def __call__(self, argv, check=False):
        self.calls.append(list(argv))
        if argv[2] == "show" and "ActiveState" in argv:
            unit = argv[-1].removesuffix(".scope")
            state = "active" if unit in self._active else "inactive"
            return subprocess.CompletedProcess(argv, 0, stdout=f"{state}\n", stderr="")
        if argv[2] == "show" and "ControlGroup" in argv:
            unit = argv[-1].removesuffix(".scope")
            cg = f"/ce.slice/ce-fleet.slice/{unit}.scope"
            (self._root / cg.lstrip("/")).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(argv, 0, stdout=f"{cg}\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _ok_probe(runner=None, **_):
    return True, "fake host supports bounding"


def _never_probe(runner=None, **_):  # pragma: no cover - failing the test IS the assert
    raise AssertionError("the support probe must not run in dry-run mode")


def _write_policy(tmp_path, **overrides):
    policy = {
        "resource_envelopes": [
            {
                "scope": "seat",
                "memory_high": "3500M",
                "memory_max": "4G",
                "memory_swap_max": "256M",
                "tasks_max": 512,
            },
            {"scope": "fleet", "memory_max": "9G"},
        ],
        "resource_enforcement": "enforce",
    }
    policy.update(overrides)
    path = tmp_path / "runtime-policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=True), encoding="utf-8")
    return path


def test_dry_run_renders_the_resource_bound_block_offline(tmp_path):
    result = launch_runtime.launch(
        harness="claude",
        session="v35f-seat",
        dry_run=True,
        tmux_adapter=FakeAdapter(),
        runtime_policy=_write_policy(tmp_path),
        support_probe=_never_probe,  # dry-run must stay offline: no probe
    )
    plan = result.plan.to_dict()
    block = plan["resource_bound"]
    assert block["unit"] == "ce-seat-v35f-seat"
    assert block["slice"] == "ce-fleet.slice"
    assert block["memory_max"] == "4G"
    assert block["fleet_memory_max"] == "9G"
    assert plan["command"][:6] == WRAP_PREFIX_HEAD
    # The plan JSON is the offline proof artifact — it must serialize.
    json.dumps(plan)


def test_dry_run_wrap_leaves_ring0_governed_tokens_byte_identical(tmp_path):
    """Golden at the runtime level: wrapped tail == the governed command that
    the same launch produces WITHOUT a resource policy."""
    unbounded = launch_runtime.launch(
        harness="claude", session="v35f-seat", dry_run=True, tmux_adapter=FakeAdapter()
    )
    bounded = launch_runtime.launch(
        harness="claude",
        session="v35f-seat",
        dry_run=True,
        tmux_adapter=FakeAdapter(),
        runtime_policy=_write_policy(tmp_path),
    )
    wrapped = bounded.plan.command
    sep = wrapped.index("--")
    assert wrapped[sep + 1:] == unbounded.plan.command
    assert unbounded.plan.command[0] == "claude"
    assert "--strict-mcp-config" in unbounded.plan.command


def test_no_policy_means_no_wrap_and_no_stamp():
    result = launch_runtime.launch(
        harness="claude", session="s", dry_run=True, tmux_adapter=FakeAdapter()
    )
    assert result.plan.resource_bound is None
    assert result.plan.command[0] == "claude"


def test_advisory_optdown_launches_unbounded_with_the_stamp(tmp_path):
    adapter = FakeAdapter()
    result = launch_runtime.launch(
        harness="claude",
        session="s",
        tmux_adapter=adapter,
        runtime_policy=_write_policy(
            tmp_path,
            resource_enforcement="advisory",
            resource_optout=dict(OPTOUT),
        ),
        support_probe=_never_probe,  # opt-down never probes
    )
    assert result.plan.resource_bound == "none (advisory)"
    assert result.resource_confirm is None
    (_, _, spawned_command), = adapter.spawned
    assert spawned_command[0] == "claude"  # unwrapped


def test_advisory_without_optout_refuses_before_any_side_effect(tmp_path):
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.ResourceBoundRefused, match="resource_optout"):
        launch_runtime.launch(
            harness="claude",
            session="s",
            tmux_adapter=adapter,
            runtime_policy=_write_policy(tmp_path, resource_enforcement="advisory"),
        )
    assert adapter.spawned == []


def test_enforce_refuses_loudly_on_unsupported_host(tmp_path):
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.ResourceBoundRefused, match="unavailable"):
        launch_runtime.launch(
            harness="claude",
            session="s",
            tmux_adapter=adapter,
            runtime_policy=_write_policy(tmp_path),
            support_probe=lambda runner=None, **_: (False, "no user manager"),
        )
    assert adapter.spawned == []  # refused BEFORE any side effect


def test_unreadable_policy_refuses(tmp_path):
    with pytest.raises(launch_runtime.ResourceBoundRefused, match="unreadable"):
        launch_runtime.launch(
            harness="claude",
            session="s",
            dry_run=True,
            tmux_adapter=FakeAdapter(),
            runtime_policy=tmp_path / "missing.yaml",
        )


def test_live_launch_wraps_confirms_oom_group_and_fleet_cap(tmp_path):
    adapter = FakeAdapter()
    systemctl = FakeSystemctl(cgroupfs_root=tmp_path)
    result = launch_runtime.launch(
        harness="claude",
        session="v35f-seat",
        tmux_adapter=adapter,
        runtime_policy=_write_policy(tmp_path),
        systemctl_runner=systemctl,
        support_probe=_ok_probe,
        cgroupfs_root=tmp_path,
    )
    (_, _, spawned_command), = adapter.spawned
    assert spawned_command[:6] == WRAP_PREFIX_HEAD
    assert spawned_command[6] == "ce-seat-v35f-seat"
    sep = spawned_command.index("--")
    assert spawned_command[sep + 1] == "claude"
    # launch-confirm: the seat is provably group-killable + the fleet cap applied.
    oom_file = (
        tmp_path / "ce.slice/ce-fleet.slice/ce-seat-v35f-seat.scope/memory.oom.group"
    )
    assert oom_file.read_text(encoding="ascii") == "1\n"
    assert result.resource_confirm == {
        "oom_group_written": True,
        "oom_group_path": str(oom_file),
        "fleet_memory_max": "9G",
    }
    assert ["systemctl", "--user", "set-property", "--runtime", "ce-fleet.slice",
            "MemoryMax=9G"] in systemctl.calls
    assert result.plan.resource_bound["unit"] == "ce-seat-v35f-seat"


def test_live_launch_resolves_unit_collision_with_suffix(tmp_path):
    adapter = FakeAdapter()
    systemctl = FakeSystemctl(
        cgroupfs_root=tmp_path, active_units={"ce-seat-v35f-seat"}
    )
    result = launch_runtime.launch(
        harness="claude",
        session="v35f-seat",
        tmux_adapter=adapter,
        runtime_policy=_write_policy(tmp_path),
        systemctl_runner=systemctl,
        support_probe=_ok_probe,
        cgroupfs_root=tmp_path,
    )
    assert result.plan.resource_bound["unit"] == "ce-seat-v35f-seat-2"


def test_wrap_applies_to_every_harness_identically(tmp_path):
    # codex has no Ring-0 spec of its own today — it is bounded the same day.
    result = launch_runtime.launch(
        harness="codex",
        session="codex-seat",
        dry_run=True,
        tmux_adapter=FakeAdapter(),
        runtime_policy=_write_policy(tmp_path),
    )
    wrapped = result.plan.command
    assert wrapped[:6] == WRAP_PREFIX_HEAD
    sep = wrapped.index("--")
    assert wrapped[sep + 1:] == ["codex"]
