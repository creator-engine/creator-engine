"""Unit tests for the v3 G-3.2 read-only forge change-status ops.

``forge.review_state`` / ``checks_state`` / ``change_conflicts`` are pure, read-only
observations of a change's merge-gates (the §8.3 contract: merge-blocked-until-reviewed,
all required checks green, up-to-date / no conflict). Each takes a value-free
:class:`ChangeRef`, issues exactly one GraphQL read through an injectable ``GhRunner``,
returns a frozen value-free result type, refuses BEFORE any forge call on a change with no
open PR (``pr_number is None``) / a malformed repo, and surfaces a transport failure as
``ForgeConfigError``. These tests inject a fake ``GhRunner`` returning canned GraphQL JSON
and perform ZERO live network / subprocess.
"""

import json
import socket
import subprocess

import pytest

from creator_engine_validator.forge import (
    ChangeRef,
    ChangeStatusRefused,
    ChecksState,
    ConflictState,
    ForgeConfigError,
    ReviewState,
    change_conflicts,
    checks_state,
    review_state,
)

_REPO = "creator-engine/creator-engine"


def _change(*, pr_number=126, repo=_REPO) -> ChangeRef:
    """An applied (claimed) ChangeRef carrying a real pr_number — the read-op input."""
    return ChangeRef(
        repo=repo,
        branch="ce/run-1",
        base="main",
        pr_number=pr_number,
        head_sha="d" * 40,
        manifest_paths=("a.py",),
        plan_ref="a" * 64,
        changed=False,
        applied=True,
        verified=True,
    )


def _runner(payload, *, rc=0, stderr=""):
    """A fake GhRunner returning canned GraphQL JSON, recording every (argv) call."""
    calls: list[list[str]] = []

    def run(argv, input_text=None):
        calls.append(list(argv))
        stdout = json.dumps(payload) if payload is not None else ""
        return subprocess.CompletedProcess(list(argv), rc, stdout=stdout, stderr=stderr)

    run.calls = calls  # type: ignore[attr-defined]
    return run


def _pr_payload(**pr_fields) -> dict:
    return {"data": {"repository": {"pullRequest": pr_fields}}}


# --------------------------------------------------------------------------- review_state
def test_review_state_reads_decision_approved():
    r = _runner(_pr_payload(reviewDecision="APPROVED"))
    state = review_state(_change(), gh_runner=r)
    assert isinstance(state, ReviewState)
    assert state.pr_number == 126
    assert state.review_decision == "APPROVED"
    assert state.approved is True
    assert len(r.calls) == 1 and "graphql" in r.calls[0]


def test_review_state_review_required_not_approved():
    r = _runner(_pr_payload(reviewDecision="REVIEW_REQUIRED"))
    state = review_state(_change(), gh_runner=r)
    assert state.review_decision == "REVIEW_REQUIRED"
    assert state.approved is False


