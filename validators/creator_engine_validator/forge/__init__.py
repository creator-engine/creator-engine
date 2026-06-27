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
from .approval_capability import (
    APPROVAL_WALL_ARMED,
    APPROVAL_WALL_DORMANT,
    APPROVAL_WALL_MISCONFIGURED,
    ApprovalCapabilityClaims,
    ApprovalCapabilityVerification,
    ApprovalCapabilityVerifier,
    ApprovalWallConfig,
    ApprovalWallRuntime,
    ApprovalWallState,
    approval_wall_secret_supplier_from_env,
    approval_wall_secret_supplier_from_secret_identity_backend,
    approval_wall_state_path,
    approval_wall_verifier_from_env,
    extract_approval_capability_marker,
    issue_approval_capability,
    load_approval_wall_state,
    resolve_approval_wall,
    save_approval_wall_state,
)
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
from .cred_injection_proxy import (
    ContainedDispatch,
    ContainedSeatReview,
    ContainedSeatReviewResult,
    CredentialBinding,
    CredentialProxyRefused,
    OutboundTransportRequest,
    ProxyDispatchResult,
    dispatch_with_credential_injection,
    gh_api_transport_adapter,
    submit_contained_seat_pr_review,
)
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
from .integrator_executor import (
    ExecutorAdapter,
    ExecutorPublishResult,
    ExecutorRefs,
    IntegratorExecutionResult,
    ResolutionPlan,
    execute_integrator_repair,
)
from .integrator_runner import (
    ConflictSnapshot,
    IntegratorEventOutcome,
    IntegratorExecutorUnavailable,
    IntegratorRunResult,
    IntegratorRunnerError,
    RepairWorkItem,
    RunnerResolutionPlan,
    run_once as run_integrator_once,
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
from .mutation_classifier import (
    AUTO_CLASSES,
    GESTURE_CLASSES,
    PRIVILEGED_CLASSES,
    mutation_class_for_paths,
)
from .automerge_policy import (
    AUTOMERGE_DECISION_AUTO,
    AUTOMERGE_DECISION_GESTURE,
    AutoMergeClassPolicy,
    AutoMergeDecision,
    AutoMergePolicyState,
    AutoMergePolicyStateError,
    automerge_policy_state_path,
    decide_automerge,
    load_automerge_policy_state,
    save_automerge_policy_state,
)
from .merge import MergeRefused, MergeResult, merge
from .plan_approval import ApprovalQuery, plan_approved
from .review_submit import ReviewResult, ReviewSubmitRefused, submit_review
from .transport_deputy_policy import (
    PolicyProfile,
    PolicyRule,
    Decision as TransportDecision,
    TransportRequest,
    evaluate as evaluate_transport_deputy_policy,
)
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
    "ApprovalCapabilityClaims",
    "ApprovalCapabilityVerification",
    "ApprovalCapabilityVerifier",
    "APPROVAL_WALL_ARMED",
    "APPROVAL_WALL_DORMANT",
    "APPROVAL_WALL_MISCONFIGURED",
    "ApprovalWallConfig",
    "ApprovalWallRuntime",
    "ApprovalWallState",
    "BranchProtectionPolicy",
    "CE_PROTECTION_RULESET_NAME",
    "ChangeRef",
    "ChangeStatusRefused",
    "ChecksState",
    "ConfigResult",
    "ConflictState",
    "ContainedDispatch",
    "ContainedSeatReview",
    "ContainedSeatReviewResult",
    "ControllerEscalationEvent",
    "CredentialBinding",
    "CredentialProxyRefused",
    "EscalationContext",
    "ForgeConfigError",
    "ForgeConfigRefused",
    "GhRunner",
    "ConflictSnapshot",
    "IntegratorEventOutcome",
    "IntegratorEscalationRefused",
    "IntegratorExecutorUnavailable",
    "IntegratorRunResult",
    "IntegratorRunnerError",
    "MergeRefused",
    "MergeResult",
    "OpenChangeRefused",
    "OutboundTransportRequest",
    "EvictionDetectionError",
    "ExecutorAdapter",
    "ExecutorPublishResult",
    "ExecutorRefs",
    "AUTO_CLASSES",
    "AUTOMERGE_DECISION_AUTO",
    "AUTOMERGE_DECISION_GESTURE",
    "AutoMergeClassPolicy",
    "AutoMergeDecision",
    "AutoMergeRefused",
    "AutoMergeResult",
    "AutoMergePolicyState",
    "AutoMergePolicyStateError",
    "GESTURE_CLASSES",
    "PRIVILEGED_CLASSES",
    "RepairNeededEvent",
    "RepairPollResult",
    "IntegratorExecutionResult",
    "RepairWorkItem",
    "ReviewResult",
    "ReviewSubmitRefused",
    "ResolverResult",
    "ReviewState",
    "ResolutionPlan",
    "PolicyProfile",
    "PolicyRule",
    "ProxyDispatchResult",
    "RulesetBypassActor",
    "RulesetPolicy",
    "RulesetRefused",
    "RulesetResult",
    "RunnerResolutionPlan",
    "ScopedToken",
    "TokenMintRefused",
    "TokenRequest",
    "TransportDecision",
    "TransportRequest",
    "app_jwt_gh_runner",
    "authenticated_gh_runner",
    "allow_auto_merge",
    "automerge_policy_state_path",
    "decide_automerge",
    "load_automerge_policy_state",
    "mutation_class_for_paths",
    "save_automerge_policy_state",
    "approval_wall_secret_supplier_from_env",
    "approval_wall_secret_supplier_from_secret_identity_backend",
    "approval_wall_state_path",
    "approval_wall_verifier_from_env",
    "change_conflicts",
    "checks_state",
    "configure_squash_only",
    "configure_repo",
    "delete_ruleset",
    "detect_repair_needed",
    "dispatch_with_credential_injection",
    "enable_auto_merge",
    "escalate_unresolved_results",
    "escalation_for_result",
    "evaluate_transport_deputy_policy",
    "execute_integrator_repair",
    "extract_approval_capability_marker",
    "gh_api_transport_adapter",
    "install_required_checks",
    "issue_approval_capability",
    "load_approval_wall_state",
    "merge",
    "mint_scoped_token",
    "open_change",
    "plan_approved",
    "poll_repair_needed",
    "resolve_conflict",
    "resolve_approval_wall",
    "resolve_non_overlapping_additions",
    "review_state",
    "revoke_scoped_token",
    "run_integrator_once",
    "save_approval_wall_state",
    "set_codeowners",
    "submit_review",
    "submit_contained_seat_pr_review",
    "upsert_ruleset",
    "verify_resolution",
]
