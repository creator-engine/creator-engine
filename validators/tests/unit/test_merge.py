"""Unit tests for the v3 G-3.3 forge-native gated merge op.

``forge.merge`` squash-merges a change's PR through an injectable ``GhRunner``, **gated** on
the three G-3.2 reads (review approved + required checks green + ``mergeable == "MERGEABLE"``).
It is **plan-by-default** (``apply=False`` observes the gate and mutates nothing) and
**refuses before any forge call** (``MergeRefused``) on a malformed change / no open PR /
``apply`` without a head SHA, or — under ``apply=True`` — on a gate-ineligible PR (never
merge an ungated PR). A transport failure surfaces as ``ForgeConfigError``. These tests
inject a fake ``GhRunner`` answering both the GraphQL gate reads and the REST merge PUT, and
perform ZERO live network / subprocess.
"""

import json
import socket
import subprocess

import pytest

from creator_engine_validator.forge import (
    ChangeRef,
    ForgeConfigError,
    MergeRefused,
    MergeResult,
    merge,
)

_REPO = "creator-engine/creator-engine"
_HEAD = "d" * 40


def _change(*, pr_number=129, repo=_REPO, head_sha=_HEAD) -> ChangeRef:
    """An applied (claimed) ChangeRef carrying a real pr_number — the merge-op input."""
    return ChangeRef(
        repo=repo,
        branch="ce/run-1",
        base="main",
        pr_number=pr_number,
        head_sha=head_sha,
        manifest_paths=("a.py",),
        plan_ref="a" * 64,
        changed=False,
        applied=True,
        verified=True,
    )


def _runner(
    *,
    review="APPROVED",
    rollup="SUCCESS",
    merge_state="CLEAN",
    mergeable="MERGEABLE",
    merge_resp=None,
    gate_rc=0,
    put_rc=0,
    stderr="",
):
    """A fake GhRunner answering the 3 GraphQL gate reads (routed by query field) AND the
    REST ``PUT .../merge``. Records every ``(argv, input_text)`` so refuse paths can assert
    ``runner.calls == []`` and the apply path can assert the exact merge PUT body.
    """
    calls: list[list[str]] = []
    inputs: list[str | None] = []

    def run(argv, input_text=None):
        calls.append(list(argv))
        inputs.append(input_text)
        is_put_merge = "PUT" in argv and any(str(a).endswith("/merge") for a in argv)
        if is_put_merge:
            resp = merge_resp if merge_resp is not None else {"sha": "f" * 40, "merged": True, "message": "Merged"}
            return subprocess.CompletedProcess(
                list(argv), put_rc, stdout=json.dumps(resp) if put_rc == 0 else "", stderr=stderr
            )
        # else a GraphQL gate read — route by which field the query selects
        query = next((str(a) for a in argv if str(a).startswith("query=")), "")
        if "reviewDecision" in query:
            pr = {"reviewDecision": review}
        elif "statusCheckRollup" in query:
            pr = {"headRefOid": "e" * 40, "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": rollup}}}]}}
        elif "mergeStateStatus" in query:
            pr = {"mergeStateStatus": merge_state, "mergeable": mergeable}
        else:  # pragma: no cover - defensive
            pr = {}
        payload = {"data": {"repository": {"pullRequest": pr}}}
        return subprocess.CompletedProcess(
            list(argv), gate_rc, stdout=json.dumps(payload) if gate_rc == 0 else "", stderr=stderr
        )

    run.calls = calls  # type: ignore[attr-defined]
    run.inputs = inputs  # type: ignore[attr-defined]
    return run


def _put_calls(r):
    return [c for c in r.calls if "PUT" in c and any(str(a).endswith("/merge") for a in c)]


# ------------------------------------------------------------------- plan-mode (apply=False)
def test_plan_mode_eligible_does_not_merge():
    r = _runner()  # approved + SUCCESS + MERGEABLE
    result = merge(_change(), gh_runner=r)
    assert isinstance(result, MergeResult)
    assert result.pr_number == 129
    assert result.eligible is True
    assert result.would_merge is True
    assert result.merged is False
    assert result.merge_commit_sha is None
    assert result.applied is False
    # the gate snapshot is surfaced
    assert result.review_decision == "APPROVED"
    assert result.rollup_state == "SUCCESS"
    assert result.merge_state_status == "CLEAN"
    assert result.mergeable == "MERGEABLE"
    # composed the three gate reads, issued NO merge PUT
    assert len(r.calls) == 3 and all("graphql" in c for c in r.calls)
    assert _put_calls(r) == []


def test_plan_mode_not_approved_ineligible():
    r = _runner(review="REVIEW_REQUIRED")
    result = merge(_change(), gh_runner=r)
    assert result.eligible is False
    assert result.merged is False
    assert _put_calls(r) == []