# --------------------------------------------------------------------------- checks_state
def test_checks_state_reads_rollup_success():
    payload = _pr_payload(
        headRefOid="e" * 40,
        commits={"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]},
    )
    state = checks_state(_change(), gh_runner=_runner(payload))
    assert isinstance(state, ChecksState)
    assert state.head_sha == "e" * 40
    assert state.rollup_state == "SUCCESS"
    assert state.all_green is True


def test_checks_state_pending_not_green():
    payload = _pr_payload(
        headRefOid="e" * 40,
        commits={"nodes": [{"commit": {"statusCheckRollup": {"state": "PENDING"}}}]},
    )
    state = checks_state(_change(), gh_runner=_runner(payload))
    assert state.rollup_state == "PENDING"
    assert state.all_green is False


def test_checks_state_null_rollup_is_not_green():
    payload = _pr_payload(headRefOid="e" * 40, commits={"nodes": [{"commit": {"statusCheckRollup": None}}]})
    state = checks_state(_change(), gh_runner=_runner(payload))
    assert state.all_green is False


# ----------------------------------------------------------------------- change_conflicts
def test_change_conflicts_clean_is_up_to_date():
    state = change_conflicts(
        _change(), gh_runner=_runner(_pr_payload(mergeStateStatus="CLEAN", mergeable="MERGEABLE"))
    )
    assert isinstance(state, ConflictState)
    assert state.merge_state_status == "CLEAN"
    assert state.mergeable == "MERGEABLE"
    assert state.up_to_date is True


def test_change_conflicts_behind_is_not_up_to_date():
    state = change_conflicts(
        _change(), gh_runner=_runner(_pr_payload(mergeStateStatus="BEHIND", mergeable="MERGEABLE"))
    )
    assert state.merge_state_status == "BEHIND"
    assert state.up_to_date is False


# ------------------------------------------------------------------ refuse-before-side-effect
@pytest.mark.parametrize("op", [review_state, checks_state, change_conflicts])
def test_refuse_when_no_open_pr(op):
    r = _runner(_pr_payload(reviewDecision="APPROVED"))
    change = _change(pr_number=None)  # plan-by-default ChangeRef — no PR to read yet
    with pytest.raises(ChangeStatusRefused):
        op(change, gh_runner=r)
    assert r.calls == []  # refused BEFORE any forge call


@pytest.mark.parametrize("op", [review_state, checks_state, change_conflicts])
def test_refuse_malformed_repo(op):
    r = _runner(_pr_payload(reviewDecision="APPROVED"))
    with pytest.raises(ChangeStatusRefused):
        op(_change(repo="not-a-repo"), gh_runner=r)
    assert r.calls == []


# ------------------------------------------------------------------------ transport failure
@pytest.mark.parametrize("op", [review_state, checks_state, change_conflicts])
def test_transport_failure_raises_forge_config_error(op):
    r = _runner(None, rc=1, stderr="boom")
    with pytest.raises(ForgeConfigError):
        op(_change(), gh_runner=r)


# ---------------------------------------------------------------------- G-3.7.0b redaction
_LEAK_TOKEN = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
_LEAK_STDERR = f"HTTP 401: Bad credentials (token {_LEAK_TOKEN})"


@pytest.mark.parametrize("op", [review_state, checks_state, change_conflicts])
def test_status_read_error_message_redacts_leaked_token(op):
    # a credential leaked into the GraphQL-read stderr is masked in the raised exception
    r = _runner(None, rc=1, stderr=_LEAK_STDERR)
    with pytest.raises(ForgeConfigError) as ei:
        op(_change(), gh_runner=r)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg
    assert "<redacted>" in msg
    assert _REPO in msg  # the non-secret identifier remains for diagnosis


# --------------------------------------------------------------------------- value-free
def test_results_carry_no_secret():
    from dataclasses import fields

    rs = review_state(_change(), gh_runner=_runner(_pr_payload(reviewDecision="APPROVED")))
    cs = checks_state(
        _change(),
        gh_runner=_runner(
            _pr_payload(headRefOid="e" * 40, commits={"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]})
        ),
    )
    co = change_conflicts(_change(), gh_runner=_runner(_pr_payload(mergeStateStatus="CLEAN", mergeable="MERGEABLE")))
    for result in (rs, cs, co):
        assert not hasattr(result, "value")
        assert "value" not in {f.name for f in fields(result)}
        assert "token" not in {f.name for f in fields(result)}


# ----------------------------------------------------------------------------- zero-live
def test_zero_live_subprocess_or_socket(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("change-status ops must use the injected fake gh_runner, not a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    state = review_state(_change(), gh_runner=_runner(_pr_payload(reviewDecision="APPROVED")))
    assert state.approved is True


# ------------------------------------------------------------------------------- purity
def test_change_status_registers_no_check_and_no_backend():
    from creator_engine_validator.checks import registered_checks
    from creator_engine_validator.runner import available_backends

    assert len(registered_checks()) == 52  # G-6 added ce_scope; v3.5-C A-C1..A-C4 added decision_record + storage_tier_finding + peer_authority + forge_claim_dedup; v3.5-E.3 E3-G1 added install_answers
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell")  # +openshell (v3.5-A.2a)
