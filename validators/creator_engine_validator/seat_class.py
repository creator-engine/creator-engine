"""Pure foreman-delegation seat-class classifier.

This module is the Slice 1 deterministic spine only: no hook wiring, no worker
spawn, no subprocess, no filesystem, no clock, no network. It classifies the
action-type boundary and emits a pure deny reason a later hard gate can reuse.
"""

from __future__ import annotations

import shlex
from collections.abc import Mapping
from typing import Any, Final

from .checks.mutation_class import BASELINE_NAMES, BASELINE_NAMES_SET, RESERVED_RESTRICTED

WORK_CLASSES: Final[frozenset[str]] = frozenset({"coordination", "implementation", "restricted"})
SEAT_CLASSES: Final[frozenset[str]] = frozenset({"foreman", "worker"})
BASELINE_MUTATION_CLASSES: Final[tuple[str, ...]] = BASELINE_NAMES
DEFAULT_DELEGATION_REQUIRED_MUTATION_CLASSES: Final[frozenset[str]] = frozenset(
    {"code", "schema", "deploy", "governance", "identity", "security"}
)

_COORDINATION_TOOLS: Final[frozenset[str]] = frozenset({"read", "grep", "glob"})
_MUTATING_TOOLS: Final[frozenset[str]] = frozenset({"edit", "write", "multiedit"})
_COORDINATION_GIT_SUBCOMMANDS: Final[frozenset[str]] = frozenset({"status", "log", "diff", "show"})
_IMPLEMENTATION_MARKERS: Final[frozenset[str]] = frozenset(
    {
        "pytest",
        "tox",
        "build",
        "test",
        "codegen",
        "generate",
        "generated",
    }
)


def resolve_seat_class(raw: str | None, *, default: str = "foreman") -> str:
    """Resolve a launch-pinned seat class, failing closed to ``foreman``."""
    del default  # API compatibility only; absence/unknown always fail closed.
    candidate = str(raw or "").strip().lower()
    if candidate in SEAT_CLASSES:
        return candidate
    return "foreman"


def _tokens(command: str | None) -> tuple[str, ...]:
    if not command:
        return ()
    try:
        return tuple(shlex.split(str(command)))
    except ValueError:
        return ()


def _git_subcommand(tokens: tuple[str, ...]) -> str | None:
    if not tokens or tokens[0] != "git":
        return None
    idx = 1
    while idx < len(tokens):
        token = tokens[idx]
        if token == "-C" and idx + 1 < len(tokens):
            idx += 2
            continue
        if token == "-c" and idx + 1 < len(tokens):
            idx += 2
            continue
        if token.startswith("-"):
            idx += 1
            continue
        return token
    return None


def _is_coordination_command(tokens: tuple[str, ...]) -> bool:
    if not tokens:
        return False
    git_subcommand = _git_subcommand(tokens)
    if git_subcommand in _COORDINATION_GIT_SUBCOMMANDS:
        return True
    if len(tokens) >= 3 and tokens[0] == "gh" and tokens[1] in {"issue", "pr"} and tokens[2] == "view":
        return True
    if len(tokens) >= 3 and tokens[0] == "ce" and tokens[1] == "lane" and tokens[2] == "launch":
        return True
    if len(tokens) >= 2 and tokens[0] == "ce" and tokens[1] in {"launch", "hud"}:
        return True
    return False


def _is_restricted_command(tokens: tuple[str, ...]) -> bool:
    return bool(set(tokens) & RESERVED_RESTRICTED)


def _is_implementation_command(tokens: tuple[str, ...]) -> bool:
    lowered = {token.lower() for token in tokens}
    if lowered & _IMPLEMENTATION_MARKERS:
        return True
    if len(tokens) >= 3 and tokens[0] == "python" and tokens[1] == "-m" and tokens[2] == "pytest":
        return True
    if len(tokens) >= 2 and tokens[0] in {"make", "npm", "pnpm", "yarn", "cargo", "go"}:
        return True
    return False


def _coordination_path_match(command: str | None, prefixes: tuple[str, ...]) -> bool:
    target = str(command or "").strip()
    if not target:
        return False
    target = target.removeprefix("./")
    for raw in prefixes:
        prefix = str(raw).strip().removeprefix("./")
        if not prefix:
            continue
        if prefix.endswith("/"):
            if target.startswith(prefix):
                return True
        elif target == prefix or target.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def classify_work_class(
    tool: str,
    command: str | None,
    mutation_class: str | None,
    *,
    coordination_path_prefixes=(),
) -> str:
    """Classify one tool/action into coordination, implementation, or restricted.

    The primary metric is action-type x irreversibility, not line count. Unknown
    or ambiguous actions fail closed to ``implementation``.
    """
    del mutation_class  # The work-class boundary is action-type; risk is used by the verdict.
    tool_name = str(tool or "").strip().lower()
    if tool_name in _COORDINATION_TOOLS:
        return "coordination"

    prefixes = tuple(str(prefix) for prefix in (coordination_path_prefixes or ()))
    if tool_name in _MUTATING_TOOLS:
        if _coordination_path_match(command, prefixes):
            return "coordination"
        return "implementation"

    tokens = _tokens(command)
    if tool_name == "bash":
        if _is_restricted_command(tokens):
            return "restricted"
        if _is_coordination_command(tokens):
            return "coordination"
        if _is_implementation_command(tokens):
            return "implementation"
        return "implementation"

    return "implementation"


def _policy_required_classes(policy: Any) -> frozenset[str]:
    if isinstance(policy, Mapping):
        raw = policy.get("delegation_required_mutation_classes")
    else:
        raw = getattr(policy, "delegation_required_mutation_classes", None)
    if not isinstance(raw, (list, tuple, set, frozenset)):
        return DEFAULT_DELEGATION_REQUIRED_MUTATION_CLASSES
    return frozenset(str(item) for item in raw if str(item) in BASELINE_NAMES_SET)


def foreman_would_deny(
    seat_class: str,
    work_class: str,
    mutation_class: str | None,
    policy: Any,
) -> str | None:
    """Return a value-free deny reason when a foreman must delegate."""
    resolved = resolve_seat_class(seat_class)
    if resolved == "worker":
        return None
    if work_class != "implementation":
        return None
    if str(mutation_class or "") not in _policy_required_classes(policy):
        return None
    return "implementation work requires worker delegation"
