"""Unit tests for the v3 G-3.0 forge-native change-lifecycle primitive.

``forge.open_change`` takes a governed run's authored head branch and opens (or, when
one already exists, claims/updates) exactly ONE pull request for it against a base
branch — the "push = claim" idempotency of §2.1. It is plan-by-default (``apply=False``
reads the open-PR state and returns a non-mutating :class:`ChangeRef`), refuses an
ill-formed request BEFORE any forge call (refuse-before-side-effect), and carries NO
token (auth lives in the injected ``GhRunner`` env). All forge I/O goes through an
injectable ``GhRunner``; these tests inject a fake runner returning canned ``gh api``
JSON and perform ZERO live network / subprocess.
"""

import json
import subprocess

import pytest

from creator_engine_validator.forge import ForgeConfigError
from creator_engine_validator.forge.change import (
    ChangeRef,
    OpenChangeRefused,
    open_change,
)

_PLAN_REF = "a" * 64  # 64-hex policy/plan digest
_REPO = "creator-engine/creator-engine"
_MANIFEST = (
    # Per-PR carrier convention (ce-ops#21): the carrier filename stem is
    # ``branch_slug("ce/run-abc") == "ce-run-abc"``.
    ".ce/pr-manifests/ce-run-abc.md",
    "validators/creator_engine_validator/forge/change.py",
)


def _args(**overrides) -> dict:
    base = dict(
        repo=_REPO,
        branch="ce/run-abc",
        base="main",
        manifest_paths=_MANIFEST,
        plan_ref=_PLAN_REF,
    )
    base.update(overrides)
    return base


def _fake_runner(*, pulls=None, created=None, get_rc=0, post_rc=0, err="boom"):
    """A GhRunner answering the GET-open-pulls list and the POST-create-PR from canned data.

    Stateful so an ``apply=True`` create (GET empty -> POST -> GET re-read) re-reads the
    newly-created PR. Records every ``(argv, input_text)`` so refuse paths can assert
    ``runner.calls == []`` and the apply path can assert the exact POST body. ``err`` is
    the stderr returned on a non-zero exit (override it to a token-bearing stderr to
    exercise the G-3.7.0b redaction of an exception message).
    """
    state = {"pulls": list(pulls or [])}
    calls: list[list[str]] = []
    inputs: list[str | None] = []

    def run(argv, input_text=None):
        calls.append(list(argv))
        inputs.append(input_text)
        method = argv[argv.index("-X") + 1] if "-X" in argv else "GET"
        is_pulls = any("/pulls" in a for a in argv)
        if method == "POST" and is_pulls:
            new = created or {"number": 99, "head": {"sha": "newsha"}}
            state["pulls"].append(new)
            return subprocess.CompletedProcess(
                argv, post_rc,
                stdout=json.dumps(new) if post_rc == 0 else "",
                stderr="" if post_rc == 0 else err,
            )
        # GET (initial read or re-read)
        return subprocess.CompletedProcess(
            argv, get_rc,
            stdout=json.dumps(state["pulls"]) if get_rc == 0 else "",
            stderr="" if get_rc == 0 else err,
        )

    run.calls = calls  # type: ignore[attr-defined]
    run.inputs = inputs  # type: ignore[attr-defined]
    return run


# ---------------------------------------------------------------------------
# Refuse BEFORE any forge call (refuse-before-side-effect) — runner NEVER called
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "overrides",
    [
        {"repo": "no-slash"},
        {"branch": ""},
        {"branch": "   "},
        {"base": ""},
        {"base": "ce/run-abc"},  # base == branch (self-targeting)
        {"manifest_paths": ()},
        {"plan_ref": ""},
        {"plan_ref": "not-a-64-hex-digest"},
    ],
)
def test_refuses_before_any_forge_call(overrides):
    runner = _fake_runner()
    with pytest.raises(OpenChangeRefused):
        open_change(**_args(**overrides), gh_runner=runner)
    assert runner.calls == []


def test_open_change_refused_is_a_forge_refusal_with_code():
    runner = _fake_runner()
    with pytest.raises(ForgeConfigError):  # OpenChangeRefused subclasses ForgeConfigRefused/Error
        open_change(**_args(repo="bad"), gh_runner=runner)
    assert OpenChangeRefused.code == "V3-FORGE-OPENCHANGE-REFUSED"


# ---------------------------------------------------------------------------
# Plan-by-default (apply=False) — read-only; create-plan vs idempotent-claim
# ---------------------------------------------------------------------------
def test_plan_create_when_no_open_pr():
    runner = _fake_runner(pulls=[])
    ref = open_change(**_args(), gh_runner=runner)
    assert isinstance(ref, ChangeRef)
    assert ref.pr_number is None and ref.head_sha is None
    assert ref.changed is True and ref.applied is False and ref.verified is False
    assert ref.repo == _REPO and ref.branch == "ce/run-abc" and ref.base == "main"
    assert ref.manifest_paths == _MANIFEST and ref.plan_ref == _PLAN_REF
    # The ONLY call was a read (GET); never a mutation.
    assert len(runner.calls) == 1
    assert runner.calls[0][:4] == ["gh", "api", "-X", "GET"]
    assert any("/pulls" in a for a in runner.calls[0])
    assert not any("POST" in c or "PATCH" in c for c in runner.calls)


def test_plan_claim_is_idempotent_when_one_open_pr():
    runner = _fake_runner(pulls=[{"number": 7, "head": {"sha": "abc123"}}])
    ref = open_change(**_args(), gh_runner=runner)
    assert ref.pr_number == 7 and ref.head_sha == "abc123"
    assert ref.changed is False and ref.applied is False and ref.verified is True
    # Idempotent read-only: a PR already claims the branch; no mutation planned.
    assert len(runner.calls) == 1
    assert runner.calls[0][:4] == ["gh", "api", "-X", "GET"]
    assert not any("POST" in c or "PATCH" in c for c in runner.calls)


