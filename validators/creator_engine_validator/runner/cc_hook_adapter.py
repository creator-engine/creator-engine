"""v3 G-4 Tier-B adapter: derive an :class:`AgentActionEvent` from a Claude-Code hook payload.

The first transport emitter for the agent-interaction contract — the
OAuth/subscription-first-class **Tier B** (Claude-Code ``PreToolUse`` hook /
``--output-format stream-json``). This module is the *derivation* layer: a PURE
function that reduces a ``PreToolUse``-shaped payload to the canonical
:class:`AgentActionEvent` the classifier + ``decide()`` control-point consume. The
live event *source* (the actual hook subprocess / stream-json tap that delivers
the payload) is a deferred seam — here a payload is a value.

Design invariants (deliberate, load-bearing):

* **PURE.** No I/O, no subprocess, no socket, no clock. It maps a dict to a frozen
  event value; importing it performs zero I/O.
* **Tier-B fidelity = ``best_effort``.** CC-hooks have decent observation but soft
  enforcement; the single conservative ``fidelity = min(observation, enforcement)``
  is ``best_effort`` (never ``faithful``). ``timing = pre`` — a ``PreToolUse`` hook
  gates before execution.
* **Boundary-clean reuse (v1 ⊥ v3).** ``mutation_class`` is derived against the
  **shared** ``checks.mutation_class`` taxonomy (``BASELINE_NAMES_SET``) — the
  authoritative class vocabulary. This module deliberately does **NOT** import the
  v1 ``hook_check`` runtime: ``hook_check`` is a ``v1`` module and ``runner.*`` is
  ``v3``, so importing it would be a HARD ``version_boundary`` crossing. The
  path/command→class mapping here is a modest, honest first-cut in the v3 surface;
  reaching parity with v1 ``hook_check``'s nuanced secret/command heuristics is a
  ratified follow-on (a shared extraction or scoped re-derivation), not a silent
  boundary crossing or a silent copy.

Defensive only — it turns an observed agent action into governed, fidelity-tagged
evidence input; it never performs the action.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from ..checks.mutation_class import BASELINE_NAMES_SET
from .audit_overlay import AgentActionEvent

#: CC-hooks tier fidelity (conservative min of observation-integrity and
#: enforcement-strength). Stamped here by the adapter, never by the agent.
TIER_B_FIDELITY = "best_effort"
#: A ``PreToolUse`` hook gates before the tool runs.
TIER_B_TIMING = "pre"

#: Claude-Code tool → op (the capability axis). Reads are observe-only.
_WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
_READ_TOOLS = frozenset({"Read", "Glob", "Grep", "LS", "NotebookRead"})
_EGRESS_TOOLS = frozenset({"WebFetch", "WebSearch"})

# Bash command shape → op (rough, deterministic; NOT the v1 hook_check heuristics).
_GIT_RE = re.compile(r"\bgit\b")
_GIT_PUSH_RE = re.compile(r"\bgit\s+push\b")
_EGRESS_CMD_RE = re.compile(r"\b(curl|wget|ssh|scp|sftp|nc|netcat|telnet|rsync)\b")
_SECRET_CMD_RE = re.compile(r"\b(gpg|openssl|ssh-keygen|ssh-add|pass|keychain|security)\b")


def _op_for(tool: str, command: str) -> str:
    """Derive the op axis from the tool (and, for ``Bash``, the command shape). PURE."""
    if tool in _WRITE_TOOLS:
        return "write"
    if tool in _READ_TOOLS:
        return "read"
    if tool in _EGRESS_TOOLS:
        return "egress"
    if tool == "Bash":
        if _SECRET_CMD_RE.search(command):
            return "secret"
        if _GIT_PUSH_RE.search(command) or _GIT_RE.search(command):
            return "vcs"
        if _EGRESS_CMD_RE.search(command):
            return "egress"
        return "exec"
    # Unknown tool — fail conservative (gateable), never silently observe-only.
    return "exec"


def _class_for_path(file_path: str) -> str:
    """Derive the blast-radius mutation_class from a path (PURE; first-cut conventions).

    Returns a member of the shared ``BASELINE_NAMES_SET`` taxonomy, or ``"none"``.
    """
    pp = PurePosixPath(file_path)
    parts = {part.lower() for part in pp.parts}
    name = pp.name
    lowered = file_path.lower()

    if ".github" in parts:
        return "deploy" if "workflows" in parts else "governance"
    if "schemas" in parts or ".schema." in name or name.endswith((".schema.yaml", ".schema.json")):
        return "schema"
    if "redaction" in lowered or "redactions" in parts:
        return "redaction"
    if "attestation" in lowered or "attestations" in parts:
        return "attestation"
    if "identity" in lowered or "controller-key" in lowered:
        return "identity"
    if "security" in parts or name.endswith((".pem", ".key", ".p12", ".pfx")):
        return "security"
    if "governance" in parts or name.upper().startswith("GOVERNANCE") or "ratification" in lowered:
        return "governance"
    if "docs" in parts or name.endswith(".md"):
        return "docs"
    if "src" in parts or "validators" in parts or name.endswith(
        (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".h")
    ):
        return "code"
    return "none"


def _class_for_command(command: str) -> str:
    """Derive a coarse mutation_class for a ``Bash`` command (PURE; first-cut)."""
    if _GIT_PUSH_RE.search(command):
        return "deploy"
    return "none"


def _normalize_class(candidate: str) -> str:
    """Pin the derived class to the shared vocabulary (``BASELINE_NAMES_SET`` ∪ ``none``)."""
    return candidate if (candidate == "none" or candidate in BASELINE_NAMES_SET) else "none"


def from_pre_tool_use(payload: Any) -> AgentActionEvent:
    """Derive an :class:`AgentActionEvent` from a Claude-Code ``PreToolUse`` payload (PURE).

    Reads ``tool_name``/``toolName`` and ``tool_input``/``toolInput`` (the
    payload shape the CC ``PreToolUse`` hook delivers). Derives ``op`` from the
    tool/command and ``mutation_class`` from the salient target via the shared
    taxonomy; stamps ``fidelity=best_effort`` + ``timing=pre``. A non-dict /
    empty payload yields a conservative gateable ``exec``/``none`` event.
    """
    if not isinstance(payload, dict):
        return AgentActionEvent(
            op="exec", mutation_class="none", target="", tool="unknown",
            fidelity=TIER_B_FIDELITY, timing=TIER_B_TIMING,
        )

    tool = payload.get("tool_name") or payload.get("toolName") or ""
    tool = tool if isinstance(tool, str) else ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    command = tool_input.get("command")
    command = command if isinstance(command, str) else ""
    file_path = tool_input.get("file_path")
    file_path = file_path if isinstance(file_path, str) else ""
    url = tool_input.get("url")
    url = url if isinstance(url, str) else ""

    op = _op_for(tool, command)

    if file_path:
        mutation_class, target = _normalize_class(_class_for_path(file_path)), file_path
    elif command:
        mutation_class, target = _normalize_class(_class_for_command(command)), command
    elif url:
        mutation_class, target = "none", url
    else:
        mutation_class, target = "none", ""

    if command:
        first = command.split()[0] if command.split() else command
        tool_repr = f"{tool or 'Bash'}:{first}"
    else:
        tool_repr = tool or "unknown"

    return AgentActionEvent(
        op=op,
        mutation_class=mutation_class,
        target=target,
        tool=tool_repr,
        fidelity=TIER_B_FIDELITY,
        timing=TIER_B_TIMING,
    )
