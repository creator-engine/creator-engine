"""The egress-broker orchestration root — deterministic verify → mint → push → PR → audit.

:func:`courier` is the non-agent composition the ADR-0007 v0 broker runs end to end. Given
``{seat_id, repo_path, branch}`` + a loaded :class:`~egress_broker.config.BrokerConfig`, it:

1. resolves the seat's App config (fail-closed on an unknown seat);
2. reads the head-commit facts host-side (``commit_facts``);
3. computes the rate-guard input from the audit log, runs the pluggable ratification/CI
   precondition hook, and evaluates the PURE fail-closed policy core;
4. on **deny** → writes a deny audit and raises :class:`EgressRefused` (the CLI exits non-zero)
   — NEVER minting or pushing;
5. on **allow + apply** → mints the seat's least-privilege App installation token, pushes the
   branch (never force; ``forge.change_push``), opens/updates the attributed PR, and revokes
   the token in a ``finally`` (so no live credential ever lingers), writing an allow audit;
6. on **allow without apply** → a dry-run that audits the plan but mints/pushes nothing (the
   safe default).

Every network/git/crypto boundary is an injected seam (defaults compose the real, frozen forge
primitives); tests drive fakes and run ZERO live git/gh/openssl/HTTPS. The minted token VALUE
lives only in the child push/PR env (the ``credential_runner`` pattern) and the in-memory
``ScopedToken`` — never the argv, a log, the returned objects, or the audit (the audit's
secret-free guard enforces this structurally).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlencode

from creator_engine_validator.checks.path_manifest_fidelity import branch_slug
from creator_engine_validator.forge._redact import redact_gh_stderr
from creator_engine_validator.forge.change_push import PushRefused
from creator_engine_validator.forge.credential_runner import authenticated_gh_runner
from creator_engine_validator.forge.scoped_token import ScopedToken, revoke_scoped_token
from creator_engine_validator.pr_preflight import DECLARED_WORK_CLASS_PATTERN, WORK_CLASSES
from creator_engine_validator.work_sizing import normalize_work_class
from egress_broker.audit import append_audit, count_recent_pushes
from egress_broker.commit_facts import CommitFactsError, read_commit_facts
from egress_broker.config import BrokerConfig, BrokerConfigError, SeatAppConfig
from egress_broker.minter import mint_egress_token, resolve_installation_id
from egress_broker.policy import CommitFacts, Decision, Precondition, RateState, evaluate

#: The EXACT least-privilege grant an egress push+PR token requests — mirrors the v3 PR-token
#: ceiling (``v3_forge_join.PR_TOKEN_*``): ``contents:write`` (push the branch) is the lone
#: escalation-gated grant, made explicit here; ``pull_requests:write`` is a Tier-3 baseline.
PUSH_PR_PERMISSIONS = {"contents": "write", "pull_requests": "write"}
PUSH_PR_ESCALATION = (("contents", "write"),)
PUSH_PR_TTL_SECONDS = 900
PUSH_PR_SECRET_NAME = "forge_egress_push_pr"

#: The pluggable ratification/CI precondition hook: ``(seat_id, repo, branch, facts) -> tuple``.
#: The default supplies NO preconditions (the broker is gated on signature/author/branch/rate);
#: the controller wires a real hook (CI-green / ratification-record) as the gateway matures.
PreconditionHook = Callable[[str, str, str, CommitFacts], tuple[Precondition, ...]]


def _no_preconditions(seat_id: str, repo: str, branch: str, facts: CommitFacts) -> tuple[Precondition, ...]:
    return ()


class EgressRefused(Exception):
    """A fail-closed refusal to courier — carries the :class:`Decision` and the audit record."""

    def __init__(self, message: str, *, decision: Decision | None = None, audit_record: dict | None = None):
        super().__init__(message)
        self.decision = decision
        self.audit_record = audit_record or {}


@dataclass(frozen=True)
class BrokerResult:
    """The outcome of a courier run — secret-free, JSON-serializable."""

    seat_id: str
    branch: str
    head_sha: str
    allowed: bool
    applied: bool
    pushed: bool
    pr_number: int | None
    installation_id: int | None
    decision: Decision
    audit_record: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContainedSeatSelfPushRequest:
    """Value-free facts a contained seat may submit for host-side SELF-PUSH.

    The request carries only identity and branch facts. The contained seat does not provide,
    receive, or influence the push credential; all verification, mint, push, PR, revoke, and
    audit work remains in the host-side courier path.
    """

    seat_id: str
    repo_path: str
    branch: str


def contained_seat_self_push(
    request: ContainedSeatSelfPushRequest,
    *,
    config: BrokerConfig,
    apply: bool = False,
    **courier_options,
) -> BrokerResult:
    """Facade for ce-ops#242 contained-seat SELF-PUSH over :func:`courier`.

    ``apply=False`` preserves courier's safe default: verify and audit only, with no mint,
    push, PR, or revocation path. Any extra options are host-owned injected seams used by
    operators or tests; they are not data supplied by the contained seat.
    """
    return courier(
        request.seat_id,
        request.repo_path,
        request.branch,
        config=config,
        apply=apply,
        **courier_options,
    )


# ---------------------------------------------------------------------------
# The PR step — idempotent open-or-update carrying the gateway attribution
# ---------------------------------------------------------------------------
def discover_declared_work_class(repo_path: str, branch: str) -> str:
    """Resolve the PR's declared work class from its per-branch carrier, fail-closed."""
    carrier_path = Path(repo_path) / ".ce" / "pr-manifests" / f"{branch_slug(branch)}.md"
    try:
        carrier_text = carrier_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EgressRefused(
            f"declared work class is required; no readable PR carrier at {carrier_path}"
        ) from exc

    matches = DECLARED_WORK_CLASS_PATTERN.findall(carrier_text)
    if len(matches) != 1:
        raise EgressRefused(
            f"declared work class is required; expected exactly one declaration in "
            f"{carrier_path}, found {len(matches)}"
        )

    try:
        return normalize_work_class(matches[0])
    except ValueError:
        raise EgressRefused(
            f"declared work class {matches[0]!r} in {carrier_path} is not one of "
            f"{', '.join(WORK_CLASSES)} (legacy aliases: tiny, story, feature, epic)"
        ) from None


