"""Repo ruleset desired-state ops for CE's GitHub forge adapter.

The ruleset surface is plan-by-default and repo-scoped only. It manages a
named repository ruleset with pull-request review requirements and explicit
``bypass_actors`` while refusing ``bypass_mode: "always"`` before any forge
call. Auth lives in the injected ``GhRunner``.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field

from ._redact import redact_gh_stderr
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_ALLOWED_MERGE_METHODS = frozenset({"merge", "squash", "rebase"})
CE_PROTECTION_RULESET_NAME = "ce-reference-protection-floor"


class RulesetRefused(ForgeConfigRefused):
    """A repo-ruleset request was refused before any forge side effect."""

    code = "V3-FORGE-RULESET-REFUSED"


@dataclass(frozen=True)
class RulesetBypassActor:
    """One GitHub ruleset bypass actor."""

    actor_id: int
    actor_type: str = "Integration"
    bypass_mode: str = "pull_request"

    def to_payload(self) -> dict:
        if self.bypass_mode == "always":
            raise RulesetRefused('ruleset bypass_mode "always" is forbidden; use "pull_request"')
        if self.bypass_mode != "pull_request":
            raise RulesetRefused(
                f"unsupported ruleset bypass_mode {self.bypass_mode!r}; only 'pull_request' is allowed"
            )
        if self.actor_type != "Integration":
            raise RulesetRefused("P1 repo ruleset bypass actors must be GitHub App Integrations")
        if self.actor_id <= 0:
            raise RulesetRefused("ruleset bypass actor_id must be positive")
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "bypass_mode": self.bypass_mode,
        }


@dataclass(frozen=True)
class RulesetPolicy:
    """Desired-state repository ruleset policy."""

    name: str
    branch: str = "main"
    enforcement: str = "active"
    required_status_check_contexts: tuple[str, ...] = ()
    strict_required_status_checks_policy: bool = True
    required_approving_review_count: int = 1
    dismiss_stale_reviews_on_push: bool = True
    require_code_owner_review: bool = False
    require_last_push_approval: bool = True
    required_review_thread_resolution: bool = True
    allowed_merge_methods: tuple[str, ...] = ("squash",)
    bypass_actors: tuple[RulesetBypassActor, ...] = ()

    def _ref_include(self) -> str:
        branch = (self.branch or "").strip()
        if not branch:
            raise RulesetRefused("ruleset branch must be non-empty")
        return branch if branch.startswith("refs/") else f"refs/heads/{branch}"

    def to_put_payload(self) -> dict:
        """Serialize to the repository rulesets create/update body."""
        name = (self.name or "").strip()
        if not name:
            raise RulesetRefused("ruleset name must be non-empty")
        if self.required_approving_review_count < 1:
            raise RulesetRefused("ruleset requires at least one approving review")
        methods = tuple(m.lower() for m in self.allowed_merge_methods)
        unknown = sorted(set(methods) - _ALLOWED_MERGE_METHODS)
        if unknown:
            raise RulesetRefused(f"unsupported merge methods for ruleset: {unknown}")
        contexts = tuple(sorted({str(c).strip() for c in self.required_status_check_contexts}))
        if any(not c for c in contexts):
            raise RulesetRefused("ruleset required status check contexts must be non-empty")
        rules = []
        if contexts:
            rules.append(
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": self.strict_required_status_checks_policy,
                        "required_status_checks": [{"context": context} for context in contexts],
                    },
                }
            )
        rules.append(
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": self.required_approving_review_count,
                    "dismiss_stale_reviews_on_push": self.dismiss_stale_reviews_on_push,
                    "require_code_owner_review": self.require_code_owner_review,
                    "require_last_push_approval": self.require_last_push_approval,
                    "required_review_thread_resolution": self.required_review_thread_resolution,
                    "allowed_merge_methods": list(methods),
                },
            }
        )
        return {
            "name": name,
            "target": "branch",
            "enforcement": self.enforcement,
            "conditions": {
                "ref_name": {
                    "include": [self._ref_include()],
                    "exclude": [],
                },
            },
            "bypass_actors": [actor.to_payload() for actor in self.bypass_actors],
            "rules": rules,
        }


@dataclass(frozen=True)
class RulesetResult:
    """Outcome of a planned or applied repo ruleset operation."""

    repo: str
    name: str
    operation: str
    ruleset_id: int | None
    changed: bool
    applied: bool
    verified: bool
    before: dict | None = None
    after: dict | None = None
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "name": self.name,
            "operation": self.operation,
            "ruleset_id": self.ruleset_id,
            "changed": self.changed,
            "applied": self.applied,
            "verified": self.verified,
            "before": self.before,
            "after": self.after,
            "actions": list(self.actions),
        }


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - live gh
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_api(
    runner: GhRunner,
    path: str,
    *,
    method: str | None = None,
    body: dict | None = None,
) -> tuple[int, object, str]:
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


def _validate_repo(repo: str) -> None:
    if not _REPO_RE.match(repo or ""):
        raise RulesetRefused(
            f"repo {repo!r} is not in owner/name form; P1 supports repository rulesets only"
        )


def _rulesets_from_payload(parsed: object) -> list[dict]:
    if isinstance(parsed, list):
        return [r for r in parsed if isinstance(r, dict)]
    if isinstance(parsed, dict):
        for key in ("rulesets", "items"):
            value = parsed.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


def _list_rulesets(runner: GhRunner, repo: str) -> list[dict]:
    code, parsed, stderr = _gh_api(runner, f"repos/{repo}/rulesets")
    if code != 0:
        raise ForgeConfigError(
            f"could not list repo rulesets for {repo}: {redact_gh_stderr(stderr) or 'unknown error'}"
        )
    return _rulesets_from_payload(parsed)


def _find_by_name(rulesets: Sequence[dict], name: str) -> dict | None:
    for ruleset in rulesets:
        if ruleset.get("name") == name:
            return ruleset
    return None


def find_ruleset(
    repo: str,
    name: str,
    *,
    gh_runner: GhRunner | None = None,
) -> dict | None:
    """Read a named repository ruleset, returning ``None`` when absent."""
    _validate_repo(repo)
    runner = gh_runner or _default_gh_runner
    return _find_by_name(_list_rulesets(runner, repo), name)


def _project_ruleset(ruleset: dict | None) -> dict | None:
    if not ruleset:
        return None
    return {
        "name": ruleset.get("name"),
        "target": ruleset.get("target"),
        "enforcement": ruleset.get("enforcement"),
        "conditions": ruleset.get("conditions") or {},
        "bypass_actors": ruleset.get("bypass_actors") or [],
        "rules": ruleset.get("rules") or [],
    }


def _rule_by_type(ruleset: dict, rule_type: str) -> dict | None:
    for rule in ruleset.get("rules") or []:
        if isinstance(rule, dict) and rule.get("type") == rule_type:
            return rule
    return None


def _status_contexts(rule: dict | None) -> set[str]:
    if not rule:
        return set()
    params = rule.get("parameters") if isinstance(rule, dict) else None
    checks = params.get("required_status_checks") if isinstance(params, dict) else None
    if not isinstance(checks, list):
        return set()
    return {str(item.get("context")) for item in checks if isinstance(item, dict) and item.get("context")}


def ruleset_satisfies_policy(ruleset: dict | None, policy: RulesetPolicy) -> bool:
    """Return whether ``ruleset`` enforces at least ``policy``'s required floor."""
    live = _project_ruleset(ruleset)
    if not live:
        return False
    desired = policy.to_put_payload()
    if live.get("target") != "branch":
        return False
    if live.get("enforcement") != desired["enforcement"]:
        return False
    ref_name = live.get("conditions", {}).get("ref_name", {})
    if policy._ref_include() not in (ref_name.get("include") or []):
        return False
    if live.get("bypass_actors") != desired["bypass_actors"]:
        return False

    desired_checks = set(policy.required_status_check_contexts)
    if desired_checks:
        status_rule = _rule_by_type(live, "required_status_checks")
        status_params = status_rule.get("parameters", {}) if status_rule else {}
        if not desired_checks <= _status_contexts(status_rule):
            return False
        if policy.strict_required_status_checks_policy and not bool(
            status_params.get("strict_required_status_checks_policy")
        ):
            return False

    pull_rule = _rule_by_type(live, "pull_request")
    pull_params = pull_rule.get("parameters", {}) if pull_rule else {}
    if int(pull_params.get("required_approving_review_count", 0) or 0) < policy.required_approving_review_count:
        return False
    for key, required in (
        ("dismiss_stale_reviews_on_push", policy.dismiss_stale_reviews_on_push),
        ("require_code_owner_review", policy.require_code_owner_review),
        ("require_last_push_approval", policy.require_last_push_approval),
        ("required_review_thread_resolution", policy.required_review_thread_resolution),
    ):
        if required and not bool(pull_params.get(key)):
            return False
    methods = tuple(m.lower() for m in policy.allowed_merge_methods)
    if methods and set(pull_params.get("allowed_merge_methods") or []) != set(methods):
        return False
    return True


