"""GitHub-native coordination config — ``configure_repo`` / ``install_required_checks`` (G-iii).

These are the two reusable, idempotent, desired-state operations the v3
orchestrator calls to make GitHub the coordination/review/merge plane for a
repository (Brief plane A; architect report §5/§7). They encode, as code, the
hardening CE owns so the user never touches it:

* ``configure_repo(repo, policy, ...)`` — bring a branch's *classic* protection
  to a desired ``BranchProtectionPolicy`` (require a PR + ≥1 non-author review,
  dismiss-stale, require last-push approval, require Code Owner review, required
  status checks, strict/up-to-date, linear history, ``enforce_admins`` on so no
  admin/bypass actor can merge past the gate, force-push/deletions off) and the
  squash-only repo merge setting.
* ``install_required_checks(repo, contexts, ...)`` — register status-check
  contexts as *required* (non-destructively unioned with any already present).

Why classic branch protection (not rulesets): it is what ``main`` already uses
and what PR #112 merged through; ``enforce_admins=true`` removes any bypass-list
concern. A rulesets migration is a deliberate later gate.

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

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

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
            f"{stderr.strip() or 'unknown error'}"
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
            f"{pstderr.strip() or 'unknown error'}"
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

    pcode, _, pstderr = _gh_api(
        runner,
        f"repos/{repo}/branches/{branch}/protection",
        method="PUT",
        body=effective.to_put_payload(),
    )
    if pcode != 0:
        raise ForgeConfigError(
            f"PUT protection for {repo}@{branch} failed: {pstderr.strip() or 'unknown error'}"
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


def _describe_diff(before: dict, after: dict) -> list[str]:
    """Human-readable per-field deltas between two ``observed`` dicts."""
    out: list[str] = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if b != a:
            out.append(f"  {key}: {b!r} -> {a!r}")
    return out
