"""Unit tests for the v3.5-C α-precursor ``forge.backlog`` adapter
(Projects-v2 reader/writer + the forge-projected advisory claim)."""

from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator.forge.backlog import (
    BacklogItem,
    ClaimPlan,
    Escalation,
    ItemRef,
    ProjectRef,
    claim_item,
    drift_check,
    idempotency_key,
    project_claim,
    read_backlog_item,
    reconcile_competing_claim,
)
from creator_engine_validator.forge.github_repo_config import ForgeConfigError

REF = ProjectRef(
    repo="creator-engine/creator-engine",
    project_id="PVT_proj1",
    status_field_id="PVTF_status",
    running_option_id="opt_running",
    claimed_at_field_id="PVTF_claimedat",
)
ITEM = ItemRef(item_id="PVTI_item1", issue_number=42)


def _node(status="Ready", assignees=(), claimed_at=None):
    return {
        "data": {"node": {
            "id": ITEM.item_id,
            "status": {"name": status} if status is not None else None,
            "claimedAt": {"text": claimed_at} if claimed_at is not None else None,
            "content": {"assignees": {"nodes": [{"login": a} for a in assignees]}},
        }}
    }


class _Runner:
    """A GhRunner answering reads from a queue of canned item states and
    recording every write argv."""

    def __init__(self, reads):
        self.reads = list(reads)
        self.calls: list[list[str]] = []

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append(argv)
        joined = " ".join(argv)
        if "query($id: ID!)" in joined:
            payload = self.reads.pop(0)
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    @property
    def writes(self):
        return [c for c in self.calls if "query($id: ID!)" not in " ".join(c)]


# --- idempotency key ------------------------------------------------------------
def test_idempotency_key_is_deterministic_over_the_claim_tuple():
    a = idempotency_key("o/r", "item-1", "instance-a", "2026-06-10T00/PT4H")
    b = idempotency_key("o/r", "item-1", "instance-a", "2026-06-10T00/PT4H")
    assert a == b and len(a) == 64 and int(a, 16) >= 0


def test_idempotency_key_varies_with_every_tuple_member():
    base = ("o/r", "item-1", "instance-a", "w1")
    keys = {idempotency_key(*base)}
    for i in range(4):
        variant = list(base)
        variant[i] += "-x"
        keys.add(idempotency_key(*variant))
    assert len(keys) == 5


# --- reader ----------------------------------------------------------------------
def test_read_backlog_item_parses_status_assignees_claimed_at():
    runner = _Runner([_node(status="Running", assignees=("alice",), claimed_at="2026-06-10T08:00:00Z")])
    item = read_backlog_item(REF, ITEM, gh_runner=runner)
    assert item == BacklogItem(
        item_id=ITEM.item_id, status="Running", assignees=("alice",),
        claimed_at="2026-06-10T08:00:00Z",
    )


def test_read_transport_failure_raises_forge_config_error():
    def runner(argv, input_text=None):
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="boom")
    with pytest.raises(ForgeConfigError):
        read_backlog_item(REF, ITEM, gh_runner=runner)


# --- drift check (pure) ------------------------------------------------------------
def test_drift_check_green_when_state_matches():
    a = BacklogItem("i", "Ready", ("alice",))
    assert not drift_check(a, BacklogItem("i", "Ready", ("alice",))).drifted


def test_drift_check_fires_on_status_or_assignee_change():
    expected = BacklogItem("i", "Ready", ())
    assert drift_check(expected, BacklogItem("i", "Running", ())).drifted
    assert drift_check(expected, BacklogItem("i", "Ready", ("bob",))).drifted


# --- plan-by-default ----------------------------------------------------------------
def test_project_claim_plan_by_default_writes_nothing():
    runner = _Runner([])
    plan = project_claim(
        REF, ITEM, claimant_login="alice", claimant_instance="inst-a",
        lease_window="w1", claimed_at="2026-06-10T08:00:00Z", gh_runner=runner,
    )
    assert isinstance(plan, ClaimPlan) and plan.applied is False
    assert runner.calls == []
    assert plan.idempotency_key == idempotency_key(REF.repo, ITEM.item_id, "inst-a", "w1")


