"""CE Ring 0 Hermes harness governance — parallel in spirit to ``claude_launch_spec``.

This module pins the Creator-Engine Hermes profile and refuses prohibited Hermes
launch surfaces *before any side effect*. It is pure/offline: it parses argv, makes a
decision, and builds a governed command. It spawns no process and reads no network.

Reality notes (verified against ``hermes --help`` / ``hermes profile`` on this host,
Hermes Agent v0.14.0):

* ``--profile <name>`` is an accepted top-level flag; ``creator-engine`` is a real
  profile. The governed command pins ``--profile creator-engine`` (visible in the
  dry-run plan), and any attempt to override it (a different ``--profile`` value or a
  leading ``profile`` management subcommand) is refused.
* Hermes has **no** ``--strict-mcp-config`` equivalent, so none is invented here; the
  residual MCP/tool-scoping gap is recorded honestly in the gate closeout.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

CANONICAL_PROFILE = "creator-engine"

# Refusal clauses (HM-D-*) — the Hermes analogue of the Claude CC-D-* clause set.
CLAUSE_PROFILE_OVERRIDE = "HM-D-1"  # override the pinned creator-engine profile
CLAUSE_YOLO = "HM-D-2"              # --yolo approval bypass
CLAUSE_RESUME = "HM-D-3"            # --resume / -r resumed (hidden) session state
CLAUSE_CONTINUE = "HM-D-4"          # --continue / -c resumed-by-name session state
CLAUSE_ACCEPT_HOOKS = "HM-D-5"      # --accept-hooks auto-approve unseen shell hooks
CLAUSE_IGNORE_CONFIG = "HM-D-6"     # --ignore-user-config / --ignore-rules weakening


class GovernedCommandError(ValueError):
    """Raised when a governed Hermes command cannot be built."""


@dataclass(frozen=True)
class HermesLaunchSpec:
    profile_override: bool = False
    yolo: bool = False
    resume: bool = False
    continue_: bool = False
    accept_hooks: bool = False
    ignore_config: bool = False


@dataclass(frozen=True)
class HermesLaunchRefusal:
    clause: str
    surface: str
    detail: str


@dataclass(frozen=True)
class HermesLaunchResult:
    ok: bool
    refusals: tuple[HermesLaunchRefusal, ...]


# Unsafe long options → the spec field they set. Detection is by argparse-style
# *prefix abbreviation* (e.g. ``--res`` → ``--resume``), so a short prefix of any of
# these is refused conservatively. None of these share a prefix with a *safe* long
# option, so blanket prefix matching here has no false positives.
_UNSAFE_LONG = {
    "--yolo": "yolo",
    "--resume": "resume",
    "--continue": "continue_",
    "--accept-hooks": "accept_hooks",
    "--ignore-user-config": "ignore_config",
    "--ignore-rules": "ignore_config",
}
# Safe long options that share a leading prefix with ``--profile`` (``--p``/``--pr``/
# ``--pro``). A profile-targeting abbreviation that is *also* a prefix of one of these
# is ambiguous (argparse would reject it), so it is not treated as a profile override.
_PROFILE_AMBIGUOUS_SAFE = ("--provider", "--pass-session-id")
_MIN_ABBREV = 3  # "--" + at least one char


def parse_hermes_argv(argv: Sequence[str]) -> HermesLaunchSpec:
    """Parse Hermes launch argv into a governance spec.

    Conservative against argparse abbreviations and concatenated short options:
    a ``--`` token that is a non-empty prefix of an unsafe long option is refused,
    and ``-r``/``-c`` (incl. concatenated ``-rVALUE``/``-cVALUE``) are resume/continue.
    """
    tokens = list(argv)
    profile_override = False
    flags = {"yolo": False, "resume": False, "continue_": False, "accept_hooks": False, "ignore_config": False}

    # A leading `profile` management subcommand changes/overrides the active profile.
    if tokens and tokens[0] == "profile":
        profile_override = True

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            name = tok.partition("=")[0]
            _, sep, inline = tok.partition("=")
            # profile override (abbreviation-aware, ambiguity-guarded)
            if (
                len(name) >= _MIN_ABBREV
                and "--profile".startswith(name)
                and not any(safe.startswith(name) for safe in _PROFILE_AMBIGUOUS_SAFE)
            ):
                value = inline if sep else (tokens[i + 1] if i + 1 < len(tokens) else "")
                if value.strip() != CANONICAL_PROFILE:
                    profile_override = True
            else:
                # unsafe long option, matched by prefix abbreviation
                for opt, field in _UNSAFE_LONG.items():
                    if len(name) >= _MIN_ABBREV and opt.startswith(name):
                        flags[field] = True
        elif tok.startswith("-") and len(tok) >= 2:
            # short options, incl. concatenated forms like -rabc / -cabc
            if tok[1] == "r":
                flags["resume"] = True
            elif tok[1] == "c":
                flags["continue_"] = True
        i += 1

    return HermesLaunchSpec(
        profile_override=profile_override,
        yolo=flags["yolo"],
        resume=flags["resume"],
        continue_=flags["continue_"],
        accept_hooks=flags["accept_hooks"],
        ignore_config=flags["ignore_config"],
    )


def evaluate_hermes_launch(spec: HermesLaunchSpec) -> HermesLaunchResult:
    """Refuse prohibited Hermes surfaces; all refusals are before any side effect."""
    refusals: list[HermesLaunchRefusal] = []
    if spec.profile_override:
        refusals.append(
            HermesLaunchRefusal(
                CLAUSE_PROFILE_OVERRIDE,
                "--profile",
                f"governed Hermes launches pin --profile {CANONICAL_PROFILE!r}; "
                "overriding the profile (flag value or `profile` subcommand) is refused",
            )
        )
    if spec.yolo:
        refusals.append(
            HermesLaunchRefusal(CLAUSE_YOLO, "--yolo", "approval-bypass launch is refused")
        )
    if spec.resume:
        refusals.append(
            HermesLaunchRefusal(
                CLAUSE_RESUME, "--resume", "resuming a hidden prior session is refused"
            )
        )
    if spec.continue_:
        refusals.append(
            HermesLaunchRefusal(
                CLAUSE_CONTINUE, "--continue", "continuing a hidden prior session is refused"
            )
        )
    if spec.accept_hooks:
        refusals.append(
            HermesLaunchRefusal(
                CLAUSE_ACCEPT_HOOKS,
                "--accept-hooks",
                "auto-approving unseen shell hooks is refused",
            )
        )
    if spec.ignore_config:
        refusals.append(
            HermesLaunchRefusal(
                CLAUSE_IGNORE_CONFIG,
                "--ignore-user-config/--ignore-rules",
                "weakening governing config/rules is refused",
            )
        )
    return HermesLaunchResult(ok=not refusals, refusals=tuple(refusals))


def _strip_profile_flags(tokens: Sequence[str]) -> list[str]:
    """Drop any ``--profile``/``--profile=`` flag (and its value) so the builder can
    re-inject the canonical pin exactly once (idempotent)."""
    out: list[str] = []
    i = 0
    tokens = list(tokens)
    while i < len(tokens):
        tok = tokens[i]
        name, sep, _ = tok.partition("=")
        if name == "--profile":
            i += 1 if sep else 2  # skip the flag, and its separate value when not inline
            continue
        out.append(tok)
        i += 1
    return out


def build_governed_hermes_command(*, base_argv: Sequence[str]) -> list[str]:
    """Build the governed Hermes command: ``hermes --profile creator-engine [safe args]``.

    Idempotent: a redundant ``--profile creator-engine`` in ``base_argv`` is collapsed.
    Callers must evaluate the spec first; this builder assumes a non-overriding argv.
    """
    cleaned = _strip_profile_flags(base_argv)
    return ["hermes", "--profile", CANONICAL_PROFILE, *cleaned]
