"""RV1-063 — ``ce launch`` / ``ce hud`` deterministic Controller-seat launcher.

DP-2 = B: v1.0 ships a deterministic launcher that opens/attaches a **visible**
tmux Controller seat running the chosen harness (Claude Code / Codex / Hermes).
``ce hud`` is an **alias / seam label** for this same launcher — it is *not* a
CE-native HUD/TUI commitment.

Fail-closed properties:

* There is **no hidden fallback**. A request for a non-visible / detached
  continuation is refused (``HiddenContinuationRefused``); on harness
  exit/crash/auth-loss the launcher must not silently continue in a headless
  pane.
* ``--resume`` attaches to an *existing* launcher session; resuming a missing /
  dead session is refused (``ResumeTargetMissing``) rather than spawning hidden.
* ``--dry-run`` produces a deterministic plan with **no** side effect and **no**
  provider login — used to prove the launch/hud alias offline.

This module does NOT replace ``ce lane launch`` (the governed per-lane
primitive), which remains intact. tmux is reached only through an injected
adapter; no secrets or environment values are printed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Sequence

from . import claude_launch_spec

DEFAULT_HARNESS = "claude"
DEFAULT_SESSION = "ce-controller"
DEFAULT_WINDOW = "controller"
SUPPORTED_HARNESSES = frozenset({"claude", "codex", "hermes", "openclaw"})
VISIBILITY = "operator_visible"


class LaunchError(Exception):
    code = "G6-LAUNCH-ERROR"


class HiddenContinuationRefused(LaunchError):
    code = "G6-LAUNCH-HIDDEN-REFUSED"


class TmuxUnavailableError(LaunchError):
    code = "G6-LAUNCH-TMUX-UNAVAILABLE"


class ResumeTargetMissing(LaunchError):
    code = "G6-LAUNCH-RESUME-MISSING"


class UnsupportedHarness(LaunchError):
    code = "G6-LAUNCH-UNSUPPORTED-HARNESS"


class LaunchRefused(LaunchError):
    """CC-G-D Ring 0: a governed Claude launch surface is refused before side effects."""

    code = "G6-LAUNCH-CLAUDE-REFUSED"


def _confirm_pack(repo_root: Path | str | None) -> bool:
    """Seam: confirm the committed hook-pack is loaded (monkeypatchable in tests).

    Delegates to :func:`hook_pack_confirm.confirm_hook_pack`. Never launches
    Claude and never makes a network call.
    """
    from . import hook_pack_confirm

    return hook_pack_confirm.confirm_hook_pack(Path(repo_root or ".")).confirmed


def _default_mcp_config_path(session: str) -> str:
    """CE-owned, repo-relative MCP config path for a Controller-seat launch."""
    return f".hermes/launch/{session}/mcp/ce-mcp.json"


@dataclass(frozen=True)
class LaunchPlan:
    mode: str  # "launch" | "resume"
    invoked_as: str  # "launch" | "hud"
    alias_of: str  # always "launch" — hud is an alias label
    harness: str
    session: str
    window: str
    command: list[str]
    visibility: str
    dry_run: bool
    resume: bool

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "invoked_as": self.invoked_as,
            "alias_of": self.alias_of,
            "harness": self.harness,
            "session": self.session,
            "window": self.window,
            "command": list(self.command),
            "visibility": self.visibility,
            "dry_run": self.dry_run,
            "resume": self.resume,
        }


@dataclass(frozen=True)
class LaunchResult:
    plan: LaunchPlan
    spawned: bool = False
    attached: bool = False
    terminal: dict | None = None

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict(),
            "spawned": self.spawned,
            "attached": self.attached,
            "terminal": self.terminal,
        }


def plan_launch(
    *,
    harness: str = DEFAULT_HARNESS,
    session: str = DEFAULT_SESSION,
    window: str = DEFAULT_WINDOW,
    invoked_as: str = "launch",
    resume: bool = False,
    dry_run: bool = False,
    extra_args: Sequence[str] | None = None,
) -> LaunchPlan:
    """Build the deterministic launch plan (pure; no side effects)."""
    if harness not in SUPPORTED_HARNESSES:
        raise UnsupportedHarness(
            f"harness {harness!r} is not a supported Controller-seat harness "
            f"({', '.join(sorted(SUPPORTED_HARNESSES))})"
        )
    command = [harness, *(list(extra_args) if extra_args else [])]
    return LaunchPlan(
        mode="resume" if resume else "launch",
        invoked_as=invoked_as,
        alias_of="launch",
        harness=harness,
        session=session,
        window=window,
        command=command,
        visibility=VISIBILITY,
        dry_run=dry_run,
        resume=resume,
    )


def _session_exists(adapter: Any, session: str) -> bool:
    probe = getattr(adapter, "session_exists", None)
    if callable(probe):
        return bool(probe(session))
    # Fall back to the existing TmuxAdapter private probe without modifying it.
    private = getattr(adapter, "_session_exists", None)
    if callable(private):
        return bool(private(session))
    return False


def launch(
    *,
    harness: str = DEFAULT_HARNESS,
    session: str = DEFAULT_SESSION,
    window: str = DEFAULT_WINDOW,
    invoked_as: str = "launch",
    resume: bool = False,
    dry_run: bool = False,
    visible: bool = True,
    allow_hidden: bool = False,
    extra_args: Sequence[str] | None = None,
    tmux_adapter: Any | None = None,
    repo_root: Path | str | None = None,
    mcp_config_path: str | None = None,
    closeout_file: str | None = None,
    completion_report_ref: str | None = None,
) -> LaunchResult:
    """Open or attach a visible Controller-seat tmux session.

    All refusals raise before any side effect (no tmux spawn). For the Claude
    harness, the CC-G-D Ring 0 launch-spec is evaluated and the governed command
    (pinned ``--setting-sources project`` + strict MCP) is built **before** the
    hidden/dry-run/tmux branches.
    """
    plan = plan_launch(
        harness=harness,
        session=session,
        window=window,
        invoked_as=invoked_as,
        resume=resume,
        dry_run=dry_run,
        extra_args=extra_args,
    )

    # CC-G-D Ring 0: refuse prohibited Claude surfaces and pin the governed
    # command BEFORE any side effect (hidden/dry-run/tmux branches below).
    if harness == "claude":
        requested = list(extra_args) if extra_args else []
        spec = claude_launch_spec.parse_claude_argv(requested)
        # The pack confirmation only changes the decision when skip-permissions is
        # requested, so the (possibly I/O-bound) probe is invoked only then.
        confirmed = _confirm_pack(repo_root) if spec.skip_permissions else False
        spec_result = claude_launch_spec.evaluate_claude_launch(
            spec, hook_pack_confirmed=confirmed
        )
        if not spec_result.ok:
            codes = ", ".join(r.clause for r in spec_result.refusals)
            surfaces = ", ".join(r.surface for r in spec_result.refusals)
            raise LaunchRefused(
                f"refusing governed Claude launch: {codes} ({surfaces}) — "
                "Ring 0 refuses before any side effect"
            )
        resolved_mcp = mcp_config_path or _default_mcp_config_path(session)
        try:
            governed = claude_launch_spec.build_governed_claude_command(
                base_argv=requested,
                mcp_config_path=resolved_mcp,
                closeout_file=closeout_file,
                completion_report_ref=completion_report_ref,
            )
        except claude_launch_spec.GovernedCommandError as exc:
            clause = (
                claude_launch_spec.CLAUSE_MCP
                if "MCP config" in str(exc)
                else claude_launch_spec.CLAUSE_LOCAL_SETTINGS
            )
            raise LaunchRefused(
                f"refusing governed Claude launch: {clause} — {exc}"
            ) from exc
        plan = replace(plan, command=governed)

    # No hidden fallback — a non-visible / detached continuation is refused.
    if allow_hidden or not visible:
        raise HiddenContinuationRefused(
            "refusing hidden/detached Controller-seat continuation; there is no hidden fallback "
            "(harness exit/crash/auth-loss must not continue headless)"
        )

    # Dry-run is pure: deterministic plan, no tmux, no provider login.
    if dry_run:
        return LaunchResult(plan=plan, spawned=False, attached=False)

    if tmux_adapter is None:
        from .tmux_adapter import TmuxAdapter

        tmux_adapter = TmuxAdapter()

    if not tmux_adapter.is_available():
        raise TmuxUnavailableError(
            "tmux is unavailable; refusing visible Controller-seat launch before any side effect"
        )

    if resume:
        if not _session_exists(tmux_adapter, session):
            raise ResumeTargetMissing(
                f"no live launcher session {session!r} to resume; refusing to spawn a hidden seat"
            )

    pane = tmux_adapter.ensure_pane(session=session, window=window, command=plan.command)
    terminal = {
        "kind": "tmux",
        "session_id": pane.session_id,
        "window_id": pane.window_id,
        "pane_id": pane.pane_id,
    }
    return LaunchResult(plan=plan, spawned=True, attached=resume, terminal=terminal)
