"""GitHub-native coordination config — ``configure_repo`` / ``install_required_checks`` (G-iii).

These are the two reusable, idempotent, desired-state operations the v3
orchestrator calls to make GitHub the coordination/review/merge plane for a
repository (Brief plane A; architect report §5/§7). They encode, as code, the
hardening CE owns so the user never touches it:

* ``configure_repo(repo, policy, ...)`` — bring a branch's protection floor
  to a desired ``BranchProtectionPolicy`` (require a PR + ≥1 non-author review,
  dismiss-stale, require last-push approval, require Code Owner review, required
  status checks, strict/up-to-date, linear history, ``enforce_admins`` on so no
  admin/bypass actor can merge past the gate, force-push/deletions off). It
  prefers classic branch protection and falls back to a repository Ruleset when
  GitHub rejects classic protection for repository plan/capability reasons.
* ``install_required_checks(repo, contexts, ...)`` — register status-check
  contexts as *required* (non-destructively unioned with any already present).
* ``configure_squash_only(repo, ...)`` — apply the repository merge-method
  setting that leaves squash merge as the only enabled merge method.

Why classic branch protection first: it is what ``main`` already uses and what
PR #112 merged through. The fallback exists for Free-plan private repositories,
where classic protection returns a plan/capability 403 while repository Rulesets
can still enforce the CE floor.

Authority note (architect, OD-04′): branch confinement and "cannot self-merge"
are **ruleset/branch-protection facts, not credential facts** — there is no
branch-scoped token and no separable merge permission. So this module (config),
*not* a token, is what enforces the no-self-merge guarantee. Author-cannot-
approve-own-PR is GitHub-intrinsic; ``require_code_owner_reviews`` + CODEOWNERS
pins the approver to the CE-managed reviewer identity.

Every GitHub call goes through an injectable :data:`GhRunner` (``gh api`` by
default). Operations are **plan-by-default** (``apply=False``): they read the
current state, compute the diff, and return a :class:`ConfigResult` describing
what *would* change; they mutate the live forge only when called with
``apply=True``. Tests inject a fake runner and never touch the network.
"""
from __future__ import annotations

import base64
import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from ._redact import redact_gh_stderr
from .protection_diagnostics import api_error_text, protection_floor_unenforceable

_SQUASH_ONLY = {
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
}

# A GhRunner runs a ``gh`` invocation (argv including the leading "gh") with an
# optional stdin body and returns the completed process. Mirrors the repo's
# ``GitRunner`` idiom (ce_event_runtime/fanin_runtime/integration_queue_dry_run),
# extended with ``input_text`` so a JSON body can be piped to ``gh api --input -``.
GhRunner = Callable[[Sequence[str], "str | None"], "subprocess.CompletedProcess"]


class ForgeConfigError(Exception):
    """A forge configuration call failed (e.g. ``gh api`` returned non-zero)."""

    code = "V3-FORGE-ERROR"


class ForgeConfigRefused(ForgeConfigError):
    """A forge configuration call refused on a precondition (e.g. apply-without-verify)."""

    code = "V3-FORGE-REFUSED"


