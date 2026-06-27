"""Strict-TDD unit tests for the ADR-0007 egress-broker PURE policy core.

``egress_broker.policy.evaluate`` is the trusted-computing-base heart of the v0 publish
broker: given already-extracted, value-free :class:`CommitFacts` + a target branch + a
:class:`BrokerPolicy`, it returns a fail-closed :class:`Decision`. It performs ZERO I/O —
the cryptographic signature verdict (``git``'s ``%G?``), the author identity, and the
target ref are facts supplied by the (separately-tested) extraction/orchestration layers;
this module only DECIDES. Every doubt denies.

The contract under test (ADR-0007 §"verifies before transmitting"):

* signature valid — ONLY a fully-trusted good signature (``%G?`` == ``G``) passes; every
  other code (``B`` bad, ``U`` good/unknown-validity, ``X``/``Y``/``R`` expired/revoked,
  ``E`` cannot-check, ``N`` none) DENIES. This is the fail-closed core: an unverifiable
  signature is a denial, never an allow.
* author ∈ an allow-list of authorized CE identities (by exact email OR by the GitHub
  ``<id>+<login>@users.noreply.github.com`` login).
* target branch matches an allowed namespace AND is never ``main`` (nor any forbidden /
  base branch) — the forbidden check is absolute and overrides a matching namespace.
* a basic rate guard and a pluggable precondition (ratification/CI) gate, supplied as
  pure inputs so the core stays pure.

``allowed`` is the AND of every check; a single failure denies and ALL failing reasons are
recorded for the audit. These tests inject only plain values — no network, git, or crypto.
"""

import pytest

from egress_broker.policy import (
    BrokerPolicy,
    CommitFacts,
    Decision,
    Precondition,
    RateState,
    evaluate,
)

# ---------------------------------------------------------------------------
# Fixtures — a known-good policy + a known-good (allowable) commit
# ---------------------------------------------------------------------------
_GOOD_SHA = "a" * 40
_AUTHOR_EMAIL = "150906340+cedev4vps-coder@users.noreply.github.com"


def _policy(**over) -> BrokerPolicy:
    base = dict(
        base_branch="main",
        allowed_branch_namespaces=("ce-", "v3-", "feat/", "ce-egress-broker"),
        forbidden_branches=frozenset({"develop"}),
        authorized_emails=frozenset({"dev@creator-engine.example"}),
        authorized_logins=frozenset(
            {"cedev1vps-cmd", "ubuntuaws745-cmyk", "ce-dev-3", "cedev4vps-coder"}
        ),
        max_pushes_per_window=10,
        window_seconds=3600,
    )
    base.update(over)
    return BrokerPolicy(**base)


def _facts(**over) -> CommitFacts:
    base = dict(
        head_sha=_GOOD_SHA,
        signature_status="G",
        signer="cedev4vps-coder",
        author_name="ce-dev-4",
        author_email=_AUTHOR_EMAIL,
    )
    base.update(over)
    return CommitFacts(**base)


def _check(decision: Decision, name: str):
    for c in decision.checks:
        if c.name == name:
            return c
    raise AssertionError(f"no check named {name!r} in {[c.name for c in decision.checks]}")


# ---------------------------------------------------------------------------
# Happy path — every gate passes → ALLOW
# ---------------------------------------------------------------------------
def test_happy_path_allows():
    d = evaluate(_facts(), "ce-egress-broker", _policy())
    assert isinstance(d, Decision)
    assert d.allowed is True
    assert d.reasons == ()  # no failing reasons
    assert all(c.passed for c in d.checks)
    # the four ADR-0007 gates are each present as a named check
    for name in ("signature_valid", "author_authorized", "branch_not_forbidden", "branch_in_namespace"):
        assert _check(d, name).passed


def test_author_authorized_by_exact_email():
    d = evaluate(_facts(author_email="dev@creator-engine.example", signer="x"), "ce-x", _policy())
    assert d.allowed is True


# ---------------------------------------------------------------------------
# Signature gate — ONLY %G? == "G" passes; every other code denies (fail-closed)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status", ["N", "", "NONE"])
def test_unsigned_commit_denies(status):
    d = evaluate(_facts(signature_status=status), "ce-x", _policy())
    assert d.allowed is False
    assert not _check(d, "signature_valid").passed


def test_bad_signature_denies():
    d = evaluate(_facts(signature_status="B"), "ce-x", _policy())
    assert d.allowed is False
    assert not _check(d, "signature_valid").passed


