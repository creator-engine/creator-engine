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
from .credential_runner import authenticated_gh_runner
from .github_repo_config import (
    DEFAULT_MAIN_PROTECTION,
    BranchProtectionPolicy,
    ConfigResult,
    ForgeConfigError,
    ForgeConfigRefused,
    GhRunner,
    configure_repo,
    install_required_checks,
)
from .merge import MergeRefused, MergeResult, merge
from .plan_approval import ApprovalQuery, plan_approved
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
    "ChangeRef",
    "ChangeStatusRefused",
    "ChecksState",
    "ConfigResult",
    "ConflictState",
    "ForgeConfigError",
    "ForgeConfigRefused",
    "GhRunner",
    "MergeRefused",
    "MergeResult",
    "OpenChangeRefused",
    "ReviewState",
    "ScopedToken",
    "TokenMintRefused",
    "TokenRequest",
    "app_jwt_gh_runner",
    "authenticated_gh_runner",
    "change_conflicts",
    "checks_state",
    "configure_repo",
    "install_required_checks",
    "merge",
    "mint_scoped_token",
    "open_change",
    "plan_approved",
    "review_state",
    "revoke_scoped_token",
]