def render_pr_body(*, seat_id: str, branch: str, head_sha: str, declared_work_class: str) -> str:
    """The PR body noting signed authorship + that the gateway (not the agent) pushed.

    ADR-0007: "Authorship travels with the signed commit (``ce-dev-N`` authored, Verified ·
    gateway pushed)." This is the human/audit mirror of that anchor; the verified-author fact is
    the commit signature itself.
    """
    declared_work_class = normalize_work_class(declared_work_class)
    return (
        f"Authored by `{seat_id}`, gateway-pushed (ADR-0007 egress broker — deterministic v0).\n\n"
        f"The contained seat `{seat_id}` authored and **signed** this commit locally; the "
        f"non-agent egress broker verified the signature + policy and pushed it. The author "
        f"identity travels with the signed commit; the broker is the transport, not the author.\n\n"
        f"- **Declared work class:** {declared_work_class}\n"
        f"- head branch: `{branch}`\n"
        f"- signed head: `{head_sha}`\n"
    )


def _gh_api(
    runner, method: str, path: str, body: dict | None = None
) -> tuple[int, object, str]:
    """``gh api -X <METHOD> <path>`` (JSON body via ``--input -``) — the local forge idiom."""
    argv = ["gh", "api", "-X", method, path]
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    parsed: object = None
    out = (getattr(proc, "stdout", "") or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return getattr(proc, "returncode", 1), parsed, getattr(proc, "stderr", "") or ""


def open_or_update_pr(
    repo: str,
    branch: str,
    base: str,
    *,
    seat_id: str,
    head_sha: str,
    declared_work_class: str,
    gh_runner,
) -> dict:
    """Open exactly one PR for ``branch`` -> ``base`` (or refresh the existing one's body).

    Idempotent "push = claim": GETs the open PR for the head; if none exists POSTs one with the
    gateway-attribution body; if one exists PATCHes its body to refresh the attribution. Returns
    a secret-free ``{pr_number, created}`` dict. Auth lives only in the injected ``gh_runner``'s
    child env. Raises on a transport failure (redacted).
    """
    owner = repo.split("/", 1)[0]
    body_text = render_pr_body(
        seat_id=seat_id,
        branch=branch,
        head_sha=head_sha,
        declared_work_class=declared_work_class,
    )
    query = urlencode((("state", "open"), ("head", f"{owner}:{branch}"), ("base", base)))

    code, parsed, stderr = _gh_api(
        gh_runner, "GET", f"repos/{repo}/pulls?{query}"
    )
    if code != 0:
        raise RuntimeError(
            f"could not read open pulls for {repo} {owner}:{branch}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    existing = parsed[0] if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) else None

    if existing is not None:
        number = existing.get("number")
        code, _p, stderr = _gh_api(
            gh_runner, "PATCH", f"repos/{repo}/pulls/{number}", {"body": body_text}
        )
        if code != 0:
            raise RuntimeError(
                f"could not update PR #{number} for {repo}: {redact_gh_stderr(stderr) or 'unknown error'}"
            )
        return {"pr_number": number, "created": False}

    code, parsed, stderr = _gh_api(
        gh_runner,
        "POST",
        f"repos/{repo}/pulls",
        {"title": f"[ce-egress] {branch} -> {base} (authored by {seat_id})", "head": branch, "base": base, "body": body_text},
    )
    if code != 0 or not isinstance(parsed, dict) or not parsed.get("number"):
        raise RuntimeError(
            f"could not open PR for {repo} {branch} -> {base}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    return {"pr_number": parsed.get("number"), "created": True}


# ---------------------------------------------------------------------------
# Helpers — policy binding sha + the audit record assembly
# ---------------------------------------------------------------------------
def policy_binding_sha(config: BrokerConfig, *, repo: str | None = None) -> str:
    """A deterministic 64-hex digest binding a mint to the policy in force (the mint's policy_sha)."""
    body = {
        "repo": repo or config.repo,
        "base_branch": config.policy.base_branch,
        "namespaces": sorted(config.policy.allowed_branch_namespaces),
        "forbidden": sorted(config.policy.forbidden_branches),
        "emails": sorted(config.policy.authorized_emails),
        "logins": sorted(config.policy.authorized_logins),
        "max_pushes_per_window": config.policy.max_pushes_per_window,
        "window_seconds": config.policy.window_seconds,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _base_record(
    seat_id: str,
    config: BrokerConfig,
    branch: str,
    facts: CommitFacts,
    app_owner: str,
    repo: str,
) -> dict:
    return {
        "seat_id": seat_id,
        "repo": repo,
        "branch": branch,
        "base": config.policy.base_branch,
        "head_sha": facts.head_sha,
        "author_name": facts.author_name,
        "author_email": facts.author_email,
        "signer": facts.signer,
        "signature_status": facts.signature_status,
        "app_owner": app_owner,
    }


def courier(
    seat_id: str,
    repo_path: str,
    branch: str,
    *,
    config: BrokerConfig,
    signer=None,
    transport=None,
    git_spawn=None,
    gh_spawn=None,
    now: Callable[[], float] | None = None,
    audit_now=None,
    apply: bool = False,
    declared_work_class: str | None = None,
    preconditions_hook: PreconditionHook | None = None,
    # Boundary injection — defaults compose the real forge; tests pass fakes.
    read_facts_fn: Callable[[], CommitFacts] | None = None,
    resolve_id_fn: Callable[[SeatAppConfig], int] | None = None,
    mint_fn: Callable[[SeatAppConfig, int], ScopedToken] | None = None,
    push_fn: Callable[[ScopedToken], dict] | None = None,
    open_pr_fn: Callable[[ScopedToken], dict] | None = None,
    revoke_fn: Callable[[ScopedToken], bool] | None = None,
) -> BrokerResult:
    """Verify → (on allow+apply) mint → push → open/update PR → revoke; audit every path.

    Fail-closed: any verification doubt denies (audit + :class:`EgressRefused`, no mint/push).
    ``apply=False`` (default) is a dry-run: it verifies and audits the plan but mints/pushes
    nothing. The minted token is always revoked (``finally``) even if the push/PR step raises.
    """
    audit_log = config.audit_log or str((repo_path and "") or "egress-audit.jsonl")
    hook = preconditions_hook or _no_preconditions

    # 1. resolve the seat (unknown seat = misconfig → deny + audit).
    try:
        seat = config.seat(seat_id)
    except BrokerConfigError as exc:
        rec = append_audit(
            audit_log,
            {"seat_id": seat_id, "repo": config.repo, "branch": branch, "decision": "deny",
             "applied": False, "pushed": False, "verified": {"reasons": [str(exc)]}},
            now=audit_now,
        )
        raise EgressRefused(str(exc), audit_record=rec) from exc

    app_owner = seat.app_owner
    seat_repo = seat.repo

    # 2. read the seat's head-commit facts host-side (absent branch = deny + audit).
    reader = read_facts_fn or (lambda: read_commit_facts(repo_path, branch, spawn=git_spawn))
    try:
        facts = reader()
    except CommitFactsError as exc:
        rec = append_audit(
            audit_log,
            {**_base_record(
                seat_id,
                config,
                branch,
                CommitFacts("", "", "", "", ""),
                app_owner,
                seat_repo,
            ),
             "decision": "deny", "applied": False, "pushed": False,
             "verified": {"reasons": [str(exc)]}},
            now=audit_now,
        )
        raise EgressRefused(str(exc), audit_record=rec) from exc

    # 3. rate-guard input + pluggable preconditions, then the PURE policy decision.
    recent = count_recent_pushes(audit_log, seat_id, window_seconds=config.policy.window_seconds, now=audit_now)
    preconditions = tuple(hook(seat_id, seat_repo, branch, facts))
    decision = evaluate(
        facts, branch, config.policy, rate_state=RateState(recent), preconditions=preconditions
    )

    base = _base_record(seat_id, config, branch, facts, app_owner, seat_repo)
    base["verified"] = decision.to_dict()

    # 4. deny → audit + refuse, never minting/pushing.
    if not decision.allowed:
        rec = append_audit(audit_log, {**base, "decision": "deny", "applied": False, "pushed": False}, now=audit_now)
        raise EgressRefused(
            f"egress refused for seat {seat_id} on {branch}: {'; '.join(decision.reasons)}",
            decision=decision, audit_record=rec,
        )

    # 5. allow without apply → dry-run plan (audit, no mint/push).
    if not apply:
        rec = append_audit(
            audit_log,
            {**base, "decision": "allow", "applied": False, "pushed": False, "plan_only": True},
            now=audit_now,
        )
        return BrokerResult(
            seat_id=seat_id, branch=branch, head_sha=facts.head_sha, allowed=True, applied=False,
            pushed=False, pr_number=None, installation_id=None, decision=decision, audit_record=rec,
        )

    try:
        resolved_declared_work_class = (
            normalize_work_class(declared_work_class)
            if declared_work_class is not None
            else discover_declared_work_class(repo_path, branch)
        )
    except (EgressRefused, ValueError) as exc:
        rec = append_audit(
            audit_log,
            {**base, "decision": "deny", "applied": False, "pushed": False,
             "transport_refusal": str(exc)},
            now=audit_now,
        )
        raise EgressRefused(str(exc), decision=decision, audit_record=rec) from exc
    if resolved_declared_work_class not in WORK_CLASSES:
        reason = (
            f"declared work class {resolved_declared_work_class!r} is not one of "
            f"{', '.join(WORK_CLASSES)} (legacy aliases: tiny, story, feature, epic)"
        )
        rec = append_audit(
            audit_log,
            {**base, "decision": "deny", "applied": False, "pushed": False,
             "transport_refusal": reason},
            now=audit_now,
        )
        raise EgressRefused(reason, decision=decision, audit_record=rec)

    # 6. allow + apply → mint → push → PR → revoke (token always revoked in finally).
    _resolve = resolve_id_fn or (
        lambda s: resolve_installation_id(
            s, installation_owner=config.installation_owner, signer=signer, transport=transport, now=now
        )
    )
    run_id = f"egress-{seat_id}-{facts.head_sha[:12]}"
    policy_sha = policy_binding_sha(config, repo=seat_repo)

    def _default_mint(s: SeatAppConfig, iid: int) -> ScopedToken:
        return mint_egress_token(
            replace(s, installation_id=iid),
            repo=seat_repo,
            installation_owner=config.installation_owner,
            signer=signer,
            run_id=run_id, policy_sha=policy_sha, permissions=PUSH_PR_PERMISSIONS,
            escalation_authority=PUSH_PR_ESCALATION, ttl_seconds=PUSH_PR_TTL_SECONDS,
            secret_name=PUSH_PR_SECRET_NAME, transport=transport, now=now,
        )

    _mint = mint_fn or _default_mint
    _push = push_fn or (lambda token: _default_push(seat_repo, branch, repo_path, token, git_spawn))
    _open_pr = open_pr_fn or (
        lambda token: open_or_update_pr(
            seat_repo, branch, config.policy.base_branch, seat_id=seat_id, head_sha=facts.head_sha,
            declared_work_class=resolved_declared_work_class,
            gh_runner=authenticated_gh_runner(token, spawn=gh_spawn) if gh_spawn else authenticated_gh_runner(token),
        )
    )
    _revoke = revoke_fn or (
        lambda token: revoke_scoped_token(
            token, gh_runner=authenticated_gh_runner(token, spawn=gh_spawn) if gh_spawn else authenticated_gh_runner(token)
        )
    )

    installation_id = _resolve(seat)
    token = _mint(seat, installation_id)
    if not getattr(token, "value", ""):
        rec = append_audit(
            audit_log,
            {
                **base,
                "decision": "deny",
                "applied": False,
                "pushed": False,
                "transport_refusal": "mint returned no usable credential; refusing ambient-auth fallback",
                "installation_id": installation_id,
            },
            now=audit_now,
        )
        raise EgressRefused(
            "egress mint returned no usable credential; refusing to invoke push/PR transports "
            "(a credential-less child could fall back to ambient auth)",
            decision=decision,
            audit_record=rec,
        )
    pushed = False
    pr_number: int | None = None
    try:
        push_result = _push(token)
        pushed = bool(push_result.get("pushed", True)) if isinstance(push_result, dict) else True
        pr_result = _open_pr(token)
        pr_number = pr_result.get("pr_number") if isinstance(pr_result, dict) else None
    except PushRefused as exc:
        rec = append_audit(
            audit_log,
            {
                **base,
                "decision": "deny",
                "applied": False,
                "pushed": False,
                "installation_id": installation_id,
                "transport_refusal": str(exc),
            },
            now=audit_now,
        )
        raise EgressRefused(str(exc), decision=decision, audit_record=rec) from exc
    finally:
        # Defense-in-depth: release the credential the instant we're done — even on failure.
        try:
            _revoke(token)
        except Exception:  # pragma: no cover - revoke is best-effort cleanup; never mask the real error
            pass

    rec = append_audit(
        audit_log,
        {**base, "decision": "allow", "applied": True, "pushed": pushed,
         "installation_id": installation_id, "pr_number": pr_number},
        now=audit_now,
    )
    return BrokerResult(
        seat_id=seat_id, branch=branch, head_sha=facts.head_sha, allowed=True, applied=True,
        pushed=pushed, pr_number=pr_number, installation_id=installation_id, decision=decision,
        audit_record=rec,
    )


def _default_push(repo: str, branch: str, repo_path: str, token: ScopedToken, git_spawn) -> dict:
    """Default push leg — the frozen ``forge.change_push`` (never force, fast-forward only)."""
    from creator_engine_validator.forge.change_push import push_change

    result = push_change(repo, branch, source_dir=repo_path, token=token, apply=True, spawn=git_spawn)
    return result.to_dict()
