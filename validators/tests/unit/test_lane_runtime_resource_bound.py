"""v3.5-F Q1 — the bounding wrap on the ``ce lane launch`` path.

Mirrors the launch_runtime coverage on the governed-lane primitive: the wrap
rides the OUTPUT of the step-6 Ring-0 governed-command build (byte-identical
tokens), refusals fire BEFORE any side effect (no pane spawn, no Pane Registry
write), launch-confirm writes ``memory.oom.group`` + the fleet cap, and the
``resource_bound`` evidence stamp lands on the LaunchResult + the ignored
governance sidecar.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, lane_runtime
from creator_engine_validator.tmux_adapter import TmuxPane

OPTOUT = {"ratified_prompt_sha": "a" * 64, "approver_ref": "b" * 64}
WRAP_PREFIX_HEAD = [
    "systemd-run", "--user", "--scope", "--collect",
    "--expand-environment=no", "--unit",
]


class FakeAdapter:
    kind = "tmux"

    def __init__(self):
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return True

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command)))
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3", pane_pid=4242)


class FakeSystemctl:
    def __init__(self, *, cgroupfs_root: Path):
        self.calls: list[list[str]] = []
        self._root = cgroupfs_root

    def __call__(self, argv, check=False):
        self.calls.append(list(argv))
        if argv[2] == "show" and "ActiveState" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="inactive\n", stderr="")
        if argv[2] == "show" and "ControlGroup" in argv:
            unit = argv[-1].removesuffix(".scope")
            cg = f"/ce.slice/ce-fleet.slice/{unit}.scope"
            (self._root / cg.lstrip("/")).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(argv, 0, stdout=f"{cg}\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _ok_probe(runner=None, **_):
    return True, "fake host supports bounding"


def _write_prompt(tmp_path: Path) -> tuple[Path, str]:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("governed gate prompt body\n", encoding="utf-8")
    return prompt, hashlib.sha256(prompt.read_bytes()).hexdigest()


def _ledger_root(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_claim(ledger_root: Path, controller_id: str, lane_id: str) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_timestamp": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "worktree_path": "/worktrees/gate3-lane",
        "envelope_ref": "envelopes/gate3.md",
        "branch": "implementer/gate3-lane",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
    }
    path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _write_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-lane-bound-0001",
        claim={"subject": "lane", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref="validators/tests/unit/test_lane_runtime_resource_bound.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


def _write_policy(tmp_path: Path, **overrides) -> Path:
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


def _launch(tmp_path: Path, **overrides):
    prompt, sha = _write_prompt(tmp_path)
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _write_brain_ledger(tmp_path / ".ce" / "state")
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


def _inner_argv(result):
    """Recover the EXACT step-6c output argv embedded in the ce-ops#26 wrapper.

    The pane command is now ``["/bin/sh", <wrapper>]``; the bounded command runs
    FOREGROUND inside the wrapper (the line before ``code=$?``). These bounding
    assertions hold on that inner argv — the wrapper is strictly OUTSIDE it.
    """
    import shlex
    from pathlib import Path as _P

    wrapper = _P(result.events_ref).parent / "sentinel-wrapper.sh"
    lines = wrapper.read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    return shlex.split(lines[idx - 1])


def test_lane_wrap_rides_the_governed_claude_command(tmp_path):
    adapter = FakeAdapter()
    systemctl = FakeSystemctl(cgroupfs_root=tmp_path)
    # Baseline: the same governed lane WITHOUT a resource policy.
    baseline_adapter = FakeAdapter()
    baseline_result = _launch(
        tmp_path,
        command=["claude"],
        mcp_config_path=".hermes/gate3-lane/mcp/ce-mcp.json",
        tmux_adapter=baseline_adapter,
    )
    governed = _inner_argv(baseline_result)

    result = _launch(
        tmp_path,
        command=["claude"],
        mcp_config_path=".hermes/gate3-lane/mcp/ce-mcp.json",
        tmux_adapter=adapter,
        runtime_policy=_write_policy(tmp_path),
        systemctl_runner=systemctl,
        support_probe=_ok_probe,
        cgroupfs_root=tmp_path,
    )
    wrapped = _inner_argv(result)
    assert wrapped[:6] == WRAP_PREFIX_HEAD
    assert wrapped[6] == "ce-seat-gate3-lane"  # unit keyed by lane_id
    sep = wrapped.index("--")
    # KEYSTONE: the step-6 Ring-0 output passes through byte-identical.
    assert wrapped[sep + 1:] == governed
    assert governed[0] == "claude" and "--strict-mcp-config" in governed
    # Evidence stamp on the result…
    assert result.resource_bound["unit"] == "ce-seat-gate3-lane"
    assert result.resource_bound["fleet_memory_max"] == "9G"
    # …and on the ignored governance sidecar.
    sidecar = json.loads(
        (result.pane_path.parent / "gate3-lane.claude-governance.json").read_text(
            encoding="utf-8"
        )
    )
    assert sidecar["resource_bound"]["memory_max"] == "4G"
    # launch-confirm: oom.group written + fleet cap applied.
    oom = tmp_path / "ce.slice/ce-fleet.slice/ce-seat-gate3-lane.scope/memory.oom.group"
    assert oom.read_text(encoding="ascii") == "1\n"
    assert ["systemctl", "--user", "set-property", "--runtime", "ce-fleet.slice",
            "MemoryMax=9G"] in systemctl.calls


def test_lane_wrap_bounds_the_inert_placeholder_too(tmp_path):
    adapter = FakeAdapter()
    result = _launch(
        tmp_path,
        tmux_adapter=adapter,
        runtime_policy=_write_policy(tmp_path),
        systemctl_runner=FakeSystemctl(cgroupfs_root=tmp_path),
        support_probe=_ok_probe,
        cgroupfs_root=tmp_path,
    )
    wrapped = _inner_argv(result)
    sep = wrapped.index("--")
    assert wrapped[sep + 1:] == lane_runtime.INERT_PLACEHOLDER_COMMAND
    assert result.resource_bound is not None


def test_lane_advisory_optdown_stamps_none_and_skips_the_wrap(tmp_path):
    adapter = FakeAdapter()
    result = _launch(
        tmp_path,
        tmux_adapter=adapter,
        runtime_policy=_write_policy(
            tmp_path, resource_enforcement="advisory", resource_optout=dict(OPTOUT)
        ),
    )
    assert _inner_argv(result) == list(lane_runtime.INERT_PLACEHOLDER_COMMAND)
    assert result.resource_bound == "none (advisory)"
    sidecar = json.loads(
        (result.pane_path.parent / "gate3-lane.claude-governance.json").read_text(
            encoding="utf-8"
        )
    )
    assert sidecar["resource_bound"] == "none (advisory)"


def test_lane_advisory_without_optout_refuses_before_side_effects(tmp_path):
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ResourceBoundRefused, match="resource_optout"):
        _launch(
            tmp_path,
            tmux_adapter=adapter,
            runtime_policy=_write_policy(tmp_path, resource_enforcement="advisory"),
        )
    assert adapter.spawned == []
    panes = list((tmp_path / ".hermes" / "active-work-ledger" / "panes").rglob("*"))
    assert panes == []  # no Pane Registry write either


def test_lane_enforce_refuses_loudly_on_unsupported_host(tmp_path):
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ResourceBoundRefused, match="unavailable"):
        _launch(
            tmp_path,
            tmux_adapter=adapter,
            runtime_policy=_write_policy(tmp_path),
            support_probe=lambda runner=None, **_: (False, "no delegation"),
        )
    assert adapter.spawned == []


def test_lane_without_policy_is_unchanged(tmp_path):
    adapter = FakeAdapter()
    result = _launch(tmp_path, tmux_adapter=adapter)
    assert _inner_argv(result) == list(lane_runtime.INERT_PLACEHOLDER_COMMAND)
    assert result.resource_bound is None