def test_plan_mode_not_green_ineligible():
    r = _runner(rollup="PENDING")
    result = merge(_change(), gh_runner=r)
    assert result.eligible is False
    assert _put_calls(r) == []


def test_plan_mode_not_mergeable_ineligible():
    # CONFLICTING is ineligible even though merge_state_status could read up-to-date
    r = _runner(merge_state="DIRTY", mergeable="CONFLICTING")
    result = merge(_change(), gh_runner=r)
    assert result.eligible is False
    assert _put_calls(r) == []


# ------------------------------------------------------------------- apply-mode (apply=True)
def test_apply_eligible_merges_squash_head_pinned():
    r = _runner()
    result = merge(_change(), apply=True, gh_runner=r)
    assert result.merged is True
    assert result.merge_commit_sha == "f" * 40
    assert result.eligible is True
    assert result.applied is True
    # exactly one merge PUT, head-pinned squash
    puts = _put_calls(r)
    assert len(puts) == 1
    put_idx = r.calls.index(puts[0])
    body = json.loads(r.inputs[put_idx])
    assert body == {"merge_method": "squash", "sha": _HEAD}
    assert any(str(a) == f"repos/{_REPO}/pulls/129/merge" for a in puts[0])


def test_apply_ineligible_refuses_without_merging():
    r = _runner(review="REVIEW_REQUIRED")
    with pytest.raises(MergeRefused):
        merge(_change(), apply=True, gh_runner=r)
    # the gate was read, but NO merge PUT was issued (never merge an ungated PR)
    assert _put_calls(r) == []


# --------------------------------------------------------------- refuse-before-side-effect
def test_refuse_when_no_open_pr():
    r = _runner()
    with pytest.raises(MergeRefused):
        merge(_change(pr_number=None), apply=True, gh_runner=r)
    assert r.calls == []


def test_refuse_malformed_repo():
    r = _runner()
    with pytest.raises(MergeRefused):
        merge(_change(repo="not-a-repo"), gh_runner=r)
    assert r.calls == []


def test_refuse_apply_without_head_sha():
    r = _runner()
    with pytest.raises(MergeRefused):
        merge(_change(head_sha=None), apply=True, gh_runner=r)
    assert r.calls == []  # refused before any gate read


def test_plan_mode_allows_missing_head_sha():
    # plan mode needs no head-pin — a head_sha=None ChangeRef still observes the gate
    r = _runner()
    result = merge(_change(head_sha=None), gh_runner=r)
    assert result.eligible is True
    assert result.merged is False
    assert _put_calls(r) == []


# ------------------------------------------------------------------------ transport failure
def test_gate_read_transport_failure_raises_forge_config_error():
    r = _runner(gate_rc=1, stderr="boom")
    with pytest.raises(ForgeConfigError):
        merge(_change(), gh_runner=r)


def test_merge_put_transport_failure_raises_forge_config_error():
    # gate eligible, but the merge PUT returns non-zero (e.g. 405 not mergeable / 409 sha mismatch)
    r = _runner(put_rc=1, stderr="not mergeable")
    with pytest.raises(ForgeConfigError):
        merge(_change(), apply=True, gh_runner=r)


# ---------------------------------------------------------------------- G-3.7.0b redaction
_LEAK_TOKEN = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
_LEAK_STDERR = f"HTTP 401: Bad credentials (token {_LEAK_TOKEN})"


def test_merge_put_error_message_redacts_leaked_token():
    # a credential leaked into the merge-PUT stderr is masked in the raised exception
    r = _runner(put_rc=1, stderr=_LEAK_STDERR)
    with pytest.raises(ForgeConfigError) as ei:
        merge(_change(), apply=True, gh_runner=r)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg
    assert "<redacted>" in msg


# --------------------------------------------------------------------------- value-free
def test_result_carries_no_secret():
    from dataclasses import fields

    result = merge(_change(), gh_runner=_runner())
    assert not hasattr(result, "value")
    names = {f.name for f in fields(result)}
    assert "value" not in names
    assert "token" not in names


# ----------------------------------------------------------------------------- zero-live
def test_zero_live_subprocess_or_socket(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("merge must use the injected fake gh_runner, not a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    result = merge(_change(), apply=True, gh_runner=_runner())
    assert result.merged is True


# ------------------------------------------------------------------------------- purity
def test_merge_registers_no_check_and_no_backend():
    from creator_engine_validator.checks import registered_checks
    from creator_engine_validator.runner import available_backends

    assert len(registered_checks()) == 52  # G-6 added ce_scope; v3.5-C A-C1..A-C4 added decision_record + storage_tier_finding + peer_authority + forge_claim_dedup; v3.5-E.3 E3-G1 added install_answers
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell")  # +openshell (v3.5-A.2a)