# ---------------------------------------------------------------------------
# apply=True — POST exactly one PR then re-read to verify (covered via the fake)
# ---------------------------------------------------------------------------
def test_apply_creates_one_pr_then_reread_verifies():
    runner = _fake_runner(pulls=[], created={"number": 99, "head": {"sha": "newsha"}})
    ref = open_change(**_args(), apply=True, gh_runner=runner)
    assert ref.applied is True and ref.verified is True and ref.changed is True
    assert ref.pr_number == 99 and ref.head_sha == "newsha"
    # Exactly one POST to .../pulls, and the body carries head/base + the marker + paths.
    post_calls = [c for c in runner.calls if "POST" in c]
    assert len(post_calls) == 1
    post_idx = runner.calls.index(post_calls[0])
    body = json.loads(runner.inputs[post_idx])
    assert body["head"] == "ce/run-abc" and body["base"] == "main"
    assert f"ce-policy-sha: {_PLAN_REF}" in body["body"]
    for p in _MANIFEST:
        assert p in body["body"]
    # Sequence: GET (read) -> POST (create) -> GET (re-read).
    methods = [c[c.index("-X") + 1] for c in runner.calls if "-X" in c]
    assert methods == ["GET", "POST", "GET"]


def test_apply_is_idempotent_no_duplicate_pr_when_one_exists():
    runner = _fake_runner(pulls=[{"number": 7, "head": {"sha": "abc123"}}])
    ref = open_change(**_args(), apply=True, gh_runner=runner)
    assert ref.applied is True and ref.verified is True and ref.changed is False
    assert ref.pr_number == 7 and ref.head_sha == "abc123"
    assert not any("POST" in c for c in runner.calls)  # no duplicate PR


# ---------------------------------------------------------------------------
# Transport failure is distinct from a policy refusal
# ---------------------------------------------------------------------------
def test_transport_failure_raises_forge_config_error():
    runner = _fake_runner(get_rc=1)
    with pytest.raises(ForgeConfigError):
        open_change(**_args(), gh_runner=runner)


def test_apply_post_failure_raises_forge_config_error():
    runner = _fake_runner(pulls=[], post_rc=1)
    with pytest.raises(ForgeConfigError):
        open_change(**_args(), apply=True, gh_runner=runner)


# ---------------------------------------------------------------------------
# G-3.7.0b — a leaked credential in gh stderr is masked in the raised exception
# ---------------------------------------------------------------------------
_LEAK_TOKEN = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
_LEAK_STDERR = f"HTTP 401: Bad credentials (token {_LEAK_TOKEN})"


def test_read_error_message_redacts_leaked_token():
    runner = _fake_runner(get_rc=1, err=_LEAK_STDERR)
    with pytest.raises(ForgeConfigError) as ei:
        open_change(**_args(), gh_runner=runner)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg
    assert "<redacted>" in msg
    assert _REPO in msg  # the non-secret identifier remains for diagnosis


def test_open_post_error_message_redacts_leaked_token():
    runner = _fake_runner(pulls=[], post_rc=1, err=_LEAK_STDERR)
    with pytest.raises(ForgeConfigError) as ei:
        open_change(**_args(), apply=True, gh_runner=runner)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg
    assert "<redacted>" in msg


# ---------------------------------------------------------------------------
# Secret-free value type — to_dict round-trips; repr/str carry no token
# ---------------------------------------------------------------------------
def test_changeref_to_dict_and_redacted_repr():
    runner = _fake_runner(pulls=[{"number": 7, "head": {"sha": "abc123"}}])
    ref = open_change(**_args(), gh_runner=runner)
    d = ref.to_dict()
    assert d["repo"] == _REPO and d["pr_number"] == 7 and d["plan_ref"] == _PLAN_REF
    assert d["manifest_paths"] == list(_MANIFEST)
    # Defensive: no token field; repr is value-redacted and leaks no ghs_ token.
    assert "ghs_" not in repr(ref) and "ghs_" not in str(ref)
    assert "<redacted>" in repr(ref)
    assert not any(getattr(ref, attr, None) for attr in ("value", "token"))


# ---------------------------------------------------------------------------
# ZERO live network — only the injected runner is ever the transport
# ---------------------------------------------------------------------------
def test_zero_live_network(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("open_change must not touch a live forge")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    runner = _fake_runner(pulls=[])
    ref = open_change(**_args(), apply=True, gh_runner=runner)
    assert ref.applied is True
    assert len(runner.calls) == 3  # GET + POST + GET; the fake was the only transport


# ---------------------------------------------------------------------------
# Invariant regression (defense-in-depth) — a pure adapter slice
# ---------------------------------------------------------------------------
def test_slice_registers_no_check_and_adds_no_backend():
    from creator_engine_validator.checks import registered_checks
    from creator_engine_validator.runner import available_backends

    assert len(registered_checks()) == 56  # G-6 added ce_scope; v3.5-C A-C1..A-C4 added decision_record + storage_tier_finding + peer_authority + forge_claim_dedup; v3.5-E.3 E3-G1 added install_answers; ce-ops#26 added seat_event; ce-ops#142 added ce_computer_use_authority_envelope; ce-ops#145 added ce_playbook_format; ce-ops#167 added ce_brain_assertions
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell", "os-native")  # +openshell (v3.5-A.2a)
