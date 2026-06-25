"""Unit tests for the egress-broker orchestration (verify → mint → push → PR → audit).

``egress_broker.orchestrator.courier`` is the deterministic, non-agent composition root: it
reads the seat's head-commit facts, evaluates the fail-closed policy, and — only on allow +
``apply`` — mints the seat's App token, pushes the branch, opens/updates the attributed PR, and
revokes the token, writing one audit record either way. Every network/git/crypto boundary is an
injected seam; these tests drive fakes and run ZERO live git/gh/openssl/HTTPS.

The load-bearing assertions: a denial NEVER mints/pushes (fail-closed), a dry-run (no ``apply``)
NEVER mints/pushes, the happy apply path mints→pushes→opens-PR→revokes in order, the token is
ALWAYS revoked (even if the PR step raises), and every path appends a secret-free audit record.
"""

import json

import pytest

from creator_engine_validator.forge.scoped_token import ScopedToken
from egress_broker.config import load_broker_config
from egress_broker.orchestrator import (
    ContainedSeatSelfPushRequest,
    EgressRefused,
    contained_seat_self_push,
    courier,
    open_or_update_pr,
    render_pr_body,
)
from egress_broker.policy import CommitFacts, Precondition

_GOOD_FACTS = CommitFacts(
    head_sha="a" * 40,
    signature_status="G",
    signer="cedev4vps-coder",
    author_name="ce-dev-4",
    author_email="150906340+cedev4vps-coder@users.noreply.github.com",
)


def _config(tmp_path, **policy_over):
    policy = {
        "base_branch": "main",
        "allowed_branch_namespaces": ["ce-", "ce242-", "v3-", "feat/"],
        "forbidden_branches": ["develop"],
        "authorized_emails": [],
        "authorized_logins": ["cedev4vps-coder"],
        "max_pushes_per_window": 10,
        "window_seconds": 3600,
    }
    policy.update(policy_over)
    return load_broker_config(
        {
            "repo": "creator-engine/creator-engine",
            "installation_owner": "creator-engine",
            "audit_log": str(tmp_path / "audit.jsonl"),
            "policy": policy,
            "seats": {
                "dev-4": {
                    "app_id": "4085526",
                    "app_owner": "cedev4vps-coder",
                    "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                    "installation_id": None,
                }
            },
        }
    )


class _Spy:
    """Records the ordered boundary calls so a test can assert the flow + ordering."""

    def __init__(self, *, push_raises=False):
        self.calls = []
        self.push_raises = push_raises
        self.token = ScopedToken(
            run_id="r", repo="creator-engine/creator-engine", policy_sha="a" * 64,
            secret_name="forge_egress_push_pr", permissions=(), expires_at="2026-06-20T13:00:00Z",
            token_ref="ref", value="ghs_minted_value",
        )

    def resolve_id(self, seat):
        self.calls.append(("resolve_id", seat.seat_id))
        return 555

    def mint(self, seat, installation_id):
        self.calls.append(("mint", seat.seat_id, installation_id))
        return self.token

    def push(self, token):
        self.calls.append(("push", token.value))
        if self.push_raises:
            raise RuntimeError("non-fast-forward")
        return {"pushed": True, "remote_head": "a" * 40, "local_head": "a" * 40}

    def open_pr(self, token):
        self.calls.append(("open_pr", token.value))
        return {"pr_number": 321, "created": True}

    def revoke(self, token):
        self.calls.append(("revoke", token.value))
        return True


