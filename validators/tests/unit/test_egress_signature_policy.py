"""Tests for the per-policy commit-signature requirement (ce-ops#281).

``require_signed_commits`` is a new :class:`~egress_broker.policy.BrokerPolicy` field
(default ``True`` = back-compat, fail-closed). When ``False`` the signature gate is SKIPPED
but ALL other gates remain enforced: author allow-list, branch namespace, forbidden-branch,
rate-limit, and head-sha well-formedness.

Security contract:
- require_signed_commits=True + unsigned commit  → REJECT  (signature gate unchanged)
- require_signed_commits=False + unsigned commit → ALLOW   (signature gate skipped)
- require_signed_commits=False + bad author      → REJECT  (author gate enforced)
- require_signed_commits=False + forbidden branch → REJECT (branch gate enforced)
- require_signed_commits=False + rate exceeded   → REJECT  (rate gate enforced)

Config loader contract:
- key absent → True  (fail-closed default)
- key = null → True  (fail-closed; only explicit boolean False opts out)
- key = 0    → True  (fail-closed; only explicit boolean False opts out)
- key = false → False (the ONLY accepted opt-out)

Zero live crypto, network, or git calls — pure-value inputs only.
"""
from __future__ import annotations

import pytest

from egress_broker.config import _build_policy
from egress_broker.policy import (
    BrokerPolicy,
    CommitFacts,
    Decision,
    RateState,
    evaluate,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
_GOOD_SHA = "c" * 40
_AUTHORIZED_LOGIN = "cedev4vps-coder"
_AUTHORIZED_EMAIL = f"150906340+{_AUTHORIZED_LOGIN}@users.noreply.github.com"


def _policy(*, require_signed_commits: bool = True, **over) -> BrokerPolicy:
    base = dict(
        base_branch="main",
        allowed_branch_namespaces=("ce-",),
        forbidden_branches=frozenset({"develop"}),
        authorized_emails=frozenset(),
        authorized_logins=frozenset({_AUTHORIZED_LOGIN}),
        max_pushes_per_window=10,
        window_seconds=3600,
        require_signed_commits=require_signed_commits,
    )
    base.update(over)
    return BrokerPolicy(**base)


def _unsigned_facts(**over) -> CommitFacts:
    """A commit with NO signature (signature_status='N')."""
    base = dict(
        head_sha=_GOOD_SHA,
        signature_status="N",
        signer="",
        author_name="ce-dev-4",
        author_email=_AUTHORIZED_EMAIL,
    )
    base.update(over)
    return CommitFacts(**base)


def _signed_facts(**over) -> CommitFacts:
    """A commit with a fully-trusted good signature (signature_status='G')."""
    base = dict(
        head_sha=_GOOD_SHA,
        signature_status="G",
        signer=_AUTHORIZED_LOGIN,
        author_name="ce-dev-4",
        author_email=_AUTHORIZED_EMAIL,
    )
    base.update(over)
    return CommitFacts(**base)


def _check(decision: Decision, name: str):
    for c in decision.checks:
        if c.name == name:
            return c
    raise AssertionError(f"no check named {name!r} in {[c.name for c in decision.checks]}")


# ---------------------------------------------------------------------------
# (a) require_signed_commits=True + unsigned commit → REJECT
# ---------------------------------------------------------------------------
def test_require_signed_true_unsigned_denies():
    """Back-compat: the default (True) still rejects unsigned commits."""
    pol = _policy(require_signed_commits=True)
    d = evaluate(_unsigned_facts(), "ce-feature", pol)
    assert d.allowed is False
    assert not _check(d, "signature_valid").passed
    # The detail must NOT say "disabled by policy"
    assert "disabled by policy" not in _check(d, "signature_valid").detail


@pytest.mark.parametrize("status", ["B", "U", "X", "Y", "R", "E", "", "NONE"])
def test_require_signed_true_non_good_statuses_deny(status):
    """Every non-G status is a denial when require_signed_commits=True."""
    pol = _policy(require_signed_commits=True)
    d = evaluate(_unsigned_facts(signature_status=status), "ce-feature", pol)
    assert d.allowed is False
    assert not _check(d, "signature_valid").passed


# ---------------------------------------------------------------------------
# (b) require_signed_commits=False + unsigned commit → ALLOW
# ---------------------------------------------------------------------------
def test_require_signed_false_unsigned_allows():
    """Contained seat: an unsigned commit is allowed when require_signed_commits=False."""
    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(), "ce-feature", pol)
    assert d.allowed is True
    # The signature_valid check is present but passes (skipped = synthetic pass)
    sig = _check(d, "signature_valid")
    assert sig.passed is True
    assert "disabled by policy" in sig.detail


@pytest.mark.parametrize("status", ["N", "B", "U", "X", "", "NONE"])
def test_require_signed_false_various_statuses_allow(status):
    """Any signature_status is accepted when require_signed_commits=False."""
    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(signature_status=status), "ce-feature", pol)
    assert d.allowed is True


# ---------------------------------------------------------------------------
# (c) require_signed_commits=False + bad/unauthorized author → REJECT
# ---------------------------------------------------------------------------
def test_require_signed_false_unauthorized_author_denies():
    """Author gate still enforced even when signature gate is off."""
    pol = _policy(require_signed_commits=False)
    attacker_facts = _unsigned_facts(
        author_email="99+evil-attacker@users.noreply.github.com"
    )
    d = evaluate(attacker_facts, "ce-feature", pol)
    assert d.allowed is False
    assert not _check(d, "author_authorized").passed
    # Signature is skipped (passes), author is the denial reason
    assert _check(d, "signature_valid").passed


