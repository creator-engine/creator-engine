"""v3.5-F Q1 — pure tests for the per-seat resource-bounding spec.

Covers the PURE core (wrap builder, unit-name sanitizer, fail-closed policy
fragment reader, §4.4 host-class defaults), the golden Ring-0-untouched
assertion (the wrap is applied to the OUTPUT of Ring 0; the governed tokens
stay byte-identical), the recorded-evidence fixture replay (the proof carrier
on hosts without user-level systemd bounding), and the injectable-runner I/O
edges — all without spawning a process or touching systemd.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import claude_launch_spec, resource_bound_spec as rbs

FIXTURE = Path(__file__).parent / "fixtures" / "resource_bound_observed.json"

BOUND = rbs.ResourceBound(
    unit="ce-seat-proof",
    slice="ce-fleet.slice",
    memory_high="3500M",
    memory_max="4G",
    memory_swap_max="256M",
    tasks_max=512,
)

OPTOUT = {
    "ratified_prompt_sha": "a" * 64,
    "approver_ref": "b" * 64,
}


def _policy(**overrides):
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
    return policy


class FakeRunner:
    """Records systemctl argv calls and replays scripted CompletedProcess results."""

    def __init__(self, results=None):
        self.calls: list[list[str]] = []
        self._results = list(results or [])

    def __call__(self, argv, check=False):
        self.calls.append(list(argv))
        if self._results:
            return self._results.pop(0)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# The pure wrap builder
# ---------------------------------------------------------------------------


def test_build_bounded_command_exact_wrap():
    wrapped = rbs.build_bounded_command(["claude", "--foo"], BOUND)
    assert wrapped == [
        "systemd-run", "--user", "--scope", "--collect",
        "--expand-environment=no",
        "--unit", "ce-seat-proof", "--slice", "ce-fleet.slice",
        "-p", "MemoryHigh=3500M",
        "-p", "MemoryMax=4G",
        "-p", "MemorySwapMax=256M",
        "-p", "TasksMax=512",
        "--", "claude", "--foo",
    ]


def test_build_bounded_command_none_is_passthrough_copy():
    command = ["claude", "--foo"]
    out = rbs.build_bounded_command(command, None)
    assert out == command
    assert out is not command  # a copy, never an alias


def test_build_bounded_command_tier_a_cpu_properties():
    bound = rbs.ResourceBound(
        unit="u", slice="s", memory_high="1G", memory_max="2G",
        memory_swap_max="0", tasks_max=8, cpu_weight=100, cpu_quota="200%",
    )
    wrapped = rbs.build_bounded_command(["x"], bound)
    sep = wrapped.index("--")
    assert "-p" in wrapped and "CPUWeight=100" in wrapped and "CPUQuota=200%" in wrapped
    assert wrapped.index("CPUQuota=200%") < sep


def test_golden_ring0_output_is_byte_identical_through_the_wrap():
    """THE KEYSTONE GOLDEN: the wrap rides the OUTPUT of Ring 0, untouched.

    Build a real governed Claude command via the Ring-0 builder, wrap it, and
    prove the governed tokens after ``--`` are byte-identical — hook-pack
    posture, ``--setting-sources project``, strict MCP all pass through.
    """
    governed = claude_launch_spec.build_governed_claude_command(
        base_argv=["--dangerously-skip-permissions"],
        mcp_config_path=".hermes/launch/ce-seat-proof/mcp/ce-mcp.json",
    )
    wrapped = rbs.build_bounded_command(governed, BOUND)
    sep = wrapped.index("--")
    assert wrapped[sep + 1:] == governed
    # And the unwrapped command reproduces today's command exactly.
    assert rbs.build_bounded_command(governed, None) == governed


def test_recorded_evidence_fixture_replays_through_the_builder():
    """The recorded O10 wrap (crash host) is exactly what the builder emits."""
    recorded = json.loads(FIXTURE.read_text(encoding="utf-8"))
    o10 = recorded["o10_wrap"]
    bound = rbs.ResourceBound(**o10["bound"])
    assert rbs.build_bounded_command(o10["governed_command"], bound) == o10["wrapped_command"]
    sep = o10["wrapped_command"].index("--")
    assert o10["wrapped_command"][sep + 1:] == o10["governed_command"]
    # The recorded isolated-kill proof (O9): clean kernel group-kill semantics.
    assert recorded["o9_isolated_kill"]["exit_code"] == 137
    assert recorded["o9_isolated_kill"]["unit_result"] == "oom-kill"
    assert recorded["o9_isolated_kill"]["sibling_seats_killed"] == 0


def test_sanitize_unit_name():
    assert rbs.sanitize_unit_name("v35f-q1-exec") == "ce-seat-v35f-q1-exec"
    assert rbs.sanitize_unit_name("a b/c:d") == "ce-seat-a-b-c-d"
    assert rbs.sanitize_unit_name("--weird..") == "ce-seat-weird"
    with pytest.raises(rbs.ResourcePolicyError):
        rbs.sanitize_unit_name("///")


# ---------------------------------------------------------------------------
# parse_resource_policy — fail-closed
# ---------------------------------------------------------------------------


def test_parse_enforce_policy():
    rp = rbs.parse_resource_policy(_policy())
    assert rp.enforcement == "enforce"
    assert rp.governed and not rp.opted_down
    assert rp.fleet_memory_max == "9G"
    bound = rp.seat_bound("ce-seat-x")
    assert bound.memory_max == "4G" and bound.tasks_max == 512


def test_parse_no_resource_fields_means_ungoverned():
    rp = rbs.parse_resource_policy({"kind": "runtime-policy-record"})
    assert not rp.governed
    assert rp.enforcement == "enforce"
    assert rp.seat_bound("u") is None


def test_advisory_without_optout_is_refused_fail_closed():
    with pytest.raises(rbs.ResourcePolicyError, match="resource_optout"):
        rbs.parse_resource_policy(_policy(resource_enforcement="advisory"))


def test_off_without_optout_is_refused_fail_closed():
    with pytest.raises(rbs.ResourcePolicyError, match="resource_optout"):
        rbs.parse_resource_policy(_policy(resource_enforcement="off"))


def test_advisory_with_ratified_optout_is_accepted():
    rp = rbs.parse_resource_policy(
        _policy(resource_enforcement="advisory", resource_optout=dict(OPTOUT))
    )
    assert rp.opted_down and rp.enforcement == "advisory"


def test_optout_with_malformed_digests_is_refused():
    bad = {"ratified_prompt_sha": "xyz", "approver_ref": "b" * 64}
    with pytest.raises(rbs.ResourcePolicyError):
        rbs.parse_resource_policy(
            _policy(resource_enforcement="off", resource_optout=bad)
        )


def test_unknown_enforcement_mode_is_refused():
    with pytest.raises(rbs.ResourcePolicyError, match="resource_enforcement"):
        rbs.parse_resource_policy(_policy(resource_enforcement="lenient"))


@pytest.mark.parametrize(
    "mutation",
    [
        {"memory_max": "4 G"},          # space breaks the shell-safe token
        {"memory_max": "4GB"},          # not a systemd suffix
        {"memory_max": None},           # missing
        {"tasks_max": 0},
        {"tasks_max": True},
        {"cpu_weight": 0},
        {"cpu_quota": "2x"},
        {"scope": "run"},               # per-run is the WRONG lifetime (Fork F-7)
        {"surprise": 1},                # unknown key
    ],
)
def test_malformed_seat_envelope_is_refused(mutation):
    policy = _policy()
    seat = dict(policy["resource_envelopes"][0])
    seat.update(mutation)
    seat = {k: v for k, v in seat.items() if v is not None}
    policy["resource_envelopes"][0] = seat
    with pytest.raises(rbs.ResourcePolicyError):
        rbs.parse_resource_policy(policy)


def test_incomplete_seat_envelope_under_enforce_is_refused():
    policy = _policy()
    del policy["resource_envelopes"][0]["memory_swap_max"]
    with pytest.raises(rbs.ResourcePolicyError, match="missing"):
        rbs.parse_resource_policy(policy)


def test_fleet_only_under_enforce_is_refused():
    policy = _policy()
    policy["resource_envelopes"] = [{"scope": "fleet", "memory_max": "9G"}]
    with pytest.raises(rbs.ResourcePolicyError, match="fleet"):
        rbs.parse_resource_policy(policy)


def test_duplicate_scopes_are_refused():
    policy = _policy()
    policy["resource_envelopes"].append({"scope": "fleet", "memory_max": "5G"})
    with pytest.raises(rbs.ResourcePolicyError, match="more than one"):
        rbs.parse_resource_policy(policy)


def test_non_mapping_policy_is_refused():
    with pytest.raises(rbs.ResourcePolicyError):
        rbs.parse_resource_policy(["not", "a", "mapping"])


# ---------------------------------------------------------------------------
# §4.4 host-class default materialization
# ---------------------------------------------------------------------------


def test_host_class_defaults_desktop_table_row():
    fragment = rbs.host_class_defaults(14 * 1024 ** 3)
    assert fragment["host_class"] == "desktop-14g"
    seat, fleet = fragment["resource_envelopes"]
    assert (seat["memory_high"], seat["memory_max"], seat["memory_swap_max"]) == (
        "3500M", "4G", "256M",
    )
    assert seat["tasks_max"] == 512
    assert fleet == {"scope": "fleet", "memory_max": "9G"}
    assert fragment["resource_enforcement"] == "enforce"


def test_host_class_defaults_small_host_table_row():
    fragment = rbs.host_class_defaults(8 * 1024 ** 3)
    assert fragment["host_class"] == "small-host-8g"
    seat, fleet = fragment["resource_envelopes"]
    assert (seat["memory_high"], seat["memory_max"], seat["memory_swap_max"]) == (
        "2G", "2500M", "128M",
    )
    assert fleet["memory_max"] == "5500M"


def test_host_class_defaults_round_trip_through_the_parser():
    # The fragment doctor emits is exactly what the launch paths accept.
    for total in (8 * 1024 ** 3, 14 * 1024 ** 3, 64 * 1024 ** 3):
        rp = rbs.parse_resource_policy(rbs.host_class_defaults(total))
        assert rp.governed and rp.seat_bound("u") is not None


def test_host_class_defaults_refuses_garbage():
    with pytest.raises(rbs.ResourcePolicyError):
        rbs.host_class_defaults(0)


# ---------------------------------------------------------------------------
# I/O edges with the injectable runner (no real systemd touched)
# ---------------------------------------------------------------------------


def test_probe_user_bounding_ok(tmp_path):
    controllers = tmp_path / "cgroup.controllers"
    controllers.write_text("cpuset cpu io memory pids\n", encoding="utf-8")
    ok, reason = rbs.probe_user_bounding(FakeRunner(), controllers_path=controllers)
    assert ok, reason


def test_probe_user_bounding_no_user_manager():
    runner = FakeRunner([_proc(returncode=1)])
    ok, reason = rbs.probe_user_bounding(runner, controllers_path="/nonexistent")
    assert not ok and "linger" in reason


def test_probe_user_bounding_missing_delegation(tmp_path):
    controllers = tmp_path / "cgroup.controllers"
    controllers.write_text("cpu\n", encoding="utf-8")
    ok, reason = rbs.probe_user_bounding(FakeRunner(), controllers_path=controllers)
    assert not ok and "memory" in reason


def test_resolve_unit_name_free_first_candidate():
    runner = FakeRunner([_proc(stdout="inactive\n")])
    assert rbs.resolve_unit_name("v35f-q1", runner) == "ce-seat-v35f-q1"
    assert runner.calls[0][-1] == "ce-seat-v35f-q1.scope"


def test_resolve_unit_name_collision_takes_suffix():
    runner = FakeRunner([_proc(stdout="active\n"), _proc(stdout="inactive\n")])
    assert rbs.resolve_unit_name("v35f-q1", runner) == "ce-seat-v35f-q1-2"


def test_resolve_unit_name_exhaustion_refuses_loudly():
    runner = FakeRunner([_proc(stdout="active\n")] * 16)
    with pytest.raises(rbs.UnitNameCollision, match="retire stale seat scopes"):
        rbs.resolve_unit_name("v35f-q1", runner, max_probes=16)


def test_apply_fleet_cap_retries_until_slice_loads():
    runner = FakeRunner([
        _proc(returncode=1, stderr="Unit ce-fleet.slice not loaded."),
        _proc(returncode=0),
    ])
    naps: list[float] = []
    rbs.apply_fleet_cap("9G", runner=runner, sleeper=naps.append)
    assert len(runner.calls) == 2 and naps == [0.25]
    assert runner.calls[0][:4] == ["systemctl", "--user", "set-property", "--runtime"]
    assert runner.calls[0][4:] == ["ce-fleet.slice", "MemoryMax=9G"]


def test_apply_fleet_cap_exhaustion_refuses_loudly():
    runner = FakeRunner([_proc(returncode=1, stderr="nope")] * 3)
    with pytest.raises(rbs.SeatScopeUnavailable, match="not applied"):
        rbs.apply_fleet_cap("9G", runner=runner, attempts=3, sleeper=lambda _: None)


def test_apply_fleet_cap_validates_size_string():
    with pytest.raises(rbs.ResourcePolicyError):
        rbs.apply_fleet_cap("9 G", runner=FakeRunner())


def test_write_oom_group_writes_into_the_resolved_scope(tmp_path):
    cg = "user.slice/user-1000.slice/user@1000.service/ce.slice/ce-fleet.slice/ce-seat-x.scope"
    scope_dir = tmp_path / cg
    scope_dir.mkdir(parents=True)
    runner = FakeRunner([_proc(stdout=f"/{cg}\n")])
    target = rbs.write_oom_group("ce-seat-x", runner=runner, cgroupfs_root=tmp_path)
    assert target.read_text(encoding="ascii") == "1\n"
    assert target == scope_dir / "memory.oom.group"


def test_write_oom_group_polls_then_refuses_when_scope_never_appears():
    runner = FakeRunner([_proc(stdout="\n")] * 4)
    with pytest.raises(rbs.SeatScopeUnavailable, match="never reported"):
        rbs.write_oom_group(
            "ce-seat-x", runner=runner, cgroupfs_root="/nonexistent",
            attempts=4, sleeper=lambda _: None,
        )