class _ContainedSelfPushSpy:
    """ce-ops#242 fake: seat sends facts; host transport deputy sees the token."""

    sentinel = "ghs_ce242_SENTINEL_TOKEN_123456789"

    def __init__(self):
        self.calls = []
        self.trusted_child_values = []
        self.boundary_records = []
        self.simulated_seat = {
            "env": {"CE_SEAT_ID": "dev-4", "CE_BRANCH": "ce242-seat-self-push"},
            "argv": ["ce", "self-push", "--branch", "ce242-seat-self-push", "--apply"],
            "logs": [
                "self-push requested",
                "credential handled by host transport deputy",
            ],
        }
        self.token = ScopedToken(
            run_id="ce242-r",
            repo="creator-engine/creator-engine",
            policy_sha="2" * 64,
            secret_name="forge_egress_push_pr",
            permissions=(),
            expires_at="2026-06-25T13:00:00Z",
            token_ref="ce242-token-ref",
            value=self.sentinel,
        )

    def resolve_id(self, seat):
        self.calls.append(("resolve_id", seat.seat_id))
        return 242

    def mint(self, seat, installation_id):
        self.calls.append(("mint", seat.seat_id, installation_id))
        return self.token

    def push(self, token):
        self.calls.append(("push", "host-transport-deputy"))
        self.trusted_child_values.append(token.value)
        self.boundary_records.append(
            {
                "boundary": "transport_deputy",
                "argv": ["git", "-C", "<host-worktree>", "push", "origin", "ce242-seat-self-push"],
                "env": {"GH_TOKEN": "<injected-at-child-boundary>"},
                "input": None,
                "log": "host-side broker pushed branch with injected credential",
            }
        )
        return {"pushed": True, "remote_head": _GOOD_FACTS.head_sha, "local_head": _GOOD_FACTS.head_sha}

    def open_pr(self, token):
        self.calls.append(("open_pr", "host-transport-deputy"))
        self.trusted_child_values.append(token.value)
        self.boundary_records.append(
            {
                "boundary": "transport_deputy",
                "argv": ["gh", "api", "-X", "POST", "repos/creator-engine/creator-engine/pulls"],
                "env": {"GH_TOKEN": "<injected-at-child-boundary>"},
                "input": {"head": "ce242-seat-self-push", "base": "main"},
                "log": "host-side broker opened or updated PR",
            }
        )
        return {"pr_number": 242, "created": True}

    def revoke(self, token):
        self.calls.append(("revoke", "host-transport-deputy"))
        self.trusted_child_values.append(token.value)
        return True


def _courier(tmp_path, branch, facts, spy, *, apply=False, config=None, **kw):
    cfg = config or _config(tmp_path)
    return courier(
        "dev-4",
        "/seat/workspace/creator-engine",
        branch,
        config=cfg,
        apply=apply,
        read_facts_fn=lambda: facts,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
        **kw,
    )


def _self_push(tmp_path, branch, facts, spy, *, apply=False, config=None, **kw):
    cfg = config or _config(tmp_path)
    return contained_seat_self_push(
        ContainedSeatSelfPushRequest(
            seat_id="dev-4",
            repo_path="/seat/workspace/creator-engine",
            branch=branch,
        ),
        config=cfg,
        apply=apply,
        read_facts_fn=lambda: facts,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
        **kw,
    )


def _audit_lines(tmp_path):
    p = tmp_path / "audit.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _assert_sentinel_absent(sentinel, *objects):
    for obj in objects:
        rendered = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=repr)
        assert sentinel not in rendered


# ---------------------------------------------------------------------------
# ce-ops#242 contained-seat SELF-PUSH - token lives only at host transport boundary
# ---------------------------------------------------------------------------
def test_contained_seat_self_push_happy_path_is_host_brokered_and_secret_free(tmp_path):
    spy = _ContainedSelfPushSpy()

    result = _self_push(tmp_path, "ce242-seat-self-push", _GOOD_FACTS, spy, apply=True)

    assert result.allowed is True
    assert result.applied is True
    assert result.pushed is True
    assert result.pr_number == 242
    assert [c[0] for c in spy.calls] == ["resolve_id", "mint", "push", "open_pr", "revoke"]
    assert spy.trusted_child_values == [spy.sentinel, spy.sentinel, spy.sentinel]
    assert all(c[1] == "host-transport-deputy" for c in spy.calls if c[0] in {"push", "open_pr", "revoke"})

    audit_json = (tmp_path / "audit.jsonl").read_text()
    _assert_sentinel_absent(
        spy.sentinel,
        repr(result),
        result.audit_record,
        audit_json,
        spy.boundary_records,
        spy.simulated_seat,
    )


