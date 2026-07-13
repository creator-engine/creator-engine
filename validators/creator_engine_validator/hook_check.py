"""Validator-backed hook bridge for Claude Code hooks (CC-G-B).

This module is the Ring 2 (VALIDATOR) substrate that a future Ring 1
Claude ``command``-type hook-pack (CC-G-C) calls in-band so that real-time
scope / mechanics / secret / completion gates and post-hoc verification
never diverge. It evaluates a single Claude hook event deterministically
and returns a machine-readable allow/deny/block decision.

Design contract: ``docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md``
(governed-posture predicate §7; prohibited mechanics §5; the three-ring
model §8). The posture predicate, manifest parsing, mutation-class
vocabulary, and completion-report checks are **reused** from the existing
validator surfaces rather than reimplemented:

* posture       → ``checks.pane_registry.evaluate_posture``
* path manifest → ``checks.path_manifest_fidelity.extract_manifest_paths*``
* mechanics     → ``checks.mutation_class.RESERVED_RESTRICTED``
* completion    → ``checks.completion_report_schema`` /
                  ``checks.completion_report_required_for_envelope`` /
                  ``checks.completion_report_terminal_sections``

Scope discipline: this module never launches Claude, never spawns a pane,
never authors ``.claude/**``, never runs live Integration Queue commands,
and never reads or echoes credential/secret bytes. It only classifies the
event it is handed.
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .seat_class import (
    FOREMAN_DELEGATION_REQUIRED_REASON,
    classify_work_class,
    foreman_would_deny,
    resolve_seat_class,
)
from .sec7_forge_guard import forge_mechanic_label

# v3.5-B.3 refusal-record seam: the SHARED hash-chain substrate only
# (V1->shared is the allowed boundary edge). The v3 evidence-persistence sink
# module is NEVER imported here — that would be the forbidden V1->V3 crossing.
from .runtime_evidence_spine import (
    CHAIN_KIND as _SPINE_CHAIN_KIND,
    RUNTIME_AGENT_ACTION_RECORD_KIND as _AGENT_ACTION_KIND,
    RUNTIME_AGENT_ACTION_RECORD_TYPE as _AGENT_ACTION_TYPE,
    append as _spine_append,
)

CONTRACT = "docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md"
REVIEWER_AUTHORITY_CAPABILITY = "independent_review_venue"

# Tools whose target file_path is subject to the scope gate.
SCOPE_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})

OUT_OF_MANIFEST_REASON = "tracked path is outside the ratified path manifest"
NO_WRITE_AUTHORITY_NOTE = "no write authority provisioned (envelope_ref=none)"
FOREMAN_DELEGATION_REASON = FOREMAN_DELEGATION_REQUIRED_REASON
DEFAULT_FOREMAN_MUTATION_CLASS = "code"
WORKER_RECORD_REL = Path(".ce/state/workers")
EXECUTION_PLANE_DENY_PREFIX = "execution-plane primitive"
EXECUTION_PLANE_DISPATCH_HINT = (
    "dispatch through a launch-pinned governed worker: "
    "ce worker run --role {role} --brief <brief> --worktree <allocated-worktree> "
    "(or ce lane launch --role {role} ...)"
)
WORKER_CONTEXT_ENV_KEYS = {
    "worker_id": "CE_WORKER_ID",
    "record_ref": "CE_WORKER_RECORD_REF",
    "role": "CE_WORKER_ROLE",
    "lane_kind": "CE_WORKER_LANE_KIND",
    "scope_id": "CE_WORKER_SCOPE_ID",
    "seat_id": "CE_WORKER_SEAT_ID",
    "actor": "CE_WORKER_ACTOR",
    "process_id": "CE_WORKER_PROCESS_ID",
}

_EXECUTION_PLANE_ROLE_HINTS: dict[str, str] = {
    "worktree_mutation": "implementer",
    "full_preflight": "implementer",
    "carrier_regeneration": "implementer",
    "bundle_extraction": "implementer",
    "harvest_push": "implementer",
    "agent_spawn": "implementer",
}

_EXECUTION_PLANE_ALLOWED_WORKERS: dict[str, frozenset[tuple[str, str]]] = {
    name: frozenset({("implementer", "implementation")})
    for name in _EXECUTION_PLANE_ROLE_HINTS
}
_SPAWN_TOOL_NAMES = frozenset({"agent", "task", "subagent", "multiagent", "multi_agent"})


# --------------------------------------------------------------------------
# Decision / context value objects
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class HookContext:
    """Resolved evaluation context for one hook event.

    ``posture`` is ``"governed"`` or ``"ungoverned"``. ``manifest_paths`` are
    repo-relative tracked paths the active ratified manifest authorizes.
    ``evidence_root`` is the ignored evidence-root prefix the gate may write
    under. ``closeout_text`` / ``completion_report_path`` feed the Stop gate.
    ``side_effect_authority`` is the validated, bounded reviewer-venue authority
    envelope (a ``reviewer_authority_envelope`` mapping) that opens exactly one
    restricted mechanic (``pr_review``) on exactly one PR — G2.007.2. ``None`` means
    no authority (restricted mechanics stay denied under governed posture). A raw
    string/loose token is NOT honored; only a schema-valid envelope is.
    """

    posture: str
    manifest_paths: tuple[str, ...] = ()
    evidence_root: str | None = None
    closeout_text: str | None = None
    completion_report_path: str | None = None
    side_effect_authority: dict | None = None
    seat_class: str = "foreman"
    seat_class_policy: dict | None = None
    worker_delegation: dict | None = None
    repo_root: str | None = None
    posture_note: str | None = None


@dataclass(frozen=True)
class ResolvedManifest:
    paths: tuple[str, ...] = ()
    posture_note: str | None = None


@dataclass(frozen=True)
class HookDecision:
    """A deterministic hook decision, serializable to Claude-hook JSON."""

    ok: bool
    hook_event_name: str
    posture: str
    decision: str  # "allow" | "deny" | "block"
    reason: str
    advisory: bool = False
    would_have_denied: bool = False
    hook_specific_output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "hookEventName": self.hook_event_name,
            "posture": self.posture,
            "decision": self.decision,
            "reason": self.reason,
            "advisory": self.advisory,
            "wouldHaveDenied": self.would_have_denied,
            "hookSpecificOutput": dict(self.hook_specific_output),
        }

    def to_claude_hook_dict(self) -> dict[str, Any]:
        """Render the minimal Claude Code hook output for this decision.

        This is an *additive* CC-G-C presentation seam; it changes no CC-G-B
        decision semantics. The mapping is:

        * ``PreToolUse`` → ``{"hookSpecificOutput": {"hookEventName":
          "PreToolUse", "permissionDecision": "deny"|"allow",
          "permissionDecisionReason": ...}}``. An ungoverned *advisory* deny
          already carries ``decision == "allow"`` here, so it maps to
          ``permissionDecision: "allow"`` — an ungoverned lane is never
          hard-denied — with the advisory context preserved in the reason.
        * ``Stop`` block → ``{"decision": "block", "reason": ...}``. A Stop
          allow/advisory emits no ``decision`` key (no-decision == allow).
        * any other event → ``{}`` (no Claude-actionable output).
        """
        if self.hook_event_name == "Stop":
            if self.decision == "block":
                return {"decision": "block", "reason": self.reason}
            return {}
        if self.hook_event_name == "PreToolUse":
            permission = "deny" if self.decision == "deny" else "allow"
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": permission,
                    "permissionDecisionReason": self.reason,
                }
            }
        return {}


# --------------------------------------------------------------------------
# Secret classification (PreToolUse Read)
# --------------------------------------------------------------------------
#
# The credential-path predicate is the single source of truth, hoisted into the
# shared ``secret_paths`` module so the v3 runner filesystem-mediation layer can
# reuse the EXACT same rules without crossing the v1<->v3 version boundary
# (importing a *shared* module is allowed from either line). Re-exported here so
# this module's public ``hook_check.is_secret_path`` API is byte-for-byte
# unchanged for existing callers.
from .secret_paths import is_secret_path  # noqa: E402  (re-export; single source of truth)


# --------------------------------------------------------------------------
# Mechanics classification (PreToolUse Bash)
# --------------------------------------------------------------------------

# Commands that map cleanly onto the shared mutation-class reserved-restricted
# vocabulary. Reusing ``mutation_class.RESERVED_RESTRICTED`` keeps the bridge
# anchored to the canonical taxonomy rather than a bespoke parallel list.
_MECHANIC_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgh\s+pr\s+merge\b"), "merge"),
    (re.compile(r"\b(npm|pnpm|yarn)\s+publish\b"), "publish"),
    (re.compile(r"\btwine\s+upload\b"), "publish"),
    (re.compile(r"\bcargo\s+publish\b"), "publish"),
)

# Mechanics the seat contract prohibits that do not map onto a mutation-class
# action verb. Classified with explicit non-vocabulary labels; still denied.
_MECHANIC_RULES_NONVOCAB: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgh\s+pr\s+review\b"), "pr_review"),
    (re.compile(r"\bgh\s+pr\s+comment\b"), "pr_comment"),
    (re.compile(r"\bgh\s+pr\s+(close|reopen)\b"), "pr_lifecycle"),
    (re.compile(r"\bce\s+(launch|lane\s+launch)\b"), "live_lane_launch"),
    (re.compile(r"\bce\s+(integration-queue|iq)\b"), "live_integration_queue"),
    # Ring-1 toolchain self-update block (ce-ops#271).
    # Global JS package manager installs: npm/pnpm/yarn install -g or add/update/upgrade --global.
    (re.compile(r"\b(npm|pnpm|yarn)\s+install\s+(?:.*\s+)?(-g|--global)\b"), "toolchain_self_update"),
    (re.compile(r"\b(npm|pnpm|yarn)\s+(add|update|upgrade)\s+(?:.*\s+)?(-g|--global)\b"), "toolchain_self_update"),
    # pip install/upgrade from index. The --no-index flag exempts CE's own VenvSwapper
    # (update.py: `pip install --no-index --find-links <wheelhouse> <package>`).
    (re.compile(r"\bpip[0-9.]*\s+(install|upgrade)\b(?!.*--no-index)"), "toolchain_self_update"),
    # System package managers.
    (re.compile(r"\b(apt|apt-get)\s+(install|upgrade|dist-upgrade)\b"), "toolchain_self_update"),
    (re.compile(r"\bdpkg\s+-i\b"), "toolchain_self_update"),
    # Pipe-to-shell installer patterns (curl|sh, wget|sh).
    (re.compile(r"\bcurl\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh\b"), "toolchain_self_update"),
    (re.compile(r"\bwget\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh\b"), "toolchain_self_update"),
)

_GIT_OPAQUE_MECHANIC = "git_opaque"
_GIT_GLOBAL_OPTIONS_WITH_VALUE = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--exec-path",
        "--config-env",
        "--super-prefix",
    }
)
_GIT_GLOBAL_OPTIONS_WITH_OPTIONAL_VALUE = frozenset({"--exec-path"})
_GIT_GLOBAL_OPTIONS_WITH_EQUALS = tuple(
    f"{option}="
    for option in (
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--exec-path",
        "--config-env",
        "--super-prefix",
    )
)
_GIT_GLOBAL_OPTIONS_NO_VALUE = frozenset(
    {
        "-p",
        "--paginate",
        "--no-pager",
        "--bare",
        "--no-replace-objects",
        "--literal-pathspecs",
        "--glob-pathspecs",
        "--noglob-pathspecs",
        "--icase-pathspecs",
        "--no-optional-locks",
        "--version",
        "--help",
    }
)
_SHELL_SEPARATORS = frozenset({";", "&&", "||", "|", "(", ")"})
_SHELL_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")
_GIT_SAFE_READONLY_SUBCOMMANDS = frozenset(
    {
        "status",
        "diff",
        "log",
        "show",
        "rev-parse",
        "show-ref",
        "ls-files",
        "ls-tree",
        "cat-file",
        "describe",
        "name-rev",
        "merge-base",
    }
)


def _yaml_safe_load_text(text: str) -> Any:
    import yaml

    return yaml.safe_load(text)


def _yaml_safe_dump_document(document: Any) -> str:
    import yaml

    return yaml.safe_dump(document, sort_keys=True, allow_unicode=True)


def _extract_manifest_paths_from_file(path: Path) -> tuple[str, ...]:
    try:
        from .checks.path_manifest_fidelity import extract_manifest_paths_from_file
    except Exception:
        return ()
    return tuple(extract_manifest_paths_from_file(path))


_GIT_BUILTINS = _GIT_SAFE_READONLY_SUBCOMMANDS | frozenset(
    {
        # Restricted outward/binding side effects.
        "push",
        "send-pack",
        "branch",
        # Foreign-VCS bridges: only their outward sub-verb (p4 submit /
        # svn dcommit) binds remotely; the per-sub-verb split happens below.
        "p4",
        "svn",
        # Ordinary local porcelain used constantly inside governed seats.
        "add",
        "am",
        "apply",
        "bisect",
        "blame",
        "checkout",
        "cherry-pick",
        "clean",
        "clone",
        "commit",
        "config",
        "fetch",
        "grep",
        "init",
        "merge",
        "mv",
        "notes",
        "pull",
        "rebase",
        "reflog",
        "remote",
        "reset",
        "restore",
        "revert",
        "rm",
        "stash",
        "submodule",
        "switch",
        "tag",
        "worktree",
        # Common plumbing/read helpers.
        "check-attr",
        "check-ignore",
        "check-ref-format",
        "count-objects",
        "for-each-ref",
        "hash-object",
        "ls-remote",
        "rev-list",
        "update-index",
    }
)


def _shell_tokens(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def _is_git_executable(token: str) -> bool:
    return token == "git" or token.endswith("/git")


def _record_git_alias(config: str, aliases: dict[str, str]) -> None:
    key, sep, value = config.partition("=")
    if not sep:
        return
    key = key.strip().lower()
    if key.startswith("alias.") and len(key) > len("alias."):
        aliases[key[len("alias.") :]] = value.strip()


def _git_branch_deletes(args: tuple[str, ...]) -> bool:
    for arg in args:
        if arg in {"-d", "-D", "--delete"} or arg.startswith("--delete="):
            return True
        if arg.startswith("-") and not arg.startswith("--") and ("d" in arg or "D" in arg):
            return True
    return False


def _git_push_deletes_ref(args: tuple[str, ...]) -> bool:
    for arg in args:
        if arg in {"-d", "--delete"} or arg.startswith("--delete="):
            return True
    return False


# Conceptual restricted "verbs" for the abbreviation guard: a directly-typed
# unknown subcommand that is a UNIQUE prefix of exactly one of these maps to that
# verb's mechanic (e.g. ``git pus`` -> push -> deploy), which removes the
# dependency on git's autocorrect. An ambiguous prefix (matching >1 verb) or a
# non-prefix unknown is NOT a unique prefix and stays ``None`` (allow).
_RESTRICTED_PREFIX_VERBS: tuple[tuple[str, str], ...] = (
    ("push", "deploy"),
    ("send-pack", "deploy"),
    ("branch-delete", "alter_repo_settings"),
)

# Foreign-VCS bridge subcommands -> their ONLY known outward (deploy) sub-verb.
# Every other sub-verb (e.g. ``p4 sync`` / ``svn fetch``) is a read -> allow; an
# ABSENT or unparseable sub-verb is conservatively classified as the outward one.
_VCS_BRIDGE_OUTWARD_SUBVERB: dict[str, str] = {
    "p4": "submit",
    "svn": "dcommit",
}


def _classify_unknown_prefix(subcommand: str) -> str | None:
    """Abbreviation guard for a directly-typed unknown git subcommand.

    Return the mechanic of the restricted verb that ``subcommand`` is a UNIQUE
    prefix of. If it prefixes more than one restricted verb (ambiguous) or none,
    it is not a unique prefix and stays ``None`` (allow).
    """
    if not subcommand:
        return None
    matched = [
        (verb, mechanic)
        for verb, mechanic in _RESTRICTED_PREFIX_VERBS
        if verb.startswith(subcommand)
    ]
    return matched[0][1] if len(matched) == 1 else None


def _vcs_bridge_subverb(args: tuple[str, ...]) -> str | None:
    """Return the first positional (non-option) token in ``args`` — the p4/svn
    sub-verb — or ``None`` when none is determinable (absent / unparseable).

    Leading options are skipped; a shell separator ends parsing. ``None`` is the
    caller's signal to fall conservative (treat the bridge call as outward).
    """
    for arg in args:
        if arg in _SHELL_SEPARATORS:
            break
        if arg == "--":
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def _classify_git_subcommand(
    subcommand: str,
    args: tuple[str, ...],
    aliases: dict[str, str],
) -> str | None:
    """Map a resolved git subcommand to a restricted mechanic.

    Git built-ins take precedence over same-named aliases. Restricted built-ins
    are ``push`` / ``send-pack`` (deploy, except push ref deletion ->
    alter_repo_settings), branch deletion (alter_repo_settings), and the
    foreign-VCS bridges' outward sub-verb (``p4 submit`` / ``svn dcommit`` ->
    deploy); ordinary local built-ins return ``None``. Inline aliases are
    resolved only for non-built-in names. Unparseable alias shapes stay
    conservative (``git_opaque``). A directly-typed unknown subcommand is run
    through the abbreviation guard (unique prefix of a restricted verb), else
    ``None`` because git itself will reject it.
    """

    seen: set[str] = set()
    while subcommand not in _GIT_BUILTINS:
        if subcommand not in aliases:
            # A directly-typed unknown (no alias, no prior alias hop) gets the
            # abbreviation guard; an unknown reached VIA an alias hop stays
            # conservative (git_opaque) — we cannot trust its expansion.
            return _GIT_OPAQUE_MECHANIC if seen else _classify_unknown_prefix(subcommand)
        if subcommand in seen:
            return _GIT_OPAQUE_MECHANIC
        seen.add(subcommand)
        alias = aliases[subcommand]
        if not alias or alias.startswith("!"):
            return _GIT_OPAQUE_MECHANIC
        try:
            alias_tokens = _shell_tokens(alias)
        except ValueError:
            return _GIT_OPAQUE_MECHANIC
        if not alias_tokens:
            return _GIT_OPAQUE_MECHANIC
        if _is_git_executable(alias_tokens[0]):
            nested = _classify_git_tokens(alias_tokens[1:])
            return nested or _GIT_OPAQUE_MECHANIC
        if alias_tokens[0].startswith("-"):
            return _GIT_OPAQUE_MECHANIC
        subcommand = alias_tokens[0]
        args = (*alias_tokens[1:], *args)

    if subcommand == "push" and _git_push_deletes_ref(args):
        return "alter_repo_settings"
    if subcommand in {"push", "send-pack"}:
        return "deploy"
    if subcommand == "branch":
        return "alter_repo_settings" if _git_branch_deletes(args) else None
    if subcommand in _VCS_BRIDGE_OUTWARD_SUBVERB:
        subverb = _vcs_bridge_subverb(args)
        if subverb is None:
            return "deploy"  # absent/unparseable sub-verb -> conservative deploy
        return "deploy" if subverb == _VCS_BRIDGE_OUTWARD_SUBVERB[subcommand] else None
    return None


def _classify_git_tokens(tokens: list[str]) -> str | None:
    aliases: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _SHELL_SEPARATORS:
            return None
        if token.startswith("-c") and token != "-c":
            _record_git_alias(token[2:], aliases)
            i += 1
            continue
        if any(token.startswith(prefix) for prefix in _GIT_GLOBAL_OPTIONS_WITH_EQUALS):
            i += 1
            continue
        if token in _GIT_GLOBAL_OPTIONS_WITH_VALUE:
            if token == "-c":
                if i + 1 >= len(tokens):
                    return _GIT_OPAQUE_MECHANIC
                _record_git_alias(tokens[i + 1], aliases)
                i += 2
                continue
            if token in _GIT_GLOBAL_OPTIONS_WITH_OPTIONAL_VALUE:
                if i + 1 < len(tokens) and tokens[i + 1] not in _SHELL_SEPARATORS:
                    i += 2
                    continue
                i += 1
                continue
            if i + 1 >= len(tokens):
                return _GIT_OPAQUE_MECHANIC
            i += 2
            continue
        if token in _GIT_GLOBAL_OPTIONS_NO_VALUE:
            i += 1
            continue
        if token == "--":
            i += 1
            continue
        if token.startswith("-"):
            return _GIT_OPAQUE_MECHANIC
        return _classify_git_subcommand(token, tuple(tokens[i + 1 :]), aliases)
    return None


def _classify_git_mechanics(command: str) -> str | None:
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return _GIT_OPAQUE_MECHANIC if re.search(r"\bgit\b", command) else None
    for index, token in enumerate(tokens):
        if _is_git_executable(token):
            action = _classify_git_tokens(tokens[index + 1 :])
            if action is not None:
                return action
    return None


def _is_gh_executable(token: str) -> bool:
    return token == "gh" or token.endswith("/gh")


def _is_curl_executable(token: str) -> bool:
    return token == "curl" or token.endswith("/curl")


def _token_value(token: str, prefixes: Iterable[str]) -> str | None:
    for prefix in prefixes:
        marker = f"{prefix}="
        if token.startswith(marker):
            return token[len(marker) :]
    return None


_GH_API_OPTIONS_WITH_VALUE = frozenset(
    {
        "-H",
        "--header",
        "--hostname",
        "--input",
        "-p",
        "--preview",
        "-q",
        "--jq",
        "-t",
        "--template",
        "--cache",
    }
)
_GH_API_FIELD_OPTIONS = frozenset({"-f", "--field", "-F", "--raw-field"})
_GH_API_METHOD_OPTIONS = frozenset({"-X", "--method"})
_GH_API_OPTIONS_NO_VALUE = frozenset(
    {"-i", "--include", "--paginate", "--silent", "--slurp", "--verbose"}
)

_CURL_METHOD_OPTIONS = frozenset({"-X", "--request"})
_CURL_URL_OPTIONS = frozenset({"--url"})
_CURL_DATA_OPTIONS = frozenset({"-d", "--data", "--data-raw", "--data-binary"})
_CURL_OPTIONS_WITH_VALUE = frozenset(
    {
        "-A",
        "--user-agent",
        "-b",
        "--cookie",
        *_CURL_DATA_OPTIONS,
        "--data-urlencode",
        "-H",
        "--header",
        "-o",
        "--output",
        "-u",
        "--user",
    }
)

_PYTHON_EXECUTABLES = frozenset({"python", "python3"})


def _is_python_executable(token: str) -> bool:
    name = PurePosixPath(token).name
    return name in _PYTHON_EXECUTABLES or bool(re.fullmatch(r"python3?\.\d+", name))


def _command_segments(command: str) -> list[tuple[str, ...]]:
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return []
    segments: list[tuple[str, ...]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            if current:
                segments.append(tuple(current))
                current = []
            continue
        current.append(token)
    if current:
        segments.append(tuple(current))
    return segments


def _strip_env_prefix(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if not tokens:
        return tokens
    index = 0
    if PurePosixPath(tokens[index]).name == "env":
        index += 1
        while index < len(tokens):
            token = tokens[index]
            if token == "-u":
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            if _SHELL_ASSIGNMENT_RE.match(token):
                index += 1
                continue
            break
    while index < len(tokens) and _SHELL_ASSIGNMENT_RE.match(tokens[index]):
        index += 1
    return tokens[index:]


def _classify_ce_forge_tokens(tokens: tuple[str, ...]) -> str | None:
    if not tokens:
        return None
    executable = PurePosixPath(tokens[0]).name
    if executable in {"ce", "cev3"} and len(tokens) >= 2:
        return forge_mechanic_label(tokens[1])
    if _is_python_executable(tokens[0]) and len(tokens) >= 4 and tokens[1] == "-m":
        module = tokens[2]
        if module == "creator_engine_validator.v3_cli":
            return forge_mechanic_label(tokens[3])
    return None


def _classify_ce_forge_mechanics(command: str) -> str | None:
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return None
    start = 0
    for index, token in enumerate(tokens):
        if token in _SHELL_SEPARATORS:
            start = index + 1
            continue
        action = _classify_ce_forge_tokens(tuple(tokens[index:]))
        if action is not None:
            return action
        if index == start and token in {"env", "/usr/bin/env"}:
            continue
    return None


def _github_api_path_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc.lower() != "api.github.com":
        return None
    return parsed.path or "/"


def _github_api_path_from_curl_target(value: str) -> str | None:
    path = _github_api_path_from_url(value)
    if path is not None:
        return path
    stripped = value.split("?", 1)[0].split("#", 1)[0]
    if stripped.startswith("/repos/") or stripped.startswith("repos/"):
        return _normalize_github_api_path(value)
    return None


def _normalize_github_api_path(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc.lower() == "api.github.com":
        path = parsed.path
    else:
        path = value.split("?", 1)[0].split("#", 1)[0]
    return path if path.startswith("/") else f"/{path}"


def _field_value_is_approve_event(value: str) -> bool:
    key, sep, raw = value.partition("=")
    return bool(sep) and key.strip().lower() == "event" and raw.strip().upper() == "APPROVE"


_INLINE_APPROVE_EVENT_RE = re.compile(
    r"""(?ix)
    \\?["']event\\?["']
    \s*:\s*
    \\?["']APPROVE\\?["']
    """
)


def _command_mentions_approve_event(command: str) -> bool:
    return bool(_INLINE_APPROVE_EVENT_RE.search(command))


def _body_value_is_approve_event(value: str) -> bool:
    return _field_value_is_approve_event(value) or _command_mentions_approve_event(value)


def _body_value_is_unreadable(value: str) -> bool:
    stripped = value.strip()
    return stripped == "-" or stripped.startswith("@")


def _github_review_pr_number(path: str) -> int | None:
    parts = tuple(part for part in path.split("/") if part)
    if (
        len(parts) == 6
        and parts[0] == "repos"
        and parts[3] == "pulls"
        and parts[5] == "reviews"
        and parts[4].isdigit()
    ):
        return int(parts[4])
    if (
        len(parts) == 8
        and parts[0] == "repos"
        and parts[3] == "pulls"
        and parts[5] == "reviews"
        and parts[7] == "events"
        and parts[4].isdigit()
    ):
        return int(parts[4])
    return None


def _parse_gh_api_call(args: tuple[str, ...]) -> tuple[str, str, bool] | None:
    method: str | None = None
    field_implies_post = False
    approve_event = False
    path: str | None = None
    i = 0
    while i < len(args):
        token = args[i]
        if token in _SHELL_SEPARATORS:
            break
        if token in _GH_API_METHOD_OPTIONS:
            if i + 1 >= len(args):
                return None
            method = args[i + 1].upper()
            i += 2
            continue
        method_value = _token_value(token, ("--method",))
        if method_value is not None:
            method = method_value.upper()
            i += 1
            continue
        if token.startswith("-X") and token != "-X":
            method = token[2:].upper()
            i += 1
            continue
        if token in _GH_API_FIELD_OPTIONS:
            field_implies_post = True
            if i + 1 < len(args) and _field_value_is_approve_event(args[i + 1]):
                approve_event = True
            i += 2 if i + 1 < len(args) else 1
            continue
        field_value = _token_value(token, ("--field", "--raw-field"))
        if field_value is not None:
            field_implies_post = True
            if _field_value_is_approve_event(field_value):
                approve_event = True
            i += 1
            continue
        if (token.startswith("-f") or token.startswith("-F")) and token not in {"-f", "-F"}:
            field_implies_post = True
            if _field_value_is_approve_event(token[2:]):
                approve_event = True
            i += 1
            continue
        if token == "--input":
            approve_event = True
            i += 2 if i + 1 < len(args) else 1
            continue
        input_value = _token_value(token, ("--input",))
        if input_value is not None:
            approve_event = True
            i += 1
            continue
        if token in _GH_API_OPTIONS_WITH_VALUE:
            i += 2 if i + 1 < len(args) else 1
            continue
        if _token_value(token, _GH_API_OPTIONS_WITH_VALUE) is not None:
            i += 1
            continue
        if token in _GH_API_OPTIONS_NO_VALUE:
            i += 1
            continue
        if token.startswith("-"):
            i += 1
            continue
        if path is None:
            path = token
        i += 1
    if path is None:
        return None
    return (
        (method or ("POST" if field_implies_post else "GET")).upper(),
        _normalize_github_api_path(path),
        approve_event,
    )


def _parse_curl_api_call(args: tuple[str, ...]) -> tuple[str, str, bool] | None:
    method: str | None = None
    url: str | None = None
    data_implies_post = False
    approve_event = False
    i = 0
    while i < len(args):
        token = args[i]
        if token in _SHELL_SEPARATORS:
            break
        if token in _CURL_METHOD_OPTIONS:
            if i + 1 >= len(args):
                return None
            method = args[i + 1].upper()
            i += 2
            continue
        request_value = _token_value(token, ("--request",))
        if request_value is not None:
            method = request_value.upper()
            i += 1
            continue
        if token.startswith("-X") and token != "-X":
            method = token[2:].upper()
            i += 1
            continue
        if token in _CURL_URL_OPTIONS:
            if i + 1 >= len(args):
                return None
            candidate = _github_api_path_from_curl_target(args[i + 1])
            if candidate is not None:
                url = args[i + 1]
            i += 2
            continue
        if _token_value(token, _CURL_URL_OPTIONS) is not None:
            candidate_url = _token_value(token, _CURL_URL_OPTIONS) or ""
            if _github_api_path_from_curl_target(candidate_url) is not None:
                url = candidate_url
            i += 1
            continue
        if token in _CURL_DATA_OPTIONS:
            data_implies_post = True
            if i + 1 < len(args):
                approve_event = approve_event or _body_value_is_approve_event(args[i + 1])
                approve_event = approve_event or _body_value_is_unreadable(args[i + 1])
            i += 2 if i + 1 < len(args) else 1
            continue
        data_value = _token_value(token, tuple(_CURL_DATA_OPTIONS - {"-d"}))
        if data_value is not None:
            data_implies_post = True
            approve_event = approve_event or _body_value_is_approve_event(data_value)
            approve_event = approve_event or _body_value_is_unreadable(data_value)
            i += 1
            continue
        if token.startswith("-d") and token != "-d":
            data_implies_post = True
            data_value = token[2:]
            approve_event = approve_event or _body_value_is_approve_event(data_value)
            approve_event = approve_event or _body_value_is_unreadable(data_value)
            i += 1
            continue
        candidate = _github_api_path_from_curl_target(token)
        if candidate is not None:
            url = token
            i += 1
            continue
        if token in _CURL_OPTIONS_WITH_VALUE:
            i += 2 if i + 1 < len(args) else 1
            continue
        if _token_value(token, _CURL_OPTIONS_WITH_VALUE) is not None:
            i += 1
            continue
        i += 1
    if url is None:
        return None
    return (
        (method or ("POST" if data_implies_post else "GET")).upper(),
        _github_api_path_from_curl_target(url) or "/",
        approve_event,
    )


def _repo_path_tail(path: str) -> tuple[str, ...] | None:
    parts = tuple(part for part in path.split("/") if part)
    if len(parts) < 3 or parts[0] != "repos":
        return None
    return parts[3:]


_GITHUB_REPO_SETTINGS_SEGMENTS = frozenset(
    {
        "actions",
        "autolinks",
        "branches",
        "collaborators",
        "codespaces",
        "dependabot",
        "environments",
        "git",
        "hooks",
        "keys",
        "pages",
        "properties",
        "rules",
        "rulesets",
        "secret-scanning",
        "secrets",
        "security-and-analysis",
        "refs",
        "settings",
        "teams",
        "vulnerability-alerts",
    }
)


def _classify_github_api_request(
    method: str,
    path: str,
    *,
    approve_event: bool = False,
) -> str | None:
    method = method.upper()
    if method in {"GET", "HEAD"}:
        return None
    if method not in {"DELETE", "PATCH", "PUT", "POST"}:
        return None
    if approve_event and _github_review_pr_number(path) is not None:
        return "pr_review"
    tail = _repo_path_tail(path)
    if tail is None:
        return None
    if not tail:
        return "alter_repo_settings"
    if tail[0] == "contents":
        return "deploy"
    if tail[0] in _GITHUB_REPO_SETTINGS_SEGMENTS:
        return "alter_repo_settings"
    if "protection" in tail or any(part.endswith("secrets") for part in tail):
        return "alter_repo_settings"
    return None


def _classify_github_api_mechanics(command: str) -> str | None:
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return "alter_repo_settings" if "api.github.com/repos/" in command else None
    inline_approve_event = _command_mentions_approve_event(command)
    for index, token in enumerate(tokens):
        if _is_gh_executable(token) and index + 1 < len(tokens) and tokens[index + 1] == "api":
            parsed = _parse_gh_api_call(tuple(tokens[index + 2 :]))
            if parsed is not None:
                method, path, field_approve_event = parsed
                action = _classify_github_api_request(
                    method,
                    path,
                    approve_event=field_approve_event or inline_approve_event,
                )
                if action is not None:
                    return action
        if _is_curl_executable(token):
            parsed = _parse_curl_api_call(tuple(tokens[index + 1 :]))
            if parsed is not None:
                method, path, body_approve_event = parsed
                action = _classify_github_api_request(
                    method,
                    path,
                    approve_event=body_approve_event or inline_approve_event,
                )
                if action is not None:
                    return action
    return None


def _is_raw_gh_api_review_approve(command: Any) -> bool:
    if not isinstance(command, str):
        return False
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return False
    inline_approve_event = _command_mentions_approve_event(command)
    for index, token in enumerate(tokens):
        if _is_gh_executable(token) and index + 1 < len(tokens) and tokens[index + 1] == "api":
            parsed = _parse_gh_api_call(tuple(tokens[index + 2 :]))
            if parsed is None:
                continue
            method, path, field_approve_event = parsed
            if (
                method.upper() in {"DELETE", "PATCH", "PUT", "POST"}
                and (field_approve_event or inline_approve_event)
                and _github_review_pr_number(path) is not None
            ):
                return True
        if _is_curl_executable(token):
            parsed = _parse_curl_api_call(tuple(tokens[index + 1 :]))
            if parsed is None:
                continue
            method, path, body_approve_event = parsed
            if (
                method.upper() in {"DELETE", "PATCH", "PUT", "POST"}
                and (body_approve_event or inline_approve_event)
                and _github_review_pr_number(path) is not None
            ):
                return True
    return False


def _is_gh_pr_review_approve(command: Any) -> bool:
    if not isinstance(command, str):
        return False
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return False
    for index, token in enumerate(tokens):
        if not (
            _is_gh_executable(token)
            and index + 3 < len(tokens)
            and tokens[index + 1] == "pr"
            and tokens[index + 2] == "review"
        ):
            continue
        review_args = tokens[index + 3 :]
        return any(arg == "-a" or arg.startswith("--approve") for arg in review_args)
    return False


def classify_mechanics(command: Any) -> str | None:
    """Return the restricted classification for ``command``, or ``None``.

    Mappable destructive git/release commands return a
    ``mutation_class.RESERVED_RESTRICTED`` action verb; other prohibited
    mechanics return a dedicated non-vocabulary label.
    """
    if not isinstance(command, str):
        return None
    forge_action = _classify_ce_forge_mechanics(command)
    if forge_action is not None:
        return forge_action
    git_action = _classify_git_mechanics(command)
    if git_action is not None:
        return git_action
    github_api_action = _classify_github_api_mechanics(command)
    if github_api_action is not None:
        return github_api_action
    for pattern, action in _MECHANIC_RULES + _MECHANIC_RULES_NONVOCAB:
        if pattern.search(command):
            return action
    return None


_GIT_WORKTREE_MUTATING_VERBS = frozenset(
    {"add", "remove", "rm", "move", "prune", "repair", "lock", "unlock"}
)


def _first_positional(args: tuple[str, ...]) -> str | None:
    index = 0
    while index < len(args):
        token = args[index]
        if token in _SHELL_SEPARATORS:
            return None
        if token == "--":
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def _git_subcommand_and_args_from_tokens(
    tokens: tuple[str, ...],
    aliases: dict[str, str] | None = None,
) -> tuple[str, tuple[str, ...]] | None:
    aliases = aliases or {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _SHELL_SEPARATORS:
            return None
        if token.startswith("-c") and token != "-c":
            _record_git_alias(token[2:], aliases)
            index += 1
            continue
        if token == "-c":
            if index + 1 >= len(tokens):
                return None
            _record_git_alias(tokens[index + 1], aliases)
            index += 2
            continue
        if any(token.startswith(prefix) for prefix in _GIT_GLOBAL_OPTIONS_WITH_EQUALS):
            index += 1
            continue
        if token in _GIT_GLOBAL_OPTIONS_WITH_VALUE:
            if index + 1 >= len(tokens):
                return None
            index += 2
            continue
        if token in _GIT_GLOBAL_OPTIONS_NO_VALUE:
            index += 1
            continue
        if token == "--":
            index += 1
            continue
        if token.startswith("-"):
            return None

        subcommand = token
        args = tuple(tokens[index + 1 :])
        seen: set[str] = set()
        while subcommand not in _GIT_BUILTINS:
            alias = aliases.get(subcommand)
            if alias is None or subcommand in seen or not alias or alias.startswith("!"):
                return subcommand, args
            seen.add(subcommand)
            try:
                alias_tokens = tuple(_shell_tokens(alias))
            except ValueError:
                return None
            if not alias_tokens:
                return None
            if _is_git_executable(alias_tokens[0]):
                nested = _git_subcommand_and_args_from_tokens(tuple(alias_tokens[1:]), aliases)
                if nested is None:
                    return None
                nested_subcommand, nested_args = nested
                return nested_subcommand, (*nested_args, *args)
            if alias_tokens[0].startswith("-"):
                return None
            subcommand = alias_tokens[0]
            args = (*alias_tokens[1:], *args)
        return subcommand, args
    return None


def _git_push_targets_harvest(args: tuple[str, ...]) -> bool:
    for arg in args:
        lowered = arg.lower()
        if "push-for-harvest" in lowered:
            return True
        if "harvest/" in lowered or "refs/heads/harvest" in lowered:
            return True
    return False


def _classify_git_execution_plane(tokens: tuple[str, ...]) -> str | None:
    if not tokens or not _is_git_executable(tokens[0]):
        return None
    parsed = _git_subcommand_and_args_from_tokens(tokens[1:])
    if parsed is None:
        return None
    subcommand, args = parsed
    if subcommand == "worktree":
        verb = _first_positional(args)
        if verb in _GIT_WORKTREE_MUTATING_VERBS:
            return "worktree_mutation"
    if subcommand == "push" and _git_push_targets_harvest(args):
        return "harvest_push"
    return None


def _classify_ce_execution_plane(tokens: tuple[str, ...]) -> str | None:
    if not tokens:
        return None
    executable = PurePosixPath(tokens[0]).name
    if executable == "ce" and len(tokens) >= 2 and tokens[1] == "validate-pr":
        return "full_preflight"
    if executable in {"ce-preflight.sh", "ce-preflight"}:
        return "full_preflight"
    if executable in {"carrier-gen", "carrier_gen"}:
        return "carrier_regeneration"
    if _is_python_executable(tokens[0]) and len(tokens) >= 3 and tokens[1] == "-m":
        module = tokens[2]
        if module == "creator_engine_validator.pr_preflight":
            return "full_preflight"
        if module == "creator_engine_validator.carrier_gen":
            return "carrier_regeneration"
        if module == "creator_engine_validator.ce_cli" and len(tokens) >= 4:
            if tokens[3] == "validate-pr":
                return "full_preflight"
        if module == "creator_engine_validator" and len(tokens) >= 4:
            if tokens[3] == "validate-pr":
                return "full_preflight"
    return None


def _tar_extracts(args: tuple[str, ...]) -> bool:
    for arg in args:
        if arg == "--extract" or arg.startswith("--extract="):
            return True
        if arg.startswith("--"):
            continue
        option = arg[1:] if arg.startswith("-") else arg
        if "x" in option:
            return True
    return False


def _classify_bundle_extraction(tokens: tuple[str, ...]) -> str | None:
    if not tokens:
        return None
    executable = PurePosixPath(tokens[0]).name
    if executable in {"tar", "bsdtar", "gtar"} and _tar_extracts(tuple(tokens[1:])):
        return "bundle_extraction"
    if executable == "unzip":
        return "bundle_extraction"
    return None


def classify_execution_plane_primitive(command: Any) -> str | None:
    """Return a #557 execution-plane primitive label, or ``None``.

    This is capability classification, not intent inference: it recognizes the
    repository's concrete primitive surfaces and leaves ordinary coordination
    reads/probes alone.
    """
    if not isinstance(command, str):
        return None
    for segment in _command_segments(command):
        tokens = _strip_env_prefix(segment)
        if not tokens:
            continue
        for classifier in (
            _classify_git_execution_plane,
            _classify_ce_execution_plane,
            _classify_bundle_extraction,
        ):
            primitive = classifier(tokens)
            if primitive is not None:
                return primitive
    return None


# --------------------------------------------------------------------------
# Scope (PreToolUse Edit / Write / MultiEdit)
# --------------------------------------------------------------------------


def _normalize_path(file_path: Any, repo_root: str | None) -> str | None:
    if not isinstance(file_path, str) or not file_path.strip():
        return None
    raw = file_path.strip()
    if raw.startswith("./"):
        raw = raw[2:]
    if repo_root and raw.startswith("/"):
        try:
            return PurePosixPath(raw).relative_to(PurePosixPath(repo_root)).as_posix()
        except ValueError:
            return raw
    return raw


def _path_under(path: str, prefix: str) -> bool:
    prefix = prefix.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def is_in_manifest(path: str, manifest_paths: Iterable[str]) -> bool:
    for entry in manifest_paths:
        entry = entry.strip()
        if not entry:
            continue
        if path == entry:
            return True
        if entry.endswith("/") and _path_under(path, entry):
            return True
        if entry.endswith("/**") and _path_under(path, entry[:-3]):
            return True
        if ("*" in entry or "?" in entry) and PurePosixPath(path).match(entry):
            return True
    return False


def _scope_would_deny(file_path: Any, context: HookContext) -> str | None:
    path = _normalize_path(file_path, context.repo_root)
    if path is None:
        return None
    if context.evidence_root and _path_under(path, context.evidence_root.rstrip("/")):
        return None
    if is_in_manifest(path, context.manifest_paths):
        return None
    return OUT_OF_MANIFEST_REASON


# A reviewer-venue authority envelope authorizes exactly one mechanic + one PR. The
# hook can verify the mechanic and the target PR number from the command; head/actor/
# ratified_prompt_sha are auditable bindings the venue honors (the hook cannot re-derive
# head/actor from the command alone).
_PR_REVIEW_NUMBER_RE = re.compile(r"\bgh\s+pr\s+review\b[^|;&]*?\b([0-9]+)\b")


def _extract_pr_number(command: Any) -> int | None:
    if not isinstance(command, str):
        return None
    match = _PR_REVIEW_NUMBER_RE.search(command)
    if match:
        return int(match.group(1))
    try:
        tokens = _shell_tokens(command)
    except ValueError:
        return None
    for index, token in enumerate(tokens):
        if _is_gh_executable(token) and index + 1 < len(tokens) and tokens[index + 1] == "api":
            parsed = _parse_gh_api_call(tuple(tokens[index + 2 :]))
            if parsed is not None:
                pr_number = _github_review_pr_number(parsed[1])
                if pr_number is not None:
                    return pr_number
        if _is_curl_executable(token):
            parsed = _parse_curl_api_call(tuple(tokens[index + 1 :]))
            if parsed is not None:
                pr_number = _github_review_pr_number(parsed[1])
                if pr_number is not None:
                    return pr_number
    return None


def _authority_covers(envelope: Any, action: str, command: Any) -> bool:
    """True only when a validated reviewer-authority envelope authorizes this exact
    mechanic AND (for pr_review) the command's target PR number. Any other mechanic,
    a wrong PR, or no/invalid envelope ⇒ not covered (deny)."""
    if not isinstance(envelope, dict):
        return False
    rec = envelope.get("reviewer_authority_envelope", envelope)
    if not isinstance(rec, dict):
        return False
    capability = rec.get("capability")
    if capability is not None and str(capability).strip() != REVIEWER_AUTHORITY_CAPABILITY:
        return False
    if str(rec.get("mechanic", "")).strip().lower() != action:
        return False
    if action == "pr_review":
        if _is_raw_gh_api_review_approve(command) or _is_gh_pr_review_approve(command):
            return False
        pr = _extract_pr_number(command)
        return pr is not None and pr == rec.get("pr_number")
    return False


_TOOLCHAIN_SELF_UPDATE_DENY_REASON = (
    "toolchain self-update ({matched}) denied in governed seats; "
    "surface updates are deliberate manifest bumps (surfaces/manifest.yaml) "
    "rolled out canonically — see ce-ops#271 / rented-surface governance"
)

_CONTAINED_OR_FLEET_ENV_MARKERS = frozenset(
    {
        "CE_EGRESS_BROKER_SOCKET",
        "CE_EGRESS_SELF_REVIEW_SOCKET",
        "CE_SEAT_ID",
        "CE_FLEET_ID",
        "CE_FLEET_SCOPE",
        "CE_VPS_CONTAINER_NAME",
        "CE_DGX_CONTAINER_NAME",
        "CE_DGX_CONTROLLER_CONTAINER_NAME",
    }
)


def _mechanics_would_deny(command: Any, context: HookContext) -> str | None:
    action = classify_mechanics(command)
    if action is None:
        return None
    if _authority_covers(context.side_effect_authority, action, command):
        return None
    if action == "toolchain_self_update":
        matched = command.split()[0] if isinstance(command, str) and command.split() else str(command)
        return _TOOLCHAIN_SELF_UPDATE_DENY_REASON.format(matched=matched)
    return (
        f"restricted mechanic ({action}) is denied without a matching ratified "
        "reviewer-venue side-effect-authority envelope (G2.007.2)"
    )


def startup_toolchain_self_update_denied(
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> tuple[bool, str | None]:
    """Return whether CE startup self-update checks are statically off.

    This is the startup-check counterpart to the Ring-1
    ``toolchain_self_update`` deny path: governed posture, contained seats, and
    fleet-marked seats do not perform self-update egress probes.
    """
    source = env if env is not None else os.environ
    for marker in sorted(_CONTAINED_OR_FLEET_ENV_MARKERS):
        if source.get(marker):
            return True, _TOOLCHAIN_SELF_UPDATE_DENY_REASON.format(matched=marker)

    root = Path(cwd) if cwd is not None else Path.cwd()
    ledger_root = source.get("CE_LEDGER_ROOT")
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ce update --check"},
        "cwd": str(root),
    }
    context = build_context(event, posture_root=str(root), ledger_root=ledger_root)
    if context.posture == "governed":
        reason = _mechanics_would_deny("ce update --check", context)
        return True, reason or _TOOLCHAIN_SELF_UPDATE_DENY_REASON.format(matched="ce")
    return False, None


def _secret_would_deny(file_path: Any, context: HookContext) -> str | None:
    category = is_secret_path(file_path)
    if category is None:
        return None
    return f"read of credential-like path denied (matched rule: {category})"


def _mutation_class_from_event(event: dict) -> str:
    ce = event.get("ce") if isinstance(event.get("ce"), dict) else {}
    value = ce.get("mutation_class")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_FOREMAN_MUTATION_CLASS


def _worker_delegation_allows_implementation(context: HookContext) -> bool:
    record = context.worker_delegation
    return (
        isinstance(record, dict)
        and record.get("role") == "implementer"
        and record.get("lane_kind") == "implementation"
        and isinstance(record.get("authenticated_worker_context"), dict)
    )


def _execution_plane_worker_allows(context: HookContext, primitive: str) -> bool:
    record = context.worker_delegation
    if not isinstance(record, dict):
        return False
    key = (str(record.get("role") or ""), str(record.get("lane_kind") or ""))
    if key not in _EXECUTION_PLANE_ALLOWED_WORKERS.get(primitive, frozenset()):
        return False
    return (
        record.get("launch_state") == "launched"
        and isinstance(record.get("authenticated_worker_context"), dict)
    )


def _execution_plane_denial_reason(primitive: str) -> str:
    role = _EXECUTION_PLANE_ROLE_HINTS.get(primitive, "implementer")
    hint = EXECUTION_PLANE_DISPATCH_HINT.format(role=role)
    return (
        f"{EXECUTION_PLANE_DENY_PREFIX} ({primitive}) denied for controller/unpinned "
        f"context; {hint}"
    )


def _execution_plane_would_deny(event: dict, context: HookContext) -> str | None:
    tool = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    primitive: str | None = None
    if tool == "Bash":
        primitive = classify_execution_plane_primitive(tool_input.get("command"))
    elif str(tool).strip().lower() in _SPAWN_TOOL_NAMES:
        primitive = "agent_spawn"
    if primitive is None or _execution_plane_worker_allows(context, primitive):
        return None
    return _execution_plane_denial_reason(primitive)


def _foreman_would_deny(event: dict, context: HookContext) -> str | None:
    tool = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    command = tool_input.get("command") if tool == "Bash" else tool_input.get("file_path")
    if tool == "Bash":
        action = classify_mechanics(command)
        if action is not None and _authority_covers(context.side_effect_authority, action, command):
            return None
    policy = context.seat_class_policy or {}
    prefixes = policy.get("coordination_path_prefixes") if isinstance(policy, dict) else ()
    coordination_prefixes = list(prefixes if isinstance(prefixes, (list, tuple)) else ())
    if context.evidence_root:
        coordination_prefixes.append(context.evidence_root)
    work_class = classify_work_class(
        str(tool),
        command if isinstance(command, str) else None,
        _mutation_class_from_event(event),
        coordination_path_prefixes=coordination_prefixes,
    )
    reason = foreman_would_deny(
        context.seat_class,
        work_class,
        _mutation_class_from_event(event),
        policy,
    )
    if reason is not None and _worker_delegation_allows_implementation(context):
        return None
    return reason


def _resolve_path_ref(ref: str, root: str | None) -> Path:
    path = Path(ref)
    if path.is_absolute() or root is None:
        return path
    return Path(root) / path


def _current_worker_context_from_env(environ: Mapping[str, str] | None = None) -> dict | None:
    source = environ if environ is not None else os.environ
    values: dict[str, str] = {}
    for key, env_name in WORKER_CONTEXT_ENV_KEYS.items():
        raw = source.get(env_name)
        if isinstance(raw, str) and raw.strip():
            values[key] = raw.strip()
    required = {
        "worker_id",
        "record_ref",
        "role",
        "lane_kind",
        "scope_id",
        "seat_id",
        "actor",
        "process_id",
    }
    if not required.issubset(values):
        return None
    try:
        process_id = int(values["process_id"])
        if process_id not in {os.getpid(), os.getppid()}:
            return None
    except ValueError:
        return None
    return values


def _valid_worker_delegation_record(
    path: Path,
    *,
    worker_context: Mapping[str, str],
    posture_root: str | None,
) -> dict | None:
    try:
        from .checks.worker_tier_contract import validate_worker_tier_contract_record
    except Exception:
        return None
    try:
        record = _yaml_safe_load_text(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(record, dict):
        return None
    repo_root = Path(posture_root) if posture_root is not None else None
    if validate_worker_tier_contract_record(record, path, repo_root=repo_root):
        return None
    if record.get("kind") != "ce-worker-spawn-record":
        return None
    if str(record.get("schema_version") or "") != "1":
        return None
    role_lane = (record.get("role"), record.get("lane_kind"))
    allowed = set().union(*_EXECUTION_PLANE_ALLOWED_WORKERS.values())
    if role_lane not in allowed:
        return None
    if role_lane != (worker_context.get("role"), worker_context.get("lane_kind")):
        return None
    if record.get("launch_state") != "launched":
        return None
    record_worker_id = record.get("worker_id")
    if not isinstance(record_worker_id, str) or not record_worker_id:
        return None
    if worker_context.get("worker_id") != record_worker_id:
        return None
    if worker_context.get("scope_id") != record.get("scope_id"):
        return None
    record_path = record.get("record_path")
    if not isinstance(record_path, str) or not record_path:
        return None
    try:
        expected_record = path.expanduser().resolve(strict=False)
        actual_record = Path(record_path).expanduser().resolve(strict=False)
        if actual_record != expected_record:
            return None
    except OSError:
        return None
    worktree_path = record.get("worktree_path")
    if not isinstance(worktree_path, str) or not worktree_path:
        return None
    if posture_root is not None:
        try:
            expected = Path(posture_root).expanduser().resolve(strict=False)
            actual = Path(worktree_path).expanduser().resolve(strict=False)
        except OSError:
            return None
        if actual != expected:
            return None
    record["authenticated_worker_context"] = {
        key: worker_context[key]
        for key in (
            "worker_id",
            "role",
            "lane_kind",
            "scope_id",
            "seat_id",
            "actor",
            "process_id",
        )
    }
    return record


def _resolve_worker_delegation(
    ce: dict,
    posture_root: str | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict | None:
    """Resolve the current launch-pinned worker record, failing closed.

    Worker capability is intentionally not selected by hook-event fields. The
    only accepted selector is the launcher-controlled current-process worker
    context exported in ``CE_WORKER_*`` variables; event-supplied
    ``ce.worker_id`` / ``ce.worker_record_ref`` are ignored so a controller
    cannot replay an authentic worker record.
    """
    del ce
    worker_context = _current_worker_context_from_env(environ)
    if worker_context is None:
        return None
    path = _resolve_path_ref(worker_context["record_ref"], posture_root)
    return _valid_worker_delegation_record(
        path,
        worker_context=worker_context,
        posture_root=posture_root,
    )




# --------------------------------------------------------------------------
# Stop / completion-report closeout
# --------------------------------------------------------------------------

_NO_NEXT_GATE_MARKERS = (
    "no next gate",
    "no-next-gate",
    "no further gate",
    "no next source",
    "no_next_gate",
)


def _closeout_violation(text: str) -> str | None:
    """Return a violation message when ``text`` lacks the canonical terminal
    closeout sections, or ``None`` when satisfied.

    Reuses ``completion_report_terminal_sections`` header detection. The third
    canonical section may be satisfied either by its header or by an explicit
    no-next-gate statement in the body.
    """
    try:
        from .checks.completion_report_terminal_sections import CANONICAL_HEADERS, _header_positions
    except Exception:
        return None

    positions = _header_positions(text)
    present = {header for header, _ in positions}
    missing = [header for header in CANONICAL_HEADERS if header not in present]
    third = CANONICAL_HEADERS[2]
    if third in missing and any(marker in text.lower() for marker in _NO_NEXT_GATE_MARKERS):
        missing = [header for header in missing if header != third]
    if missing:
        return f"closeout missing canonical terminal section(s): {missing!r}"
    return None


def _completion_report_block(report_path: str) -> str | None:
    try:
        from .checks import completion_report_required_for_envelope, completion_report_schema
    except Exception as exc:
        return f"referenced completion report could not be checked: {exc}"

    results = [
        completion_report_schema.run([Path(report_path)]),
        completion_report_required_for_envelope.run([Path(report_path)]),
    ]
    errors = [error for result in results for error in result.errors]
    if not errors:
        return None
    codes = sorted({error.code for error in errors})
    detail = "; ".join(error.format() for error in errors[:3])
    return f"referenced completion report failed checks {codes}: {detail}"


# --------------------------------------------------------------------------
# v3.5-B.3 — the refusal-record spine seam (append-only OBSERVABILITY)
# --------------------------------------------------------------------------
# A governed hard deny (restricted mechanic / secret path — the posture-gated
# deny branch below) additionally appends ONE ``runtime_agent_action``
# record with ``classification: denied`` onto an instance-local refusal chain
# under the hook's own v1 root. Invariants (the gate's heart):
#
# * **Decide first, record after.** The decision is computed and returned
#   exactly as before; recording happens after the verdict exists and changes
#   NO decision semantics. The existing advisory ``observations.ndjson`` stays
#   untouched as the legacy advisory log.
# * **Best-effort, fail-safe.** Recording never raises into the hook path: the
#   deny stands even if the append fails; a failed append never converts a
#   deny into a crash-allow or a crash-block.
# * **Boundary-clean.** The chain discipline rides the SHARED
#   ``runtime_evidence_spine`` (V1->shared); the v3 evidence-persistence sink
#   is never imported (V1->V3 would be the forbidden crossing), so the tiny
#   read-append-write below is the hook's own.

#: The refusal chain lives under the hook's own v1 instance-local root,
#: beside the legacy advisory log (which stays untouched).
_REFUSAL_CHAIN_DIRPARTS = (".hermes", "cc-g-c-hook-observations")
_REFUSAL_CHAIN_FILENAME = "refusal-chain.yaml"

#: The refusal record's policy binding: the hook attests against the SEAT
#: CONTRACT (no runtime-policy record exists on this path), bound as the
#: deterministic, value-free digest of the contract identity.
HOOK_POLICY_SHA = hashlib.sha256(CONTRACT.encode("utf-8")).hexdigest()

#: CC-hook observation tier (mirrors the v3 Tier-B adapter conventions —
#: stamped by this adapter, never the agent; ``pre`` = gated before execution).
_HOOK_FIDELITY = "best_effort"
_HOOK_TIMING = "pre"

#: mechanic -> (op, mutation_class) record axes. A provenance-grade first-cut
#: mirroring the v3 ``runner.cc_hook_adapter`` conventions (``git push`` ->
#: vcs/deploy) — declared inline because v3 modules are not importable here.
_MECHANIC_RECORD_AXES: dict[str, tuple[str, str]] = {
    "merge": ("vcs", "governance"),
    "deploy": ("vcs", "deploy"),
    "publish": ("egress", "deploy"),
    "alter_repo_settings": ("vcs", "governance"),
    "pr_review": ("egress", "governance"),
    "pr_comment": ("egress", "none"),
    "pr_lifecycle": ("egress", "governance"),
    "live_lane_launch": ("exec", "governance"),
    "live_integration_queue": ("exec", "governance"),
    "forge_configure_repo": ("egress", "governance"),
    "forge_ruleset": ("egress", "governance"),
    "forge_review_submit": ("egress", "governance"),
    "forge_auto_merge": ("egress", "governance"),
    "toolchain_self_update": ("exec", "governance"),
    _GIT_OPAQUE_MECHANIC: ("vcs", "governance"),
}

#: Bound the value-free ``target`` provenance field.
_TARGET_MAXLEN = 512


def _refusal_record_body(event: dict, decision: HookDecision) -> dict[str, Any]:
    """Build the denied ``runtime_agent_action`` record body for a governed deny.

    Value-free: ``target``/``tool`` are salient-parameter provenance (the
    attempted command / path), never a credential or secret value — the hook
    never reads file contents on this path.
    """
    tool = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    if tool == "Bash":
        command = tool_input.get("command")
        command = command if isinstance(command, str) else ""
        action = classify_mechanics(command)
        if action is None and decision.reason == FOREMAN_DELEGATION_REASON:
            op, mut_class = "exec", _mutation_class_from_event(event)
        else:
            op, mut_class = _MECHANIC_RECORD_AXES.get(action or "", ("exec", "none"))
        target = command[:_TARGET_MAXLEN]
        first = command.split()[0] if command.split() else "Bash"
        tool_repr = f"Bash:{first}"
    elif tool == "Read":
        file_path = tool_input.get("file_path")
        op, mut_class = "secret", "security"
        target = str(file_path or "")[:_TARGET_MAXLEN]
        tool_repr = "Read"
    elif tool in SCOPE_TOOLS:
        file_path = tool_input.get("file_path")
        op, mut_class = "file", _mutation_class_from_event(event)
        target = str(file_path or "")[:_TARGET_MAXLEN]
        tool_repr = str(tool or "unknown")
    else:  # defensive fallback for future governed hard-deny classes
        op, mut_class = "exec", "none"
        target = ""
        tool_repr = str(tool or "unknown")
    return {
        "kind": _AGENT_ACTION_KIND,
        "record_type": _AGENT_ACTION_TYPE,
        "schema_version": "1",
        "policy_sha": HOOK_POLICY_SHA,
        "run_id": str(event.get("session_id") or "cc-hook"),
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "op": op,
        "mutation_class": mut_class,
        "target": target,
        "tool": tool_repr,
        "fidelity": _HOOK_FIDELITY,
        "timing": _HOOK_TIMING,
        "classification": "denied",
        "decision_mode": "deny",
        "decision_reason": decision.reason,
    }


def _record_refusal(event: dict, context: HookContext, decision: HookDecision) -> None:
    """Best-effort append of a governed deny onto the refusal chain (NEVER raises).

    The tiny read-append-write: load the existing chain document (skip — never
    destroy — an unreadable one), seal the new record via the shared spine
    ``append`` (content-addressed + chain-linked), write the chain document
    back. Any failure returns silently: the deny already stands.
    """
    try:
        root = context.repo_root
        if not root:
            return
        path = Path(root).joinpath(*_REFUSAL_CHAIN_DIRPARTS) / _REFUSAL_CHAIN_FILENAME
        records: list[dict[str, Any]] = []
        if path.exists():
            doc = _yaml_safe_load_text(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                return  # unreadable chain: skip recording, never overwrite evidence
            existing = doc.get("records")
            if not isinstance(existing, list) or not all(isinstance(r, dict) for r in existing):
                return
            records = existing
        sealed = _spine_append(records, _refusal_record_body(event, decision))
        chain_doc = {
            "kind": _SPINE_CHAIN_KIND,
            "record_type": "runtime_evidence_chain",
            "schema_version": "1",
            "records": [*records, sealed],
            "note": (
                "Ring-1 hook refusal chain (v3.5-B.3) — append-only observability; "
                "the deny decision NEVER depends on this file."
            ),
        }
        text = _yaml_safe_dump_document(chain_doc)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except Exception:
        # Best-effort by contract: recording never raises into the hook path.
        return


# --------------------------------------------------------------------------
# Event evaluation
# --------------------------------------------------------------------------


def _pre_tool_use_decision(would_deny_reason: str | None, context: HookContext) -> HookDecision:
    if would_deny_reason is None:
        reason = "permitted under active manifest / mechanics / secret policy"
        return HookDecision(
            ok=True,
            hook_event_name="PreToolUse",
            posture=context.posture,
            decision="allow",
            reason=reason,
            hook_specific_output={
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
            },
        )
    # G-i (v3 kickoff): under governed posture a *path-manifest mismatch* is
    # ADVISORY (allow-with-warning), not a hard deny — author-time scope
    # containment moves to the PR-diff gate (path_manifest_fidelity --base).
    # Secret-path, restricted-mechanic, and foreman-delegation denies are hard
    # denies under governed posture. Branch on the reason so only manifest
    # mismatches are relaxed.
    manifest_mismatch = would_deny_reason == OUT_OF_MANIFEST_REASON
    execution_plane_deny = would_deny_reason.startswith(EXECUTION_PLANE_DENY_PREFIX)
    if (context.posture == "governed" and not manifest_mismatch) or execution_plane_deny:
        return HookDecision(
            ok=True,
            hook_event_name="PreToolUse",
            posture=context.posture,
            decision="deny",
            reason=would_deny_reason,
            would_have_denied=True,
            hook_specific_output={
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": would_deny_reason,
            },
        )
    # Advisory-allow: an ungoverned would-deny of any class, OR a governed
    # path-manifest mismatch (G-i). Still report what would have been denied.
    if manifest_mismatch and context.posture == "governed":
        reason = f"advisory (governed; manifest enforcement is advisory): would deny — {would_deny_reason}"
    else:
        reason = f"advisory (ungoverned): would deny — {would_deny_reason}"
    if context.posture_note:
        reason = f"{reason}; posture-note: {context.posture_note}"
    return HookDecision(
        ok=True,
        hook_event_name="PreToolUse",
        posture=context.posture,
        decision="allow",
        reason=reason,
        advisory=True,
        would_have_denied=True,
        hook_specific_output={
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        },
    )


def _evaluate_pre_tool_use(event: dict, context: HookContext) -> HookDecision:
    tool = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    would_deny_reason = _execution_plane_would_deny(event, context)
    if would_deny_reason is not None:
        return _pre_tool_use_decision(would_deny_reason, context)
    if tool in SCOPE_TOOLS:
        would_deny_reason = _scope_would_deny(tool_input.get("file_path"), context)
    elif tool == "Read":
        would_deny_reason = _secret_would_deny(tool_input.get("file_path"), context)
    elif tool == "Bash":
        would_deny_reason = _mechanics_would_deny(tool_input.get("command"), context)
    if would_deny_reason is None:
        would_deny_reason = _foreman_would_deny(event, context)
    # Other tools have no governed scope/mechanics/secret rule here → allow.
    return _pre_tool_use_decision(would_deny_reason, context)


def _evaluate_stop(event: dict, context: HookContext) -> HookDecision:
    reasons: list[str] = []
    if context.closeout_text is None:
        reasons.append("no closeout text available to verify required terminal sections")
    else:
        violation = _closeout_violation(context.closeout_text)
        if violation:
            reasons.append(violation)
    if context.completion_report_path:
        cr_violation = _completion_report_block(context.completion_report_path)
        if cr_violation:
            reasons.append(cr_violation)
    hso = {"hookEventName": "Stop"}
    if not reasons:
        return HookDecision(
            ok=True,
            hook_event_name="Stop",
            posture=context.posture,
            decision="allow",
            reason="closeout satisfies the terminal-section contract",
            hook_specific_output=hso,
        )
    reason = "; ".join(reasons)
    if context.posture == "governed":
        return HookDecision(
            ok=True,
            hook_event_name="Stop",
            posture=context.posture,
            decision="block",
            reason=reason,
            would_have_denied=True,
            hook_specific_output=hso,
        )
    return HookDecision(
        ok=True,
        hook_event_name="Stop",
        posture=context.posture,
        decision="allow",
        reason=f"advisory (ungoverned): would block — {reason}",
        advisory=True,
        would_have_denied=True,
        hook_specific_output=hso,
    )


def evaluate(event: dict, context: HookContext) -> HookDecision:
    """Evaluate one Claude hook event against the resolved context."""
    name = event.get("hook_event_name") or event.get("hookEventName") or ""
    if name == "PreToolUse":
        decision = _evaluate_pre_tool_use(event, context)
        if decision.decision == "deny":
            # v3.5-B.3: decide FIRST, record AFTER. Governed hard denies reach
            # decision=="deny"; governed manifest mismatch remains
            # advisory-allow under G-i. Recording is best-effort — the deny
            # above stands regardless.
            _record_refusal(event, context, decision)
        return decision
    if name == "Stop":
        return _evaluate_stop(event, context)
    return HookDecision(
        ok=True,
        hook_event_name=name,
        posture=context.posture,
        decision="allow",
        reason=f"no governed rule for hook event {name!r}",
        hook_specific_output={"hookEventName": name},
    )


# --------------------------------------------------------------------------
# Context resolution (CLI / canonical hook path)
# --------------------------------------------------------------------------


def _posture_discovery_root(
    ledger_root: str | None, posture_root: str | None
) -> Path | None:
    """Resolve the directory under which the §7 posture claims+panes are discovered.

    Gate B (posture-claim reachability): a governed seat's REAL Active-Work Ledger is
    launch-pinned via ``--ledger-root`` (exported by ``ce lane launch`` as
    ``CE_LEDGER_ROOT`` — the analog of the proven ``reviewer-authority-ref`` seam).
    When pinned we discover under it, so a worktree seat — whose own tree carries no
    real ledger — resolves ``governed`` from its real claim, not a fixture.

    Otherwise we discover under ``<posture_root>/.hermes/active-work-ledger`` — **never
    the whole posture-root tree** — so tracked ``examples/**`` claim/pane fixtures (and
    snapshot copies) can never be matched as governing claims. ``None`` when neither a
    ledger nor a posture root is resolvable (caller falls to ``ungoverned``).
    """
    if ledger_root:
        return Path(ledger_root)
    if posture_root:
        return Path(posture_root) / ".hermes" / "active-work-ledger"
    return None


def _resolve_posture(
    ce: dict,
    posture_mode: str,
    posture_root: str | None,
    ledger_root: str | None = None,
):
    if posture_mode in {"governed", "ungoverned"}:
        return posture_mode, None
    explicit = ce.get("posture")
    if explicit in {"governed", "ungoverned"}:
        return explicit, None
    discovery_root = _posture_discovery_root(ledger_root, posture_root)
    if discovery_root is None or not discovery_root.is_dir():
        # No pinned ledger and no live ledger under the posture root → an
        # unallocated / unpinned seat. Fail to ungoverned (advisory floor); a
        # tracked examples/** fixture can no longer flip it to governed.
        return "ungoverned", None
    try:
        from .checks.pane_registry import evaluate_posture
    except Exception:
        return "ungoverned", None

    result = evaluate_posture([discovery_root])
    return result.posture, result.claim


def _resolve_manifest(manifest_doc, ce, posture_root, bound_claim) -> ResolvedManifest:
    if manifest_doc:
        paths = _extract_manifest_paths_from_file(Path(manifest_doc))
        if paths:
            return ResolvedManifest(tuple(paths))
    ce_paths = ce.get("manifest_paths")
    if isinstance(ce_paths, list):
        return ResolvedManifest(tuple(str(p) for p in ce_paths))
    if bound_claim is not None and posture_root:
        envelope_ref = bound_claim.record.get("envelope_ref")
        if envelope_ref == "none":
            return ResolvedManifest((), NO_WRITE_AUTHORITY_NOTE)
        if isinstance(envelope_ref, str) and envelope_ref:
            for candidate in (Path(posture_root) / envelope_ref, Path(envelope_ref)):
                if candidate.is_file():
                    paths = _extract_manifest_paths_from_file(candidate)
                    if paths:
                        return ResolvedManifest(tuple(paths))
    return ResolvedManifest()


def _resolve_side_effect_authority(ce: dict, posture_root: str | None) -> dict | None:
    """Resolve a validated, bounded reviewer-venue authority envelope record, or None.

    Accepts an inline ``ce.reviewer_authority`` mapping or a ``ce.reviewer_authority_ref``
    path (resolved under ``posture_root``). A raw loose token is NOT honored — only a
    schema-valid ``reviewer_authority_envelope`` is. Fail-closed: any load/validation
    problem yields ``None`` (no authority).
    """
    try:
        from .checks.reviewer_authority_envelope import (
            KEY as _RVA_KEY,
            validate_reviewer_authority_envelope_record,
        )
        from .loader import LoaderError, load_yaml
    except Exception:
        return None

    candidate: Any = None
    inline = ce.get("reviewer_authority")
    if isinstance(inline, dict):
        candidate = inline if _RVA_KEY in inline else {_RVA_KEY: inline}
    else:
        ref = ce.get("reviewer_authority_ref")
        if isinstance(ref, str) and ref:
            search = [Path(posture_root) / ref, Path(ref)] if posture_root else [Path(ref)]
            for path in search:
                if path.is_file():
                    try:
                        candidate = load_yaml(path)
                    except LoaderError:
                        candidate = None
                    break
    if not isinstance(candidate, dict):
        return None
    if validate_reviewer_authority_envelope_record(candidate, Path(posture_root or ".")):
        return None
    rec = candidate.get(_RVA_KEY)
    return rec if isinstance(rec, dict) else None


def _resolve_seat_class_policy(ce: dict, posture_root: str | None) -> dict | None:
    """Resolve inline ``ce.seat_class_policy`` or ``ce.seat_class_policy_ref``.

    Runtime resolution deliberately avoids adding schema coupling here.
    Invalid/missing refs fail closed by returning no policy; the pure helper
    then uses its default required mutation classes.
    """
    from .loader import LoaderError, load_yaml

    inline = ce.get("seat_class_policy")
    if isinstance(inline, dict):
        return inline
    ref = ce.get("seat_class_policy_ref")
    if not isinstance(ref, str) or not ref:
        return None
    search = [Path(posture_root) / ref, Path(ref)] if posture_root else [Path(ref)]
    for path in search:
        if not path.is_file():
            continue
        try:
            candidate = load_yaml(path)
        except LoaderError:
            return None
        return candidate if isinstance(candidate, dict) else None
    return None


def build_context(
    event: dict,
    *,
    posture: str = "auto",
    posture_root: str | None = None,
    ledger_root: str | None = None,
    manifest_doc: str | None = None,
    evidence_root: str | None = None,
    closeout_file: str | None = None,
    completion_report: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> HookContext:
    """Build a :class:`HookContext` from a hook event plus optional overrides.

    Resolution precedence: explicit override flags > the event's ``ce``
    extension block > auto-resolution from ``.hermes`` posture inputs.

    ``ledger_root`` is the launch-pinned absolute Active-Work Ledger root (Gate B).
    When present it scopes the §7 posture claim/pane discovery to the seat's real
    ledger; otherwise discovery is scoped to ``<posture_root>/.hermes/active-work-ledger``.
    """
    ce = event.get("ce") if isinstance(event.get("ce"), dict) else {}
    posture_root = posture_root or ce.get("posture_root") or event.get("cwd")
    ledger_root = ledger_root or ce.get("ledger_root")
    posture_value, bound_claim = _resolve_posture(ce, posture, posture_root, ledger_root)
    manifest = _resolve_manifest(manifest_doc, ce, posture_root, bound_claim)
    evidence_root = evidence_root or ce.get("evidence_root")
    completion_report = completion_report or ce.get("completion_report")
    side_effect_authority = _resolve_side_effect_authority(ce, posture_root)
    seat_class_policy = _resolve_seat_class_policy(ce, posture_root)
    policy_seat_class = seat_class_policy.get("seat_class") if isinstance(seat_class_policy, dict) else None
    seat_class = resolve_seat_class(ce.get("seat_class") or policy_seat_class)
    worker_delegation = _resolve_worker_delegation(ce, posture_root, environ=environ)

    closeout_text = ce.get("closeout_text")
    if closeout_file:
        try:
            closeout_text = Path(closeout_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            closeout_text = None

    return HookContext(
        posture=posture_value,
        manifest_paths=manifest.paths,
        evidence_root=evidence_root,
        closeout_text=closeout_text,
        completion_report_path=completion_report,
        side_effect_authority=side_effect_authority,
        seat_class=seat_class,
        seat_class_policy=seat_class_policy,
        worker_delegation=worker_delegation,
        repo_root=posture_root,
        posture_note=manifest.posture_note,
    )