# --------------------------------------------------------------------------
# Desired-state policy
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class BranchProtectionPolicy:
    """Desired-state classic branch protection for a single branch.

    Field names mirror the GitHub REST *classic* protection PUT body. The
    ``required_status_check_contexts`` are unioned with any contexts already
    present so configuring a repo never silently drops a check someone else
    registered.
    """

    required_status_check_contexts: tuple[str, ...] = ()
    strict: bool = True
    required_approving_review_count: int = 1
    dismiss_stale_reviews: bool = True
    require_code_owner_reviews: bool = True
    require_last_push_approval: bool = True
    required_linear_history: bool = True
    enforce_admins: bool = True
    required_conversation_resolution: bool = True
    allow_force_pushes: bool = False
    allow_deletions: bool = False

    def with_contexts(self, contexts: Sequence[str]) -> "BranchProtectionPolicy":
        """Return a copy whose required contexts are the sorted union with ``contexts``."""
        merged = tuple(sorted({*self.required_status_check_contexts, *contexts}))
        return replace(self, required_status_check_contexts=merged)

    def to_put_payload(self) -> dict:
        """Serialize to the classic-protection ``PUT .../protection`` request body."""
        return {
            "required_status_checks": {
                "strict": self.strict,
                "contexts": list(self.required_status_check_contexts),
            },
            "enforce_admins": self.enforce_admins,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": self.dismiss_stale_reviews,
                "require_code_owner_reviews": self.require_code_owner_reviews,
                "required_approving_review_count": self.required_approving_review_count,
                "require_last_push_approval": self.require_last_push_approval,
            },
            "restrictions": None,
            "required_linear_history": self.required_linear_history,
            "allow_force_pushes": self.allow_force_pushes,
            "allow_deletions": self.allow_deletions,
            "required_conversation_resolution": self.required_conversation_resolution,
        }

    def observed(self) -> dict:
        """The policy-relevant fields in the normalized shape :func:`_observe` returns.

        Comparing ``policy.observed()`` to ``_observe(current_protection)`` is the
        idempotency test: equal → no change needed.
        """
        return {
            "contexts": sorted(self.required_status_check_contexts),
            "strict": self.strict,
            "required_approving_review_count": self.required_approving_review_count,
            "dismiss_stale_reviews": self.dismiss_stale_reviews,
            "require_code_owner_reviews": self.require_code_owner_reviews,
            "require_last_push_approval": self.require_last_push_approval,
            "required_linear_history": self.required_linear_history,
            "enforce_admins": self.enforce_admins,
            "required_conversation_resolution": self.required_conversation_resolution,
            "allow_force_pushes": self.allow_force_pushes,
            "allow_deletions": self.allow_deletions,
        }


# CE's desired-state for its own ``main`` (the G-iii hardening). The required
# context is the single Validate job that already runs pytest AND the
# path-manifest diff-gate; ``require_code_owner_reviews`` pins the approver to
# the CE-managed reviewer identity declared in ``.github/CODEOWNERS``.
DEFAULT_MAIN_PROTECTION = BranchProtectionPolicy(
    required_status_check_contexts=("Validate governance artifacts",),
    require_code_owner_reviews=True,
)


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ConfigResult:
    """Outcome of a forge configuration operation."""

    repo: str
    branch: str
    operation: str
    changed: bool
    applied: bool
    verified: bool
    before: dict | None = None
    after: dict | None = None
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "branch": self.branch,
            "operation": self.operation,
            "changed": self.changed,
            "applied": self.applied,
            "verified": self.verified,
            "before": self.before,
            "after": self.after,
            "actions": list(self.actions),
        }


# --------------------------------------------------------------------------
# gh transport
# --------------------------------------------------------------------------
def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=60,
    )


def _gh_api(
    runner: GhRunner,
    path: str,
    *,
    method: str | None = None,
    body: dict | None = None,
) -> tuple[int, object, str]:
    """Invoke ``gh api [--method M] <path> [--input -]``.

    Returns ``(returncode, parsed_json_or_None, stderr)``. Never raises on a
    non-zero exit (the caller decides) and never raises on unparseable stdout.
    """
    argv: list[str] = ["gh", "api"]
    if method is not None:
        argv += ["--method", method]
    argv.append(path)
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _enabled(value: object) -> bool:
    """Normalize a protection field that may be a bool or a ``{"enabled": bool}`` GET wrapper."""
    if isinstance(value, dict):
        return bool(value.get("enabled", False))
    return bool(value)