@pytest.mark.parametrize(
    ("branch", "facts"),
    [
        pytest.param("main", _GOOD_FACTS, id="denied_branch"),
        pytest.param(
            "ce242-seat-self-push",
            CommitFacts(
                head_sha="a" * 40,
                signature_status="N",
                signer="",
                author_name="ce-dev-4",
                author_email="150906340+cedev4vps-coder@users.noreply.github.com",
            ),
            id="denied_signature",
        ),
        pytest.param(
            "ce242-seat-self-push",
            CommitFacts(
                head_sha="a" * 40,
                signature_status="G",
                signer="mallory",
                author_name="mallory",
                author_email="9+mallory@users.noreply.github.com",
            ),
            id="denied_author",
        ),
    ],
)
def test_contained_seat_self_push_fail_closed_denials_never_mint_or_push(tmp_path, branch, facts):
    spy = _ContainedSelfPushSpy()

    with pytest.raises(EgressRefused):
        _self_push(tmp_path, branch, facts, spy, apply=True)

    assert spy.calls == []
    assert spy.trusted_child_values == []
    assert spy.boundary_records == []
    rec = _audit_lines(tmp_path)[-1]
    assert rec["decision"] == "deny"
    assert rec["pushed"] is False
    _assert_sentinel_absent(spy.sentinel, (tmp_path / "audit.jsonl").read_text(), spy.simulated_seat)


def test_contained_seat_self_push_dry_run_never_mints_or_pushes(tmp_path):
    spy = _ContainedSelfPushSpy()

    result = _self_push(tmp_path, "ce242-seat-self-push", _GOOD_FACTS, spy, apply=False)

    assert result.allowed is True
    assert result.applied is False
    assert result.pushed is False
    assert spy.calls == []
    assert spy.trusted_child_values == []
    assert spy.boundary_records == []
    rec = _audit_lines(tmp_path)[-1]
    assert rec["decision"] == "allow"
    assert rec["plan_only"] is True
    _assert_sentinel_absent(spy.sentinel, repr(result), rec, (tmp_path / "audit.jsonl").read_text())


def test_contained_seat_raw_git_push_remains_denied_by_governed_hook():
    from creator_engine_validator import hook_check

    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git push origin ce242-seat-self-push"},
    }
    decision = hook_check.evaluate(
        event,
        hook_check.HookContext(
            posture="governed",
            manifest_paths=("validators/tests/unit/test_egress_orchestrator.py",),
            seat_class="worker",
        ),
    )

    assert hook_check.classify_mechanics("git push origin ce242-seat-self-push") == "deploy"
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"


# ---------------------------------------------------------------------------
# Deny path — refuse, audit, NEVER mint/push (fail-closed)
# ---------------------------------------------------------------------------
def test_unsigned_commit_is_refused_and_never_mints(tmp_path):
    spy = _Spy()
    unsigned = CommitFacts(head_sha="a" * 40, signature_status="N", signer="", author_name="x",
                           author_email="150906340+cedev4vps-coder@users.noreply.github.com")
    with pytest.raises(EgressRefused) as ei:
        _courier(tmp_path, "ce-x", unsigned, spy, apply=True)
    assert spy.calls == []  # nothing minted, pushed, or opened
    rec = _audit_lines(tmp_path)[-1]
    assert rec["decision"] == "deny"
    assert rec["pushed"] is False
    assert any("signature" in r for r in rec["verified"]["reasons"])
    assert not ei.value.decision.allowed


def test_branch_main_is_refused(tmp_path):
    spy = _Spy()
    with pytest.raises(EgressRefused):
        _courier(tmp_path, "main", _GOOD_FACTS, spy, apply=True)
    assert spy.calls == []


def test_unauthorized_author_is_refused(tmp_path):
    spy = _Spy()
    bad = CommitFacts(head_sha="a" * 40, signature_status="G", signer="x", author_name="x",
                      author_email="9+attacker@users.noreply.github.com")
    with pytest.raises(EgressRefused):
        _courier(tmp_path, "ce-x", bad, spy, apply=True)
    assert spy.calls == []


def test_missing_branch_is_refused_and_audited(tmp_path):
    from egress_broker.commit_facts import CommitFactsError

    spy = _Spy()

    def boom():
        raise CommitFactsError("no such branch")

    with pytest.raises(EgressRefused):
        courier(
            "dev-4", "/seat/ws", "ce-x", config=_config(tmp_path), apply=True,
            read_facts_fn=boom, resolve_id_fn=spy.resolve_id, mint_fn=spy.mint,
            push_fn=spy.push, open_pr_fn=spy.open_pr, revoke_fn=spy.revoke,
        )
    assert spy.calls == []
    assert _audit_lines(tmp_path)[-1]["decision"] == "deny"


