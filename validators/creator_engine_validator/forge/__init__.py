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
from .plan_approval import ApprovalQuery, plan_approved

__all__ = [
    "DEFAULT_MAIN_PROTECTION",
    "ApprovalQuery",
    "BranchProtectionPolicy",
    "ConfigResult",
    "ForgeConfigError",
    "ForgeConfigRefused",
    "GhRunner",
    "configure_repo",
    "install_required_checks",
    "plan_approved",
]