def test_require_signed_false_empty_author_denies():
    """Empty author email still denied when signature gate is off."""
    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(author_email=""), "ce-feature", pol)
    assert d.allowed is False
    assert not _check(d, "author_authorized").passed


# ---------------------------------------------------------------------------
# (d) require_signed_commits=False + forbidden branch → REJECT
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("branch", ["main", "MAIN", "master", "develop"])
def test_require_signed_false_forbidden_branch_denies(branch):
    """Branch gate still enforced when signature gate is off."""
    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(), branch, pol)
    assert d.allowed is False
    # At least one of the branch gates failed
    branch_failed = (
        not _check(d, "branch_not_forbidden").passed
        or not _check(d, "branch_in_namespace").passed
    )
    assert branch_failed


def test_require_signed_false_out_of_namespace_denies():
    """Branch-namespace gate still enforced when signature gate is off."""
    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(), "random/hack", pol)
    assert d.allowed is False
    assert not _check(d, "branch_in_namespace").passed


# ---------------------------------------------------------------------------
# (e) require_signed_commits=False + rate-limit exceeded → REJECT
# ---------------------------------------------------------------------------
def test_require_signed_false_rate_exceeded_denies():
    """Rate-limit gate still enforced when signature gate is off."""
    pol = _policy(require_signed_commits=False, max_pushes_per_window=5)
    d = evaluate(_unsigned_facts(), "ce-feature", pol, rate_state=RateState(recent_count=5))
    assert d.allowed is False
    assert not _check(d, "within_rate_limit").passed


def test_require_signed_false_under_rate_limit_allows():
    """Rate-limit under cap: still allowed when signature gate is off."""
    pol = _policy(require_signed_commits=False, max_pushes_per_window=5)
    d = evaluate(_unsigned_facts(), "ce-feature", pol, rate_state=RateState(recent_count=4))
    assert d.allowed is True


# ---------------------------------------------------------------------------
# (f) Back-compat: require_signed_commits=True (explicit) behaves identically to default
# ---------------------------------------------------------------------------
def test_require_signed_true_happy_path_signed_allows():
    """A fully signed, authorized commit still passes with require_signed_commits=True."""
    pol = _policy(require_signed_commits=True)
    d = evaluate(_signed_facts(), "ce-feature", pol)
    assert d.allowed is True
    assert _check(d, "signature_valid").passed
    assert "disabled by policy" not in _check(d, "signature_valid").detail


# ---------------------------------------------------------------------------
# (g) Config loader: require_signed_commits parsing (fail-closed default)
# ---------------------------------------------------------------------------
def _minimal_policy_raw(**over) -> dict:
    base = {
        "base_branch": "main",
        "allowed_branch_namespaces": ["ce-"],
        "authorized_logins": ["cedev4vps-coder"],
        "max_pushes_per_window": 10,
        "window_seconds": 3600,
    }
    base.update(over)
    return base


def test_config_loader_absent_key_defaults_to_true():
    """Key absent → fail-closed default True."""
    raw = _minimal_policy_raw()
    assert "require_signed_commits" not in raw
    pol = _build_policy(raw)
    assert pol.require_signed_commits is True


def test_config_loader_null_defaults_to_true():
    """Null value → fail-closed default True (only explicit boolean False opts out)."""
    pol = _build_policy(_minimal_policy_raw(require_signed_commits=None))
    assert pol.require_signed_commits is True


def test_config_loader_zero_defaults_to_true():
    """Integer 0 → fail-closed default True (only explicit boolean False opts out)."""
    pol = _build_policy(_minimal_policy_raw(require_signed_commits=0))
    assert pol.require_signed_commits is True


def test_config_loader_empty_string_defaults_to_true():
    """Empty string → fail-closed default True."""
    pol = _build_policy(_minimal_policy_raw(require_signed_commits=""))
    assert pol.require_signed_commits is True


def test_config_loader_explicit_true_stays_true():
    """Boolean True → True."""
    pol = _build_policy(_minimal_policy_raw(require_signed_commits=True))
    assert pol.require_signed_commits is True


def test_config_loader_explicit_false_opts_out():
    """Boolean False is the ONLY accepted opt-out → False."""
    pol = _build_policy(_minimal_policy_raw(require_signed_commits=False))
    assert pol.require_signed_commits is False


# ---------------------------------------------------------------------------
# (h) Decision is still a pure, serializable, secret-free value
# ---------------------------------------------------------------------------
def test_decision_to_dict_serializable_when_signature_off():
    import json

    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(), "ce-feature", pol)
    payload = d.to_dict()
    json.dumps(payload)  # must be JSON-serializable
    assert payload["allowed"] is True
    names = {c["name"] for c in payload["checks"]}
    assert "signature_valid" in names


def test_evaluate_remains_pure_no_io_when_signature_off(monkeypatch):
    """evaluate() must be ZERO I/O even when the signature gate is off."""
    import socket
    import subprocess

    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("policy.evaluate must perform ZERO I/O")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    pol = _policy(require_signed_commits=False)
    d = evaluate(_unsigned_facts(), "ce-feature", pol)
    assert d.allowed is True