def test_unknown_seat_is_refused_and_audited(tmp_path):
    spy = _Spy()
    with pytest.raises(EgressRefused):
        courier(
            "dev-9", "/seat/ws", "ce-x", config=_config(tmp_path), apply=True,
            read_facts_fn=lambda: _GOOD_FACTS, resolve_id_fn=spy.resolve_id, mint_fn=spy.mint,
            push_fn=spy.push, open_pr_fn=spy.open_pr, revoke_fn=spy.revoke,
        )
    assert spy.calls == []
    assert _audit_lines(tmp_path)[-1]["decision"] == "deny"


def test_failed_precondition_is_refused(tmp_path):
    spy = _Spy()
    hook = lambda seat_id, repo, branch, facts: (Precondition("ci_green", False, "checks red"),)
    with pytest.raises(EgressRefused):
        _courier(tmp_path, "ce-x", _GOOD_FACTS, spy, apply=True, preconditions_hook=hook)
    assert spy.calls == []


# ---------------------------------------------------------------------------
# Dry-run (allowed, no apply) — verifies + audits but NEVER mints/pushes
# ---------------------------------------------------------------------------
def test_dry_run_allows_but_does_not_mint_or_push(tmp_path):
    spy = _Spy()
    result = _courier(tmp_path, "ce-egress-broker", _GOOD_FACTS, spy, apply=False)
    assert result.allowed is True
    assert result.applied is False
    assert spy.calls == []  # plan-only: no mint/push/PR
    rec = _audit_lines(tmp_path)[-1]
    assert rec["decision"] == "allow"
    assert rec["applied"] is False
    assert rec["pushed"] is False


# ---------------------------------------------------------------------------
# Happy apply path — mint → push → open PR → revoke, in order; audited
# ---------------------------------------------------------------------------
def test_apply_mints_pushes_opens_pr_and_revokes_in_order(tmp_path):
    spy = _Spy()
    result = _courier(tmp_path, "ce-egress-broker", _GOOD_FACTS, spy, apply=True)
    assert result.allowed is True and result.applied is True
    ops = [c[0] for c in spy.calls]
    assert ops == ["resolve_id", "mint", "push", "open_pr", "revoke"]
    assert result.pr_number == 321
    rec = _audit_lines(tmp_path)[-1]
    assert rec["decision"] == "allow"
    assert rec["pushed"] is True
    assert rec["applied"] is True
    assert rec["installation_id"] == 555
    assert rec["pr_number"] == 321
    assert rec["app_owner"] == "cedev4vps-coder"


def test_apply_without_injected_mint_uses_default_minter(tmp_path):
    import json

    transport_calls = []
    boundary_calls = []

    def signer(signing_input: bytes) -> bytes:
        return b"SIG::" + signing_input[:6]

    def transport(method, url, headers, body):
        transport_calls.append({"method": method, "url": url, "body": body})
        if method == "GET" and "app/installations" in url:
            return 200, json.dumps([{"id": 555, "account": {"login": "creator-engine"}}])
        if method == "POST" and url.endswith("/app/installations/555/access_tokens"):
            return 201, json.dumps({"token": "ghs_default_minted", "expires_at": "2026-06-20T13:00:00Z"})
        raise AssertionError(f"unexpected request {method} {url}")

    def push(token):
        boundary_calls.append(("push", token.value))
        return {"pushed": True, "remote_head": "a" * 40, "local_head": "a" * 40}

    def open_pr(token):
        boundary_calls.append(("open_pr", token.value))
        return {"pr_number": 321, "created": True}

    def revoke(token):
        boundary_calls.append(("revoke", token.value))
        return True

    result = courier(
        "dev-4", "/seat/workspace/creator-engine", "ce-egress-broker",
        config=_config(tmp_path), apply=True, read_facts_fn=lambda: _GOOD_FACTS,
        signer=signer, transport=transport, now=lambda: 1_700_000_000,
        push_fn=push, open_pr_fn=open_pr, revoke_fn=revoke,
    )

    assert result.allowed is True and result.applied is True
    assert result.installation_id == 555
    assert result.pr_number == 321
    assert [c["method"] for c in transport_calls] == ["GET", "POST"]
    assert transport_calls[1]["url"].endswith("/app/installations/555/access_tokens")
    assert boundary_calls == [
        ("push", "ghs_default_minted"),
        ("open_pr", "ghs_default_minted"),
        ("revoke", "ghs_default_minted"),
    ]