@pytest.mark.parametrize("status", ["U", "X", "Y", "R", "E"])
def test_unverifiable_or_revoked_signature_denies(status):
    """``U`` (good but UNKNOWN validity) and expired/revoked/uncheckable all DENY.

    ``U`` is the load-bearing fail-closed case: a syntactically good signature whose key is
    not in the broker host's trust store is a *verification doubt*, so it must deny — never
    treat "good but untrusted" as good.
    """
    d = evaluate(_facts(signature_status=status), "ce-x", _policy())
    assert d.allowed is False
    assert not _check(d, "signature_valid").passed


def test_lowercase_g_is_not_good():
    d = evaluate(_facts(signature_status="g"), "ce-x", _policy())
    assert d.allowed is False  # exact "G" only; no case folding on the crypto verdict


# ---------------------------------------------------------------------------
# Author gate — must be on the allow-list (email or noreply-login)
# ---------------------------------------------------------------------------
def test_unauthorized_author_denies_even_with_good_signature():
    d = evaluate(_facts(author_email="9+attacker@users.noreply.github.com"), "ce-x", _policy())
    assert d.allowed is False
    assert not _check(d, "author_authorized").passed
    assert _check(d, "signature_valid").passed  # signature was fine; AUTHOR is the reason


def test_empty_author_denies():
    d = evaluate(_facts(author_email=""), "ce-x", _policy())
    assert d.allowed is False
    assert not _check(d, "author_authorized").passed


def test_author_email_match_is_case_insensitive():
    d = evaluate(_facts(author_email="DEV@Creator-Engine.Example", signer="x"), "ce-x", _policy())
    assert d.allowed is True


def test_noreply_login_must_match_exactly_not_substring():
    # "cedev4vps-coder-evil" must NOT be admitted by the "cedev4vps-coder" allow entry
    d = evaluate(
        _facts(author_email="9+cedev4vps-coder-evil@users.noreply.github.com"),
        "ce-x",
        _policy(),
    )
    assert d.allowed is False
    assert not _check(d, "author_authorized").passed


def test_noreply_lookalike_host_denies():
    # a look-alike domain must not satisfy the noreply login path
    d = evaluate(
        _facts(author_email="9+cedev4vps-coder@users.noreply.github.com.evil.com"),
        "ce-x",
        _policy(),
    )
    assert d.allowed is False


# ---------------------------------------------------------------------------
# Branch gate — never main / forbidden / base; must match an allowed namespace
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("branch", ["main", "MAIN", "develop", "master"])
def test_forbidden_or_main_branch_denies(branch):
    d = evaluate(_facts(), branch, _policy())
    assert d.allowed is False
    assert not _check(d, "branch_not_forbidden").passed


def test_base_branch_is_always_forbidden_even_if_not_listed():
    pol = _policy(base_branch="release", forbidden_branches=frozenset())
    d = evaluate(_facts(), "release", pol)
    assert d.allowed is False
    assert not _check(d, "branch_not_forbidden").passed


def test_disallowed_namespace_denies():
    d = evaluate(_facts(), "random/hack", _policy())
    assert d.allowed is False
    assert not _check(d, "branch_in_namespace").passed


def test_ce_ticket_branches_accepted_with_ce_namespace():
    """The special 'ce' namespace admits CE ticket branches with or without the dash."""
    pol = _policy(allowed_branch_namespaces=("ce", "feat/"))
    for branch in ("ce302-broker-namespace", "ce-302-broker-namespace"):
        d = evaluate(_facts(), branch, pol)
        assert _check(d, "branch_in_namespace").passed


@pytest.mark.parametrize("branch", ["central-banking", "certbot-renew", "ceasefire", "ce"])
def test_ce_namespace_denies_non_ticket_ce_prefixes(branch):
    """Regression: configured 'ce' is digit-anchored, not a bare startswith prefix."""
    pol = _policy(allowed_branch_namespaces=("ce", "feat/"))
    d = evaluate(_facts(), branch, pol)
    assert not _check(d, "branch_in_namespace").passed


def test_ceNNN_dash_branch_rejected_without_ce_namespace():
    """ceNNN- branches require the special 'ce' ticket namespace."""
    pol = _policy(allowed_branch_namespaces=("ce-", "feat/"))
    for branch in ("ce296-closebot-token-and-parser", "ce302-broker-namespace"):
        d = evaluate(_facts(), branch, pol)
        assert not _check(d, "branch_in_namespace").passed