def _observe(protection: dict | None) -> dict:
    """Project a classic-protection GET body into the comparable shape of ``policy.observed()``."""
    if not protection:
        return {}
    rsc = protection.get("required_status_checks") or {}
    rpr = protection.get("required_pull_request_reviews") or {}
    return {
        "contexts": sorted(rsc.get("contexts", []) or []),
        "strict": bool(rsc.get("strict", False)),
        "required_approving_review_count": int(rpr.get("required_approving_review_count", 0) or 0),
        "dismiss_stale_reviews": bool(rpr.get("dismiss_stale_reviews", False)),
        "require_code_owner_reviews": bool(rpr.get("require_code_owner_reviews", False)),
        "require_last_push_approval": bool(rpr.get("require_last_push_approval", False)),
        "required_linear_history": _enabled(protection.get("required_linear_history")),
        "enforce_admins": _enabled(protection.get("enforce_admins")),
        "required_conversation_resolution": _enabled(
            protection.get("required_conversation_resolution")
        ),
        "allow_force_pushes": _enabled(protection.get("allow_force_pushes")),
        "allow_deletions": _enabled(protection.get("allow_deletions")),
    }


def _read_protection(runner: GhRunner, repo: str, branch: str) -> dict | None:
    """GET the current classic protection, or ``None`` when the branch is unprotected (404)."""
    code, parsed, _ = _gh_api(runner, f"repos/{repo}/branches/{branch}/protection")
    if code != 0:
        return None
    return parsed if isinstance(parsed, dict) else None


def _api_error_text(parsed: object, stderr: str) -> str:
    return api_error_text(parsed, stderr)


def _classic_protection_plan_unsupported(parsed: object, stderr: str) -> bool:
    return protection_floor_unenforceable(parsed, stderr)


def _ruleset_policy_from_branch_protection(policy: BranchProtectionPolicy, *, branch: str):
    from .ruleset import CE_PROTECTION_RULESET_NAME, RulesetPolicy

    return RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        branch=branch,
        required_status_check_contexts=policy.required_status_check_contexts,
        strict_required_status_checks_policy=policy.strict,
        required_approving_review_count=max(1, policy.required_approving_review_count),
        dismiss_stale_reviews_on_push=policy.dismiss_stale_reviews,
        require_last_push_approval=policy.require_last_push_approval,
        required_review_thread_resolution=policy.required_conversation_resolution,
        bypass_actors=(),
    )