def test_token_is_revoked_even_if_pr_step_raises(tmp_path):
    spy = _Spy(push_raises=True)
    with pytest.raises(RuntimeError):
        _courier(tmp_path, "ce-egress-broker", _GOOD_FACTS, spy, apply=True)
    # the token must still be revoked despite the push failure (no leaked live credential)
    assert ("revoke", "ghs_minted_value") in spy.calls


def test_audit_record_is_secret_free_even_on_apply(tmp_path):
    spy = _Spy()
    _courier(tmp_path, "ce-egress-broker", _GOOD_FACTS, spy, apply=True)
    raw = (tmp_path / "audit.jsonl").read_text()
    assert "ghs_minted_value" not in raw  # the token value never reaches the audit


def test_rate_limit_blocks_after_cap(tmp_path):
    cfg = _config(tmp_path, max_pushes_per_window=1)
    spy = _Spy()
    # first apply succeeds and records a push
    _courier(tmp_path, "ce-one", _GOOD_FACTS, spy, apply=True, config=cfg)
    # second is over the cap → refused before any mint
    spy2 = _Spy()
    with pytest.raises(EgressRefused):
        _courier(tmp_path, "ce-two", _GOOD_FACTS, spy2, apply=True, config=cfg)
    assert spy2.calls == []


# ---------------------------------------------------------------------------
# PR step — idempotent open-or-update with gateway attribution in the body
# ---------------------------------------------------------------------------
def test_render_pr_body_notes_authorship_and_gateway_push():
    body = render_pr_body(seat_id="dev-4", branch="ce-x", head_sha="a" * 40)
    assert "dev-4" in body
    assert "gateway-pushed" in body.lower()
    assert "a" * 40 in body


def _gh_fake(existing=None, calls=None):
    import json

    def runner(argv, input_text=None):
        import subprocess as sp

        if calls is not None:
            calls.append({"argv": list(argv), "input": input_text})
        # GET open pulls
        if "-X" in argv and argv[argv.index("-X") + 1] == "GET":
            return sp.CompletedProcess(argv, 0, stdout=json.dumps(existing or []), stderr="")
        # POST create
        if "-X" in argv and argv[argv.index("-X") + 1] == "POST":
            return sp.CompletedProcess(argv, 0, stdout=json.dumps({"number": 777}), stderr="")
        # PATCH update
        if "-X" in argv and argv[argv.index("-X") + 1] == "PATCH":
            return sp.CompletedProcess(argv, 0, stdout=json.dumps({"number": 42}), stderr="")
        raise AssertionError(argv)

    return runner


def test_open_or_update_pr_creates_when_none_exists():
    calls = []
    out = open_or_update_pr(
        "creator-engine/creator-engine", "ce-x", "main",
        seat_id="dev-4", head_sha="a" * 40, gh_runner=_gh_fake(existing=[], calls=calls),
    )
    assert out["pr_number"] == 777
    assert out["created"] is True
    methods = [c["argv"][c["argv"].index("-X") + 1] for c in calls]
    assert "GET" in methods and "POST" in methods


def test_open_or_update_pr_encodes_lookup_query_params():
    from urllib.parse import parse_qs, urlsplit

    calls = []
    open_or_update_pr(
        "creator-engine/creator-engine", "ce-x&base=develop", "main",
        seat_id="dev-4", head_sha="a" * 40, gh_runner=_gh_fake(existing=[], calls=calls),
    )
    get_path = calls[0]["argv"][4]
    query = urlsplit(get_path).query
    params = parse_qs(query)

    assert "%26" in query
    assert params["state"] == ["open"]
    assert params["head"] == ["creator-engine:ce-x&base=develop"]
    assert params["base"] == ["main"]


def test_open_or_update_pr_updates_when_one_exists():
    calls = []
    existing = [{"number": 42, "head": {"sha": "a" * 40}}]
    out = open_or_update_pr(
        "creator-engine/creator-engine", "ce-x", "main",
        seat_id="dev-4", head_sha="a" * 40, gh_runner=_gh_fake(existing=existing, calls=calls),
    )
    assert out["pr_number"] == 42
    assert out["created"] is False
    methods = [c["argv"][c["argv"].index("-X") + 1] for c in calls]
    assert "PATCH" in methods  # idempotent refresh of the attribution body
