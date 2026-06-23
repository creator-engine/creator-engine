"""CE v3 forge adapter — the thin GitHub-native coordination seam (G-iii).

This sub-package is the first slice of the v3 platform's forge adapter:
the small set of *idempotent, desired-state* operations the (future, thin)
orchestrator calls once to rent coordination/review/merge to GitHub —
``configure_repo()`` (branch protection + reviewer policy) and
``install_required_checks()`` (required status-check registration). See
``docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md``.

Design invariants (deliberate, load-bearing):

* **Not a validator check.** Nothing here is ``@register``-ed; importing
  this package registers no check and leaves ``--list-checks`` byte-identical.
  The validator's check path stays offline/no-network; this adapter is the
  *only* place that talks to a live forge.
* **Network only behind an injectable runner.** All GitHub I/O goes through a
  ``GhRunner`` (``gh api`` subprocess by default) that callers inject — so
  tests run with a fake runner and perform **zero** live network calls, and
  importing the module performs no I/O.

  *Exception (ce-ops#38):* live forge access is no longer **exclusively** under
  ``forge/``. The shared work-claim runtime ``creator_engine_validator.work_claims``
  also talks to a live forge (the per-ticket work-claim issue comment), because it
  is consumed by BOTH ``ce_cli`` (v1) and ``v3_cli`` (v3) and so MUST NOT import
  ``forge.*`` (a v3 surface) under the version boundary. It deliberately mirrors
  this package's ``GhRunner`` / ``gh api`` seam with its own private copy rather
  than importing it; the same injectable-runner, zero-network-in-tests posture
  applies there.
* **Plan-by-default.** Both operations default to ``apply=False`` (read +
  diff + return the plan). A live mutation happens only when a caller passes
  ``apply=True`` with a real runner. This batch (G-iii code PR) never does.

This adapter may later be EXTRACTED into a standalone ``ce_orchestrator``
package on the architect's pre-committed trigger; until then it lives in the
installable validator package so the existing CI pytest job covers it.
"""
from __future__ import annotations

from .app_jwt_runner import app_jwt_gh_runner
from .change import ChangeRef, OpenChangeRefused, open_change
from .change_status import (
    ChangeStatusRefused,
    ChecksState,
    ConflictState,
    ReviewState,
    change_conflicts,
    checks_state,
    review_state,
)
from .eviction_detection import (
    EvictionDetectionError,
    RepairNeededEvent,
    RepairPollResult,
    detect_repair_needed,
    poll_repair_needed,
)
from .credential_runner import authenticated_gh_runner
from .deterministic_resolvers import (
    ResolverResult,
    resolve_conflict,
    resolve_non_overlapping_additions,
    verify_resolution,
)
from .integrator_escalation import (
    ControllerEscalationEvent,
    EscalationContext,
    IntegratorEscalationRefused,
    escalate_unresolved_results,
    escalation_for_result,
)
from .github_repo_config import (
    DEFAULT_MAIN_PROTECTION,
    BranchProtectionPolicy,
    ConfigResult,
    ForgeConfigError,
    ForgeConfigRefused,
    GhRunner,
    allow_auto_merge,
    configure_squash_only,
    configure_repo,
    install_required_checks,
    set_codeowners,
)
from .auto_merge import AutoMergeRefused, AutoMergeResult, enable_auto_merge
from .merge import MergeRefused, MergeResult, merge
from .plan_approval import ApprovalQuery, plan_approved
from .review_submit import ReviewResult, ReviewSubmitRefused, submit_review
from .ruleset import (
    CE_PROTECTION_RULESET_NAME,
    RulesetBypassActor,
    RulesetPolicy,
    RulesetRefused,
    RulesetResult,
    delete_ruleset,
    upsert_ruleset,
)
from .scoped_token import (
    ScopedToken,
    TokenMintRefused,
    TokenRequest,
    mint_scoped_token,
    revoke_scoped_token,
)

__all__ = [
    "DEFAULT_MAIN_PROTECTION",
    "ApprovalQuery",
    "BranchProtectionPolicy",
    "CE_PROTECTION_RULESET_NAME",
    "ChangeRef",
    "ChangeStatusRefused",
    "ChecksState",
    "ConfigResult",
    "ConflictState",
    "ControllerEscalationEvent",
    "EscalationContext",
    "ForgeConfigError",
    "ForgeConfigRefused",
    "GhRunner",
    "IntegratorEscalationRefused",
    "MergeRefused",
    "MergeResult",
    "OpenChangeRefused",
    "EvictionDetectionError",
    "AutoMergeRefused",
    "AutoMergeResult",
    "RepairNeededEvent",
    "RepairPollResult",
    "ReviewResult",
    "ReviewSubmitRefused",
    "ResolverResult",
    "ReviewState",
    "RulesetBypassActor",
    "RulesetPolicy",
    "RulesetRefused",
    "RulesetResult",
    "ScopedToken",
    "TokenMintRefused",
    "TokenRequest",
    "app_jwt_gh_runner",
    "authenticated_gh_runner",
    "allow_auto_merge",
    "change_conflicts",
    "checks_state",
    "configure_squash_only",
    "configure_repo",
    "delete_ruleset",
    "detect_repair_needed",
    "enable_auto_merge",
    "escalate_unresolved_results",
    "escalation_for_result",
    "install_required_checks",
    "merge",
    "mint_scoped_token",
    "open_change",
    "plan_approved",
    "poll_repair_needed",
    "resolve_conflict",
    "resolve_non_overlapping_additions",
    "review_state",
    "revoke_scoped_token",
    "set_codeowners",
    "submit_review",
    "upsert_ruleset",
    "verify_resolution",
]
