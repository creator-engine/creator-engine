"""CDX-D Ring 0 — pure Codex launch-spec evaluator + governed command builder.

This module is deliberately narrower than the Claude launch-spec. It does not
claim a Codex Ring-1 hook-pack. It refuses obvious posture-defeating Codex
surfaces before tmux spawn and builds the command through an environment scrub
that removes common ambient repo-write credentials.

Clause identifiers are stable and namespaced ``CDX-D-*``.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

CLAUSE_HEADLESS = "CDX-D-1"
CLAUSE_REMOTE = "CDX-D-2"
CLAUSE_TRANSCRIPT = "CDX-D-3"
CLAUSE_POSTURE_BYPASS = "CDX-D-4"
CLAUSE_ADD_DIR = "CDX-D-5"
CLAUSE_BYPASS_MODE = "CDX-D-6"
CLAUSE_ARG_ALLOWLIST = "CDX-D-7"

HEADLESS_SUBCOMMANDS = frozenset(
    {"exec", "review", "mcp-server", "exec-server", "app-server", "apply"}
)
REMOTE_TOKEN_FLAGS = frozenset(
    {
        "--remote-token",
        "--remote-auth-token",
        "--remote-api-token",
        "--codex-remote-token",
    }
)
POSTURE_BYPASS_FLAGS = frozenset(
    {"--dangerously-bypass-hook-trust", "--ignore-rules", "--ignore-user-config"}
)
BYPASS_FLAG = "--dangerously-bypass-approvals-and-sandbox"
CREDENTIAL_ENV_UNSETS = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "GITHUB_API_URL",
    "GH_HOST",
    "GH_CONFIG_DIR",
    "GH_DEBUG",
)

_VALUE_FLAGS = frozenset({"--model", "-m", "--reasoning-effort", "--effort", "--add-dir"})
_SAFE_VALUE_FLAGS = frozenset({"--model", "-m", "--reasoning-effort", "--effort"})
_SAFE_BOOL_FLAGS = frozenset({BYPASS_FLAG})


class GovernedCommandError(ValueError):
    """Raised when a governed Codex command cannot be built safely."""


@dataclass(frozen=True)
class CodexLaunchSpec:
    """Parsed view of requested Codex args, excluding the ``codex`` token."""

    argv: tuple[str, ...]
    add_dirs: tuple[str, ...] = ()
    explicit_bypass: bool = False


@dataclass(frozen=True)
class LaunchRefusal:
    clause: str
    surface: str
    detail: str

    def to_dict(self) -> dict:
        return {"clause": self.clause, "surface": self.surface, "detail": self.detail}


@dataclass(frozen=True)
class LaunchSpecResult:
    refusals: tuple[LaunchRefusal, ...] = ()
    bypass_mode: str | None = None

    @property
    def ok(self) -> bool:
        return not self.refusals

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "bypass_mode": self.bypass_mode,
            "refusals": [r.to_dict() for r in self.refusals],
        }


def parse_codex_argv(argv: Sequence[str]) -> CodexLaunchSpec:
    """Parse requested ``codex`` args leniently for the Ring-0 evaluator."""
    tokens = list(argv)
    add_dirs: list[str] = []
    explicit_bypass = False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        name, sep, inline_value = token.partition("=")
        if token == BYPASS_FLAG:
            explicit_bypass = True
        if name == "--add-dir":
            if sep:
                add_dirs.append(inline_value)
            elif i + 1 < len(tokens):
                add_dirs.append(tokens[i + 1])
                i += 1
        elif name in _VALUE_FLAGS and not sep:
            i += 1
        i += 1
    return CodexLaunchSpec(
        argv=tuple(tokens),
        add_dirs=tuple(add_dirs),
        explicit_bypass=explicit_bypass,
    )


def detect_config_bypass_mode(config_path: Path | str | None = None) -> str | None:
    """Return ``"config"`` only when the live Codex config declares bypass posture."""
    path = Path(config_path) if config_path is not None else Path.home() / ".codex" / "config.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    if data.get("approval_policy") == "never" and data.get("sandbox_mode") == "danger-full-access":
        return "config"
    return None


def evaluate_codex_launch(
    spec: CodexLaunchSpec,
    *,
    allowed_root: Path | str,
    config_bypass_mode: str | None,
) -> LaunchSpecResult:
    """Fail closed for prohibited Codex authoring-seat launch surfaces."""
    refusals: list[LaunchRefusal] = []
    argv = spec.argv
    allowed = Path(allowed_root).resolve()

    if argv and argv[0] in HEADLESS_SUBCOMMANDS:
        refusals.append(
            LaunchRefusal(
                CLAUSE_HEADLESS,
                argv[0],
                "non-interactive/headless Codex subcommands are not governed authoring seats",
            )
        )

    if "remote-control" in argv:
        refusals.append(
            LaunchRefusal(CLAUSE_REMOTE, "remote-control", "remote-control is outside the visible seat")
        )
    for token in argv:
        name = token.partition("=")[0]
        if name == "--remote" or name in REMOTE_TOKEN_FLAGS:
            refusals.append(
                LaunchRefusal(CLAUSE_REMOTE, name, "remote surfaces and remote auth tokens are refused")
            )

    if "--ephemeral" in argv:
        refusals.append(
            LaunchRefusal(CLAUSE_TRANSCRIPT, "--ephemeral", "ephemeral mode disables durable transcript identity")
        )

    for token in argv:
        name = token.partition("=")[0]
        if name in POSTURE_BYPASS_FLAGS:
            refusals.append(
                LaunchRefusal(
                    CLAUSE_POSTURE_BYPASS,
                    name,
                    "trust/posture bypass surfaces are not ratified by G1-codex",
                )
            )

    for raw in spec.add_dirs:
        try:
            target = Path(raw).expanduser()
            if not target.is_absolute():
                target = allowed / target
            target.resolve().relative_to(allowed)
        except (OSError, ValueError):
            refusals.append(
                LaunchRefusal(
                    CLAUSE_ADD_DIR,
                    "--add-dir",
                    f"writable-scope expansion {raw!r} is outside the declared worktree root",
                )
            )

    for i, token in enumerate(argv):
        name, sep, _value = token.partition("=")
        if name in _SAFE_BOOL_FLAGS:
            continue
        if name in _SAFE_VALUE_FLAGS:
            continue
        if name == "--add-dir":
            continue
        if i > 0 and argv[i - 1].partition("=")[0] in _VALUE_FLAGS and "=" not in argv[i - 1]:
            continue
        if token.startswith("-"):
            refusals.append(
                LaunchRefusal(
                    CLAUSE_ARG_ALLOWLIST,
                    name,
                    "Codex harness args are allowlisted; this launch arg is not permitted by G1-codex",
                )
            )

    bypass_mode = "argv" if spec.explicit_bypass else config_bypass_mode
    if bypass_mode not in {"argv", "config"}:
        refusals.append(
            LaunchRefusal(
                CLAUSE_BYPASS_MODE,
                "codex_bypass_mode",
                "Codex bypass mode must be explicit in argv or verified from ~/.codex/config.toml",
            )
        )

    return LaunchSpecResult(refusals=tuple(refusals), bypass_mode=bypass_mode)


def build_governed_codex_command(base_argv: Sequence[str]) -> list[str]:
    """Build the governed Codex command with ambient repo-write credentials scrubbed."""
    return [
        "env",
        *(part for name in CREDENTIAL_ENV_UNSETS for part in ("-u", name)),
        "codex",
        *list(base_argv),
    ]
