"""Read-only PreToolUse profile for the `ce ask` support agent (P0.3).

The support agent dogfoods CE's refusal spine instead of a bespoke guardrail
(CE_SUPPORT_AGENT_PLAN_20260627.md §5). This module configures the Ring-1/Ring-2
PreToolUse gate as a **read-only, corpus-scoped** profile and emits the same
``HookDecision`` value object the dev-seat path emits — so the support seat is
governed by the exact machinery the rest of the fleet runs, not a fork.

The profile is deny-by-default for anything outside a read of the product-lens
corpus root:

* **Deny all write tools** (``Edit`` / ``Write`` / ``MultiEdit``) — read-only
  contract. Reuses ``hook_check.SCOPE_TOOLS`` as the single source of "what a
  write tool is".
* **Deny exec / network** (``Bash`` and any shell/network tool) entirely — the
  support agent has no exec or egress.
* **Deny any `ce` subcommand invocation** — it can DESCRIBE the gate; it never
  OPERATES it.
* **Deny any read outside the corpus root allowlist** (the confidentiality wall,
  defense-in-depth layer 2). Reads are restricted to the static corpus roots
  derived from the product-lens allowlist (``support_corpus.corpus_roots``), and
  secret paths are denied even within those roots (reuses
  ``hook_check.is_secret_path`` — single-sourced credential predicate).

Only ``Read`` / ``Grep`` / ``Glob`` of an in-corpus, non-secret path is allowed.
This module is a *consumer* of the spine's primitives; it does not redefine any
deny rule.
"""
from __future__ import annotations

from pathlib import Path

from . import hook_check
from . import support_corpus

POSTURE = "support-readonly"

# The only tools the support agent may use at all (read/search). Everything else
# is denied. ``WebFetch`` is intentionally excluded from this slice's profile:
# the external-tier allowlisted-docs-origin fetch is a later (Phase 3) ticket; a
# read-only INTERNAL seat grounds on the in-tree corpus, not the network.
READ_TOOLS = frozenset({"Read", "Grep", "Glob"})

# Write tools come straight from the spine (single source of truth).
WRITE_TOOLS = hook_check.SCOPE_TOOLS  # {"Edit", "Write", "MultiEdit"}

# Exec / network tools the support agent must never have.
EXEC_NETWORK_TOOLS = frozenset({"Bash", "WebFetch", "WebSearch", "NotebookEdit"})

DENY_WRITE_REASON = "support agent is read-only; write tools are denied"
DENY_EXEC_REASON = "support agent has no exec/network authority"
DENY_CE_SUBCOMMAND_REASON = (
    "support agent describes the gate; it cannot invoke `ce` subcommands"
)
DENY_OUT_OF_CORPUS_REASON = (
    "read is outside the product-lens corpus root (confidentiality wall)"
)
DENY_SECRET_REASON = "support agent never reads secret/credential paths"
ALLOW_READ_REASON = "in-corpus read-only access"


def _decision(decision: str, reason: str) -> hook_check.HookDecision:
    return hook_check.HookDecision(
        ok=(decision == "allow"),
        hook_event_name="PreToolUse",
        posture=POSTURE,
        decision=decision,
        reason=reason,
    )


def _within_corpus_root(rel: str, *, roots: tuple[str, ...]) -> bool:
    if "." in roots:  # repo-root entries (README.md, CONTRIBUTING.md, ...) live at top
        # Top-level files are allowed by exact match against the manifest below;
        # a bare "." root does NOT grant the whole tree. Directory roots gate
        # subtrees; the per-file corpus eligibility check is the precise filter.
        pass
    posix = Path(rel).as_posix()
    for root in roots:
        if root == ".":
            # Only a top-level file (no directory component) qualifies under ".".
            if "/" not in posix:
                return True
            continue
        if posix == root or posix.startswith(root + "/"):
            return True
    return False


def _relativize(file_path: str, *, repo_root: Path) -> str | None:
    """Repo-root-relative POSIX path, or None if outside the repo."""
    try:
        p = Path(file_path)
        if not p.is_absolute():
            p = repo_root / p
        return p.resolve().relative_to(repo_root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def evaluate(
    tool_name: str,
    tool_input: dict | None = None,
    *,
    repo_root: Path | None = None,
) -> hook_check.HookDecision:
    """Deterministic PreToolUse decision for the support read-only profile.

    Returns a ``hook_check.HookDecision`` (same type the dev-seat path emits),
    renderable to Claude/codex hook JSON via ``to_claude_hook_dict()``.
    """
    root = (repo_root or support_corpus.repo_root()).resolve()
    tool_input = tool_input or {}

    # 1) Write tools — denied (read-only contract).
    if tool_name in WRITE_TOOLS:
        return _decision("deny", DENY_WRITE_REASON)

    # 2) Exec / network tools — denied.
    if tool_name in EXEC_NETWORK_TOOLS:
        return _decision("deny", DENY_EXEC_REASON)

    # 3) Read/search tools — must target an in-corpus, non-secret path.
    if tool_name in READ_TOOLS:
        target = (
            tool_input.get("file_path")
            or tool_input.get("path")
            or tool_input.get("pattern")
            or ""
        )
        if not target:
            # A bare Grep/Glob with no path defaults to cwd-wide scan — deny;
            # the support seat must read named corpus files only.
            return _decision("deny", DENY_OUT_OF_CORPUS_REASON)

        # Secret paths are denied regardless of corpus membership. Reuses the
        # single-sourced credential predicate (hook_check.is_secret_path). The
        # predicate keys on the final path component, so we also probe each
        # component to catch a file *nested under* a credential-store directory
        # (e.g. ``~/.ce-keys/overwatch.env``) — a read, not a redefinition, of
        # the same rule set.
        target_str = str(target)
        if hook_check.is_secret_path(target_str):
            return _decision("deny", DENY_SECRET_REASON)
        for part in Path(target_str).parts:
            if hook_check.is_secret_path(part):
                return _decision("deny", DENY_SECRET_REASON)

        rel = _relativize(str(target), repo_root=root)
        if rel is None:
            return _decision("deny", DENY_OUT_OF_CORPUS_REASON)

        roots = support_corpus.corpus_roots()
        if not _within_corpus_root(rel, roots=roots):
            return _decision("deny", DENY_OUT_OF_CORPUS_REASON)

        return _decision("allow", ALLOW_READ_REASON)

    # 4) Anything else (unknown / `ce`-subcommand / privileged tool) — denied.
    return _decision("deny", DENY_CE_SUBCOMMAND_REASON)