def _repo_merge_settings(parsed: dict) -> dict:
    return {key: bool(parsed.get(key, False)) for key in _SQUASH_ONLY}


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------
def install_required_checks(
    repo: str,
    contexts: Sequence[str],
    *,
    branch: str = "main",
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ConfigResult:
    """Ensure ``contexts`` are required status checks on ``branch`` (idempotent, union).

    Reads the current required contexts, computes the sorted union with
    ``contexts`` and PATCHes ``.../protection/required_status_checks`` only when
    that union differs. With ``apply=False`` (default) it reads + plans and
    mutates nothing; with ``apply=True`` it applies and re-reads to verify.
    """
    runner = gh_runner or _default_gh_runner
    code, parsed, stderr = _gh_api(
        runner, f"repos/{repo}/branches/{branch}/protection/required_status_checks"
    )
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not read required status checks for {repo}@{branch}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    current = sorted(parsed.get("contexts", []) or [])
    strict = bool(parsed.get("strict", True))
    desired = sorted({*current, *contexts})
    changed = desired != current
    before = {"contexts": current, "strict": strict}
    after = {"contexts": desired, "strict": strict}
    actions: list[str] = []

    if not changed:
        actions.append(f"required checks already satisfied: {desired}")
        return ConfigResult(
            repo=repo, branch=branch, operation="install_required_checks",
            changed=False, applied=False, verified=True, before=before, after=after,
            actions=actions,
        )
    if not apply:
        actions.append(f"PLAN: would set required contexts {current} -> {desired}")
        return ConfigResult(
            repo=repo, branch=branch, operation="install_required_checks",
            changed=True, applied=False, verified=False, before=before, after=after,
            actions=actions,
        )

    pcode, _, pstderr = _gh_api(
        runner,
        f"repos/{repo}/branches/{branch}/protection/required_status_checks",
        method="PATCH",
        body={"strict": strict, "contexts": desired},
    )
    if pcode != 0:
        raise ForgeConfigError(
            f"PATCH required status checks for {repo}@{branch} failed: "
            f"{redact_gh_stderr(pstderr) or 'unknown error'}"
        )
    actions.append(f"APPLIED: required contexts {current} -> {desired}")
    vcode, vparsed, _ = _gh_api(
        runner, f"repos/{repo}/branches/{branch}/protection/required_status_checks"
    )
    verified = (
        vcode == 0
        and isinstance(vparsed, dict)
        and sorted(vparsed.get("contexts", []) or []) == desired
    )
    return ConfigResult(
        repo=repo, branch=branch, operation="install_required_checks",
        changed=True, applied=True, verified=verified, before=before, after=after,
        actions=actions,
    )


def configure_repo(
    repo: str,
    policy: BranchProtectionPolicy = DEFAULT_MAIN_PROTECTION,
    *,
    branch: str = "main",
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ConfigResult:
    """Bring ``branch`` protection to ``policy`` (idempotent desired-state).

    Reads current protection, unions the policy's required contexts with any
    already present (non-destructive), and PUTs the full classic-protection
    body only when the policy-relevant observation differs. With ``apply=False``
    (default) it reads + plans and mutates nothing; with ``apply=True`` it
    applies and re-reads to verify the live state now matches the policy.
    """
    runner = gh_runner or _default_gh_runner
    current = _read_protection(runner, repo, branch)
    observed = _observe(current)

    # Non-destructive: keep any pre-existing required contexts.
    effective = policy.with_contexts(observed.get("contexts", []))
    desired = effective.observed()
    changed = observed != desired
    actions: list[str] = []

    if not changed:
        actions.append("protection already matches desired policy")
        return ConfigResult(
            repo=repo, branch=branch, operation="configure_repo",
            changed=False, applied=False, verified=True, before=observed, after=desired,
            actions=actions,
        )
    if not apply:
        actions.append("PLAN: protection would change to desired policy")
        actions += _describe_diff(observed, desired)
        return ConfigResult(
            repo=repo, branch=branch, operation="configure_repo",
            changed=True, applied=False, verified=False, before=observed, after=desired,
            actions=actions,
        )

    pcode, pparsed, pstderr = _gh_api(
        runner,
        f"repos/{repo}/branches/{branch}/protection",
        method="PUT",
        body=effective.to_put_payload(),
    )
    if pcode != 0:
        if _classic_protection_plan_unsupported(pparsed, pstderr):
            from .ruleset import upsert_ruleset

            ruleset_policy = _ruleset_policy_from_branch_protection(effective, branch=branch)
            actions.append(
                "classic branch protection unsupported for this repository/plan; "
                f"applying repository Ruleset fallback {ruleset_policy.name!r}"
            )
            try:
                ruleset = upsert_ruleset(
                    repo,
                    ruleset_policy,
                    apply=True,
                    gh_runner=runner,
                )
            except ForgeConfigError as exc:
                raise ForgeConfigError(
                    "classic branch protection is unsupported for this repository/plan, "
                    f"and the repository Ruleset fallback failed: {exc}"
                ) from exc
            actions.extend(ruleset.actions)
            if not ruleset.verified:
                actions.append("VERIFY MISMATCH: repository Ruleset fallback did not verify")
            return ConfigResult(
                repo=repo,
                branch=branch,
                operation="configure_repo",
                changed=ruleset.changed,
                applied=ruleset.applied,
                verified=ruleset.verified,
                before=observed,
                after={"classic_policy": desired, "ruleset": ruleset.after},
                actions=actions,
            )
        raise ForgeConfigError(
            f"PUT protection for {repo}@{branch} failed: {redact_gh_stderr(pstderr) or 'unknown error'}"
        )
    actions.append("APPLIED: protection PUT to desired policy")
    actions += _describe_diff(observed, desired)
    reread = _observe(_read_protection(runner, repo, branch))
    verified = reread == desired
    if not verified:
        actions.append(f"VERIFY MISMATCH: live={reread} desired={desired}")
    return ConfigResult(
        repo=repo, branch=branch, operation="configure_repo",
        changed=True, applied=True, verified=verified, before=observed, after=desired,
        actions=actions,
    )


def allow_auto_merge(
    repo: str,
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ConfigResult:
    """Ensure the repository-level ``allow_auto_merge`` setting is enabled."""
    runner = gh_runner or _default_gh_runner
    code, parsed, stderr = _gh_api(runner, f"repos/{repo}")
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not read repository settings for {repo}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    before = {"allow_auto_merge": bool(parsed.get("allow_auto_merge", False))}
    after = {"allow_auto_merge": True}
    actions: list[str] = []
    if before == after:
        actions.append("repo auto-merge setting already enabled")
        return ConfigResult(
            repo=repo, branch="", operation="allow_auto_merge",
            changed=False, applied=False, verified=True, before=before, after=after,
            actions=actions,
        )
    if not apply:
        actions.append("PLAN: would enable repo auto-merge setting")
        return ConfigResult(
            repo=repo, branch="", operation="allow_auto_merge",
            changed=True, applied=False, verified=False, before=before, after=after,
            actions=actions,
        )
    pcode, _pparsed, pstderr = _gh_api(
        runner, f"repos/{repo}", method="PATCH", body={"allow_auto_merge": True}
    )
    if pcode != 0:
        raise ForgeConfigError(
            f"PATCH allow_auto_merge for {repo} failed: "
            f"{redact_gh_stderr(pstderr) or 'unknown error'}"
        )
    actions.append("APPLIED: enabled repo auto-merge setting")
    vcode, vparsed, _ = _gh_api(runner, f"repos/{repo}")
    verified = (
        vcode == 0
        and isinstance(vparsed, dict)
        and bool(vparsed.get("allow_auto_merge", False)) is True
    )
    if not verified:
        actions.append(f"VERIFY MISMATCH: live={vparsed} desired={after}")
    return ConfigResult(
        repo=repo, branch="", operation="allow_auto_merge",
        changed=True, applied=True, verified=verified, before=before, after=after,
        actions=actions,
    )


def configure_squash_only(
    repo: str,
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ConfigResult:
    """Ensure squash merge is the only enabled repository merge method."""
    runner = gh_runner or _default_gh_runner
    code, parsed, stderr = _gh_api(runner, f"repos/{repo}")
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not read repository merge settings for {repo}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    before = _repo_merge_settings(parsed)
    after = dict(_SQUASH_ONLY)
    actions: list[str] = []
    if before == after:
        actions.append("repo merge settings already squash-only")
        return ConfigResult(
            repo=repo, branch="", operation="configure_squash_only",
            changed=False, applied=False, verified=True, before=before, after=after,
            actions=actions,
        )
    if not apply:
        actions.append("PLAN: would configure repo merge settings to squash-only")
        return ConfigResult(
            repo=repo, branch="", operation="configure_squash_only",
            changed=True, applied=False, verified=False, before=before, after=after,
            actions=actions,
        )
    pcode, _pparsed, pstderr = _gh_api(
        runner, f"repos/{repo}", method="PATCH", body=after
    )
    if pcode != 0:
        raise ForgeConfigError(
            f"PATCH squash-only merge settings for {repo} failed: "
            f"{redact_gh_stderr(pstderr) or 'unknown error'}"
        )
    actions.append("APPLIED: configured repo merge settings to squash-only")
    vcode, vparsed, _ = _gh_api(runner, f"repos/{repo}")
    verified = vcode == 0 and isinstance(vparsed, dict) and _repo_merge_settings(vparsed) == after
    if not verified:
        actions.append(f"VERIFY MISMATCH: live={vparsed} desired={after}")
    return ConfigResult(
        repo=repo, branch="", operation="configure_squash_only",
        changed=True, applied=True, verified=verified, before=before, after=after,
        actions=actions,
    )


def _codeowners_body(owners: Sequence[str]) -> str:
    cleaned = tuple(str(owner).strip() for owner in owners if str(owner).strip())
    if not cleaned:
        raise ForgeConfigRefused("CODEOWNERS update requires at least one owner")
    return f"* {' '.join(cleaned)}\n"


def _decode_content_file(parsed: object) -> tuple[str | None, str | None]:
    if not isinstance(parsed, dict):
        return None, None
    sha = parsed.get("sha")
    raw = str(parsed.get("content") or "")
    if not raw:
        return None, (str(sha) if sha else None)
    try:
        content = base64.b64decode(raw.encode("ascii"), validate=False).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        content = None
    return content, (str(sha) if sha else None)


def set_codeowners(
    repo: str,
    owners: Sequence[str],
    *,
    branch: str = "main",
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ConfigResult:
    """Write ``.github/CODEOWNERS`` through the Contents API (plan-by-default)."""
    desired_content = _codeowners_body(owners)
    runner = gh_runner or _default_gh_runner
    path = f"repos/{repo}/contents/.github/CODEOWNERS?ref={branch}"
    code, parsed, stderr = _gh_api(runner, path)
    current_content: str | None = None
    current_sha: str | None = None
    if code == 0:
        current_content, current_sha = _decode_content_file(parsed)
    elif "404" not in stderr and "Not Found" not in stderr:
        raise ForgeConfigError(
            f"could not read CODEOWNERS for {repo}@{branch}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    before = {"content": current_content, "sha": current_sha}
    after = {"content": desired_content}
    changed = current_content != desired_content
    actions: list[str] = []
    if not changed:
        actions.append("CODEOWNERS already matches desired owners")
        return ConfigResult(
            repo=repo, branch=branch, operation="set_codeowners",
            changed=False, applied=False, verified=True, before=before, after=after,
            actions=actions,
        )
    if not apply:
        actions.append("PLAN: would write .github/CODEOWNERS")
        return ConfigResult(
            repo=repo, branch=branch, operation="set_codeowners",
            changed=True, applied=False, verified=False, before=before, after=after,
            actions=actions,
        )
    body = {
        "message": "chore: update CODEOWNERS",
        "content": base64.b64encode(desired_content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if current_sha:
        body["sha"] = current_sha
    pcode, _pparsed, pstderr = _gh_api(
        runner, f"repos/{repo}/contents/.github/CODEOWNERS", method="PUT", body=body
    )
    if pcode != 0:
        raise ForgeConfigError(
            f"PUT CODEOWNERS for {repo}@{branch} failed: "
            f"{redact_gh_stderr(pstderr) or 'unknown error'}"
        )
    actions.append("APPLIED: wrote .github/CODEOWNERS")
    vcode, vparsed, _ = _gh_api(runner, path)
    verified_content, _ = _decode_content_file(vparsed) if vcode == 0 else (None, None)
    verified = verified_content == desired_content
    if not verified:
        actions.append("VERIFY MISMATCH: live CODEOWNERS did not match desired content")
    return ConfigResult(
        repo=repo, branch=branch, operation="set_codeowners",
        changed=True, applied=True, verified=verified, before=before, after=after,
        actions=actions,
    )


def _describe_diff(before: dict, after: dict) -> list[str]:
    """Human-readable per-field deltas between two ``observed`` dicts."""
    out: list[str] = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if b != a:
            out.append(f"  {key}: {b!r} -> {a!r}")
    return out