def test_project_claim_apply_writes_assignee_status_and_claimed_at():
    runner = _Runner([])
    project_claim(
        REF, ITEM, claimant_login="alice", claimant_instance="inst-a",
        lease_window="w1", claimed_at="2026-06-10T08:00:00Z",
        apply=True, gh_runner=runner,
    )
    joined = [" ".join(c) for c in runner.writes]
    assert any(f"repos/{REF.repo}/issues/{ITEM.issue_number}/assignees" in c for c in joined)
    assert any("updateProjectV2ItemFieldValue" in c and "option=opt_running" in c for c in joined)
    assert any("text=2026-06-10T08:00:00Z" in c for c in joined)


# --- the claim protocol: drift-check → write → back-off re-read → reconcile ----------
def _claim(runner, *, apply=True, expected=None, claimed_at="2026-06-10T08:00:00Z"):
    return claim_item(
        REF, ITEM, claimant_login="alice", claimant_instance="inst-a",
        lease_window="w1", claimed_at=claimed_at,
        expected=expected or BacklogItem(ITEM.item_id, "Ready", ()),
        apply=apply, gh_runner=runner,
        backoff_seconds=lambda: 0.0, sleeper=lambda s: None,
    )


def test_claim_drift_before_write_escalates_without_writing():
    runner = _Runner([_node(status="Running", assignees=())])
    result = _claim(runner)
    assert isinstance(result, Escalation)
    assert "drift-check" in result.reason
    assert runner.writes == []


def test_claim_on_already_held_item_escalates_not_overwrites():
    runner = _Runner([_node(status="Ready", assignees=("bob",))])
    result = _claim(runner, expected=BacklogItem(ITEM.item_id, "Ready", ("bob",)))
    assert isinstance(result, Escalation)
    assert result.winner == "bob"
    assert runner.writes == []  # a second live claimant NEVER silently overwrites


def test_claim_happy_path_writes_then_verifies():
    runner = _Runner([
        _node(status="Ready", assignees=()),                                  # drift-check read
        _node(status="Running", assignees=("alice",), claimed_at="2026-06-10T08:00:00Z"),  # verify read
    ])
    result = _claim(runner)
    assert isinstance(result, ClaimPlan) and result.applied
    assert len(runner.writes) == 3


def test_claim_toctou_collision_after_write_escalates_earlier_claimant_wins():
    runner = _Runner([
        _node(status="Ready", assignees=()),
        _node(status="Running", assignees=("alice", "mallory"),
              claimed_at="2026-06-10T07:59:00Z"),  # mallory's claim is EARLIER
    ])
    result = _claim(runner)
    assert isinstance(result, Escalation)
    assert result.winner == "mallory"
    # the competing claim is surfaced, not removed: no extra write happened
    assert len(runner.writes) == 3


def test_claim_plan_mode_stops_before_any_write():
    runner = _Runner([_node(status="Ready", assignees=())])
    result = _claim(runner, apply=False)
    assert isinstance(result, ClaimPlan) and result.applied is False
    assert runner.writes == []


def test_reconcile_no_competitor_returns_none():
    plan = ClaimPlan(item=ITEM, claimant_login="alice",
                     claimed_at="2026-06-10T08:00:00Z", idempotency_key="k")
    observed = BacklogItem(ITEM.item_id, "Running", ("alice",), "2026-06-10T08:00:00Z")
    assert reconcile_competing_claim(ITEM, plan, observed) is None


def test_no_force_or_overwrite_code_path_exists():
    import creator_engine_validator.forge.backlog as mod
    suspicious = [n for n in dir(mod) if "force" in n.lower() or "overwrite" in n.lower()]
    assert suspicious == []


# --- zero live network -----------------------------------------------------------
def test_zero_live_network(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("backlog adapter must not touch a live forge in tests")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    runner = _Runner([_node()])
    item = read_backlog_item(REF, ITEM, gh_runner=runner)
    assert item.status == "Ready"