def test_forbidden_overrides_a_matching_namespace():
    # even if a namespace prefix would match "main", the forbidden gate denies
    pol = _policy(allowed_branch_namespaces=("main", "ce-"))
    d = evaluate(_facts(), "main", pol)
    assert d.allowed is False
    assert not _check(d, "branch_not_forbidden").passed


@pytest.mark.parametrize("branch", ["", "   ", "has space", "-dashlead", "a\tb"])
def test_malformed_branch_denies(branch):
    d = evaluate(_facts(), branch, _policy())
    assert d.allowed is False


@pytest.mark.parametrize("delimiter", ["?", "&", "#", "="])
def test_branch_with_query_delimiter_denies(delimiter):
    d = evaluate(_facts(), f"ce-x{delimiter}develop", _policy())
    assert d.allowed is False
    assert not _check(d, "branch_in_namespace").passed


# ---------------------------------------------------------------------------
# Head-sha gate — a missing / malformed head can't be verified → deny
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sha", ["", "nothex", "abc", "g" * 40, "a" * 39, "a" * 65])
def test_malformed_head_sha_denies(sha):
    d = evaluate(_facts(head_sha=sha), "ce-x", _policy())
    assert d.allowed is False
    assert not _check(d, "head_sha_wellformed").passed


def test_sha256_head_allowed():
    d = evaluate(_facts(head_sha="b" * 64), "ce-x", _policy())
    assert d.allowed is True


# ---------------------------------------------------------------------------
# Rate guard — over the per-window cap denies (basic scope/rate)
# ---------------------------------------------------------------------------
def test_rate_over_cap_denies():
    d = evaluate(_facts(), "ce-x", _policy(max_pushes_per_window=3), rate_state=RateState(recent_count=3))
    assert d.allowed is False
    assert not _check(d, "within_rate_limit").passed


def test_rate_under_cap_allows():
    d = evaluate(_facts(), "ce-x", _policy(max_pushes_per_window=3), rate_state=RateState(recent_count=2))
    assert d.allowed is True


def test_rate_guard_disabled_when_cap_zero():
    d = evaluate(_facts(), "ce-x", _policy(max_pushes_per_window=0), rate_state=RateState(recent_count=999))
    assert d.allowed is True  # cap 0 = guard disabled (documented); other gates still apply


# ---------------------------------------------------------------------------
# Pluggable precondition gate — a failed ratification/CI precondition denies
# ---------------------------------------------------------------------------
def test_unsatisfied_precondition_denies():
    pre = (Precondition(name="ci_green", satisfied=False, detail="checks pending"),)
    d = evaluate(_facts(), "ce-x", _policy(), preconditions=pre)
    assert d.allowed is False
    assert not _check(d, "precondition:ci_green").passed


def test_satisfied_preconditions_allow():
    pre = (
        Precondition(name="ci_green", satisfied=True, detail="ok"),
        Precondition(name="ratified", satisfied=True, detail="ok"),
    )
    d = evaluate(_facts(), "ce-x", _policy(), preconditions=pre)
    assert d.allowed is True


def test_no_preconditions_is_not_a_denial_by_itself():
    d = evaluate(_facts(), "ce-x", _policy(), preconditions=())
    assert d.allowed is True


# ---------------------------------------------------------------------------
# Multiple failures — every failing reason is recorded (full audit), allowed=False
# ---------------------------------------------------------------------------
def test_multiple_failures_all_recorded():
    d = evaluate(
        _facts(signature_status="B", author_email="x@nope.example"),
        "main",
        _policy(),
    )
    assert d.allowed is False
    failed = {c.name for c in d.checks if not c.passed}
    assert {"signature_valid", "author_authorized", "branch_not_forbidden"} <= failed
    # reasons mirror the failing checks (non-empty, value-free strings)
    assert len(d.reasons) >= 3
    assert all(isinstance(r, str) and r for r in d.reasons)


# ---------------------------------------------------------------------------
# Decision is a pure, serializable, secret-free value
# ---------------------------------------------------------------------------
def test_decision_to_dict_is_serializable_and_secret_free():
    import json

    d = evaluate(_facts(), "ce-egress-broker", _policy())
    payload = d.to_dict()
    json.dumps(payload)  # must be JSON-serializable
    assert payload["allowed"] is True
    assert isinstance(payload["checks"], list) and payload["checks"]
    assert {"name", "passed", "detail"} <= set(payload["checks"][0])


def test_evaluate_is_pure_no_io(monkeypatch):
    import socket
    import subprocess

    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("policy.evaluate must perform ZERO I/O")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    d = evaluate(_facts(), "ce-x", _policy())
    assert d.allowed is True
