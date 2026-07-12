"""CC-G-D Ring 0 — pure Claude launch-spec evaluator + governed command builder.

This module is the HARD Ring 0 launch/accept refusal surface for governed
Claude Code lanes. It mirrors :mod:`environment_guard`: it is **pure and
offline** — it parses a requested ``claude`` argv into a :class:`ClaudeLaunchSpec`,
returns fail-closed :class:`LaunchRefusal` clauses for every prohibited surface
(seat contract §5), and builds a governed command that pins
``--setting-sources project`` and strict MCP. It spawns no process, reads no
file, makes no network call, and launches no MCP server (config-posture only).

Enforcement-strength framing (seat contract §3, §8.2): the refusals here are the
**HARD** Ring 0 kernel boundary — refused before any side effect, not talkable
around in-band. The committed Claude hook-pack (Ring 1) remains RUNTIME /
DEFEASIBLE and is **not** strengthened to HARD by this module.

Clause identifiers are stable and namespaced ``CC-D-*``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# Clause identifiers (CC-G-D Ring 0 launch refusals). Stable, namespaced.
CLAUSE_BARE = "CC-D-1"  # --bare
CLAUSE_PRINT = "CC-D-2"  # -p / --print (headless) for a governed authoring lane
CLAUSE_AGENTS = "CC-D-3"  # background `agents` subcommand / --agents
CLAUSE_REMOTE_CONTROL = "CC-D-4"  # --remote-control / remoteControlAtStartup
CLAUSE_LOCAL_SETTINGS = "CC-D-5"  # settings.local.json weakening / --setting-sources w/o project
CLAUSE_SKIP_PERMS = "CC-D-6"  # --dangerously-skip-permissions without a confirmed hook-pack
CLAUSE_MCP = "CC-D-7"  # uncontrolled/global MCP inheritance (no strict/owned config)

PROHIBITED_ALWAYS = frozenset(
    {CLAUSE_BARE, CLAUSE_AGENTS, CLAUSE_REMOTE_CONTROL, CLAUSE_LOCAL_SETTINGS}
)

# Flags that consume the following token as their value (``--flag value`` form).
_VALUE_FLAGS = frozenset({"--setting-sources", "--mcp-config"})


class GovernedCommandError(ValueError):
    """Raised when a governed command cannot be built without violating posture."""


@dataclass(frozen=True)
class ClaudeLaunchSpec:
    """Parsed view of a requested Claude launch. Pure data; no side effects."""

    argv: tuple[str, ...]  # the requested claude args (excluding the harness token)
    setting_sources: tuple[str, ...] | None = None  # parsed value of --setting-sources, else None
    mcp_config_path: str | None = None  # value of --mcp-config, else None
    strict_mcp: bool = False  # --strict-mcp-config present
    skip_permissions: bool = False  # --dangerously-skip-permissions present


@dataclass(frozen=True)
class LaunchRefusal:
    clause: str
    surface: str  # the offending flag/mode token, e.g. "--bare"
    detail: str

    def to_dict(self) -> dict:
        return {"clause": self.clause, "surface": self.surface, "detail": self.detail}


@dataclass(frozen=True)
class LaunchSpecResult:
    refusals: tuple[LaunchRefusal, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.refusals

    def to_dict(self) -> dict:
        return {"ok": self.ok, "refusals": [r.to_dict() for r in self.refusals]}


def parse_claude_argv(argv: Sequence[str]) -> ClaudeLaunchSpec:
    """Parse a requested ``claude`` argv into a :class:`ClaudeLaunchSpec`.

    Handles both ``--flag value`` and ``--flag=value`` forms. ``--setting-sources``
    is comma-split into a tuple. This is a *lenient* parser: unknown tokens are
    preserved verbatim in ``argv`` and otherwise ignored (the evaluator, not the
    parser, decides what is prohibited).
    """
    tokens = list(argv)
    setting_sources: tuple[str, ...] | None = None
    mcp_config_path: str | None = None
    strict_mcp = False
    skip_permissions = False

    i = 0
    while i < len(tokens):
        token = tokens[i]
        name, sep, inline_value = token.partition("=")

        def _value() -> str | None:
            if sep:
                return inline_value
            if i + 1 < len(tokens):
                return tokens[i + 1]
            return None

        if name == "--setting-sources":
            raw = _value()
            if raw is not None:
                setting_sources = tuple(part for part in raw.split(",") if part != "")
            if not sep:
                i += 1
        elif name == "--mcp-config":
            raw = _value()
            if raw is not None:
                mcp_config_path = raw
            if not sep:
                i += 1
        elif name == "--strict-mcp-config":
            strict_mcp = True
        elif name == "--dangerously-skip-permissions":
            skip_permissions = True
        i += 1

    return ClaudeLaunchSpec(
        argv=tuple(tokens),
        setting_sources=setting_sources,
        mcp_config_path=mcp_config_path,
        strict_mcp=strict_mcp,
        skip_permissions=skip_permissions,
    )


def evaluate_claude_launch(
    spec: ClaudeLaunchSpec,
    *,
    hook_pack_confirmed: bool,
    governed_authoring_lane: bool = True,
) -> LaunchSpecResult:
    """Fail-closed: return one :class:`LaunchRefusal` per prohibited surface present.

    The refusals encode the seat-contract §5 prohibitions as the HARD Ring 0
    boundary. ``--print`` is refused only for a governed authoring lane (read-only
    scripted ``ce`` checks may use it — but those never go through this builder).
    ``--dangerously-skip-permissions`` is permitted only when the hook-pack is
    confirmed loaded (``hook_pack_confirmed``).
    """
    refusals: list[LaunchRefusal] = []
    argv = spec.argv

    # CC-D-1 — --bare defeats the entire enforcement layer.
    if "--bare" in argv:
        refusals.append(
            LaunchRefusal(CLAUSE_BARE, "--bare", "--bare skips hooks/settings/CLAUDE.md discovery")
        )

    # CC-D-2 — -p/--print headless mode for a governed authoring lane.
    if governed_authoring_lane:
        for token in ("-p", "--print"):
            if token in argv:
                refusals.append(
                    LaunchRefusal(
                        CLAUSE_PRINT,
                        token,
                        "headless print mode is not the visible, archivable pane a governed lane requires",
                    )
                )

    # CC-D-3 — background `agents` subcommand (first token) or --agents.
    if argv and argv[0] == "agents":
        refusals.append(
            LaunchRefusal(CLAUSE_AGENTS, "agents", "background `agents` subcommand is invisible/unarchivable")
        )
    if "--agents" in argv:
        refusals.append(
            LaunchRefusal(CLAUSE_AGENTS, "--agents", "background `--agents` sessions are invisible/unarchivable")
        )

    # CC-D-4 — --remote-control / remoteControlAtStartup external channel.
    for token in ("--remote-control", "--remote-control-at-startup"):
        if token in argv:
            refusals.append(
                LaunchRefusal(
                    CLAUSE_REMOTE_CONTROL, token, "remote control is outside the visible/archived model"
                )
            )
    if any("remoteControlAtStartup" in t for t in argv):
        refusals.append(
            LaunchRefusal(
                CLAUSE_REMOTE_CONTROL,
                "remoteControlAtStartup",
                "remoteControlAtStartup is outside the visible/archived model",
            )
        )

    # CC-D-5 — settings.local.json weakening / --setting-sources excluding project.
    if spec.setting_sources is not None:
        sources = spec.setting_sources
        if "local" in sources or "project" not in sources:
            refusals.append(
                LaunchRefusal(
                    CLAUSE_LOCAL_SETTINGS,
                    "--setting-sources",
                    "governed launches must pin --setting-sources to include project and exclude local",
                )
            )
    if any(_points_at_local_settings(t) for t in argv):
        refusals.append(
            LaunchRefusal(
                CLAUSE_LOCAL_SETTINGS,
                "settings.local.json",
                "settings.local.json can silently weaken the committed hook-pack",
            )
        )

    # CC-D-6 — --dangerously-skip-permissions without a confirmed hook-pack.
    if spec.skip_permissions and not hook_pack_confirmed:
        refusals.append(
            LaunchRefusal(
                CLAUSE_SKIP_PERMS,
                "--dangerously-skip-permissions",
                "skip-permissions is safe only once Ring 0 confirms the hook-pack is loaded",
            )
        )

    # CC-D-7 — uncontrolled / global MCP inheritance. Config-posture only.
    if spec.mcp_config_path is not None:
        if not spec.strict_mcp:
            refusals.append(
                LaunchRefusal(
                    CLAUSE_MCP,
                    "--mcp-config",
                    "MCP config supplied without --strict-mcp-config; global/user servers would be inherited",
                )
            )
        elif not _is_ce_owned_mcp_path(spec.mcp_config_path):
            refusals.append(
                LaunchRefusal(
                    CLAUSE_MCP,
                    "--mcp-config",
                    f"MCP config {spec.mcp_config_path!r} is not a CE-owned path inside the repo / .hermes",
                )
            )

    return LaunchSpecResult(refusals=tuple(refusals))


def _points_at_local_settings(token: str) -> bool:
    """True when an ``--add-dir``/``--settings`` value names ``settings.local.json``."""
    _, _, value = token.partition("=")
    return "settings.local.json" in (value or token)


def _is_ce_owned_mcp_path(path: str) -> bool:
    """True when ``path`` is a CE-owned MCP config inside the repo / ``.hermes``.

    Pure/offline: a CE-owned path is a *relative* path that does not escape the
    tree (no leading ``/``, no ``..`` component). Absolute or escaping paths are
    treated as uncontrolled/global and refused.
    """
    if not path or path.startswith("/") or path.startswith("~"):
        return False
    parts = path.replace("\\", "/").split("/")
    return ".." not in parts


# Flags this builder owns: they are stripped from ``base_argv`` and re-injected
# canonically so the governed command can never carry a conflicting/duplicate copy.
_BUILDER_OWNED_VALUE_FLAGS = frozenset({"--setting-sources", "--mcp-config"})
_BUILDER_OWNED_BARE_FLAGS = frozenset({"--strict-mcp-config"})

# Claude's session selectors determine whether a new invocation resumes the
# latest conversation, selects one interactively, or targets an explicit ID.
# CE's default is ``--continue``; preserve a caller's explicit selection rather
# than adding a contradictory second selector.
_SESSION_SELECTION_FLAGS = frozenset({"--continue", "-c", "--resume", "-r", "--session-id"})


def _has_session_selection(tokens: Sequence[str]) -> bool:
    """Return true when the caller supplied any Claude session-selection flag."""
    for token in tokens:
        name, _sep, _value = token.partition("=")
        if name in _SESSION_SELECTION_FLAGS:
            return True
    return False


def build_governed_claude_command(
    *,
    base_argv: Sequence[str] | None,
    mcp_config_path: str,
    closeout_file: str | None = None,
    completion_report_ref: str | None = None,
) -> list[str]:
    """Return the safe ``claude ...`` argv with the governed posture pinned.

    Injects ``--setting-sources project``, ``--strict-mcp-config``, and
    ``--mcp-config <ce-path>``. The CE closeout pointers (``closeout_file`` /
    ``completion_report_ref``) are exported via the lane *environment* by the
    runtime — **never** as claude flags — so they are intentionally not emitted
    here. Idempotent: a clean ``--setting-sources project`` in ``base_argv`` is
    canonicalized, and a conflicting one (excluding ``project`` or including
    ``local``) raises :class:`GovernedCommandError` rather than producing a
    duplicate/contradictory flag.
    """
    base = list(base_argv or [])
    base_spec = parse_claude_argv(base)
    if base_spec.setting_sources is not None:
        sources = base_spec.setting_sources
        if "local" in sources or "project" not in sources:
            raise GovernedCommandError(
                "refusing to build governed command: base argv pins --setting-sources "
                f"{sources!r} which excludes 'project' or includes 'local'"
            )
    if not _is_ce_owned_mcp_path(mcp_config_path):
        raise GovernedCommandError(
            f"refusing to build governed command: MCP config {mcp_config_path!r} "
            "is not a CE-owned path inside the repo / .hermes"
        )

    passthrough = _strip_builder_owned_flags(base)
    # Extra Claude arguments are independent of default resume behavior. Only a
    # real session selector supplied by the caller suppresses the default.
    if not _has_session_selection(passthrough):
        passthrough.append("--continue")
    command = ["claude", *passthrough]
    command += ["--setting-sources", "project"]
    command += ["--strict-mcp-config", "--mcp-config", mcp_config_path]
    return command


def _strip_builder_owned_flags(tokens: Sequence[str]) -> list[str]:
    """Drop builder-owned flags (and their values) from ``tokens``."""
    out: list[str] = []
    i = 0
    toks = list(tokens)
    while i < len(toks):
        name, sep, _ = toks[i].partition("=")
        if name in _BUILDER_OWNED_VALUE_FLAGS:
            if not sep:
                i += 1  # also skip the value token
        elif name in _BUILDER_OWNED_BARE_FLAGS:
            pass
        else:
            out.append(toks[i])
        i += 1
    return out