def upsert_ruleset(
    repo: str,
    policy: RulesetPolicy,
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> RulesetResult:
    """Create or update a named repository ruleset (plan-by-default)."""
    _validate_repo(repo)
    desired = policy.to_put_payload()
    runner = gh_runner or _default_gh_runner
    rulesets = _list_rulesets(runner, repo)
    existing = _find_by_name(rulesets, desired["name"])
    existing_id = int(existing["id"]) if existing and existing.get("id") is not None else None
    before = _project_ruleset(existing)
    after = _project_ruleset(desired)
    changed = before != after
    actions: list[str] = []

    if not changed:
        actions.append("repo ruleset already matches desired policy")
        return RulesetResult(
            repo=repo, name=desired["name"], operation="upsert_ruleset",
            ruleset_id=existing_id, changed=False, applied=False, verified=True,
            before=before, after=after, actions=actions,
        )
    if not apply:
        verb = "update" if existing_id is not None else "create"
        actions.append(f"PLAN: would {verb} repo ruleset {desired['name']!r}")
        return RulesetResult(
            repo=repo, name=desired["name"], operation="upsert_ruleset",
            ruleset_id=existing_id, changed=True, applied=False, verified=False,
            before=before, after=after, actions=actions,
        )

    if existing_id is None:
        code, parsed, stderr = _gh_api(
            runner, f"repos/{repo}/rulesets", method="POST", body=desired
        )
        action = "created"
    else:
        code, parsed, stderr = _gh_api(
            runner, f"repos/{repo}/rulesets/{existing_id}", method="PUT", body=desired
        )
        action = "updated"
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not {action[:-1]} repo ruleset {desired['name']!r} for {repo}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    new_id = int(parsed["id"]) if parsed.get("id") is not None else existing_id
    actions.append(f"APPLIED: {action} repo ruleset {desired['name']!r}")
    reread = _find_by_name(_list_rulesets(runner, repo), desired["name"])
    verified = _project_ruleset(reread) == after
    if not verified:
        actions.append(f"VERIFY MISMATCH: live={_project_ruleset(reread)} desired={after}")
    return RulesetResult(
        repo=repo, name=desired["name"], operation="upsert_ruleset",
        ruleset_id=new_id, changed=True, applied=True, verified=verified,
        before=before, after=after, actions=actions,
    )


def delete_ruleset(
    repo: str,
    name: str,
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> RulesetResult:
    """Delete a named repository ruleset when present (plan-by-default)."""
    _validate_repo(repo)
    if not (name or "").strip():
        raise RulesetRefused("ruleset name must be non-empty")
    runner = gh_runner or _default_gh_runner
    existing = _find_by_name(_list_rulesets(runner, repo), name)
    existing_id = int(existing["id"]) if existing and existing.get("id") is not None else None
    before = _project_ruleset(existing)
    actions: list[str] = []

    if existing_id is None:
        actions.append("repo ruleset already absent")
        return RulesetResult(
            repo=repo, name=name, operation="delete_ruleset", ruleset_id=None,
            changed=False, applied=False, verified=True, before=None, after=None,
            actions=actions,
        )
    if not apply:
        actions.append(f"PLAN: would delete repo ruleset {name!r}")
        return RulesetResult(
            repo=repo, name=name, operation="delete_ruleset", ruleset_id=existing_id,
            changed=True, applied=False, verified=False, before=before, after=None,
            actions=actions,
        )

    code, _parsed, stderr = _gh_api(
        runner, f"repos/{repo}/rulesets/{existing_id}", method="DELETE"
    )
    if code != 0:
        raise ForgeConfigError(
            f"could not delete repo ruleset {name!r} for {repo}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    reread = _find_by_name(_list_rulesets(runner, repo), name)
    verified = reread is None
    actions.append(f"APPLIED: deleted repo ruleset {name!r}")
    if not verified:
        actions.append(f"VERIFY MISMATCH: live ruleset still exists for {name!r}")
    return RulesetResult(
        repo=repo, name=name, operation="delete_ruleset", ruleset_id=existing_id,
        changed=True, applied=True, verified=verified, before=before, after=None,
        actions=actions,
    )
