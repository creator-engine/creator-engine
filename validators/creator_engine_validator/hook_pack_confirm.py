"""CC-G-D Ring 0 — committed Claude hook-pack confirmation predicate.

``confirm_hook_pack`` is the pure-ish precondition the Ring 0 kernel checks
*before* permitting ``--dangerously-skip-permissions`` (clause ``CC-D-6`` in
:mod:`claude_launch_spec`). It confirms the committed hook-pack is present,
its ``.claude/settings.json`` parses, the expected PreToolUse/Stop hooks are
registered, the hook scripts carry the executable bit, and the validator is
reachable.

It reads only ``.claude/**`` under ``repo_root`` and the validator probe is
**injectable** so callers/tests never shell out, never launch Claude, and never
make a network call. Confirming the pack does **not** strengthen Ring 1 from
RUNTIME/DEFEASIBLE to HARD — it only supplies the Ring 0 fact that the pack is
active (seat contract §8.2).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# The PreToolUse matcher must cover at least these tools (seat contract §5 / CC-G-C).
EXPECTED_PRETOOLUSE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "Read", "Bash"})

# The committed hook scripts that must exist and be executable.
EXPECTED_HOOK_SCRIPTS = ("ce-hook-common.sh", "ce-pretooluse.sh", "ce-stop.sh")

ValidatorProbe = Callable[[], bool]


@dataclass(frozen=True)
class HookPackConfirmation:
    present: bool
    settings_parsed: bool
    pretooluse_registered: bool
    stop_registered: bool
    hooks_executable: bool
    validator_reachable: bool
    detail: tuple[str, ...] = ()

    @property
    def confirmed(self) -> bool:
        return all(
            (
                self.present,
                self.settings_parsed,
                self.pretooluse_registered,
                self.stop_registered,
                self.hooks_executable,
                self.validator_reachable,
            )
        )

    def to_dict(self) -> dict:
        return {
            "confirmed": self.confirmed,
            "present": self.present,
            "settings_parsed": self.settings_parsed,
            "pretooluse_registered": self.pretooluse_registered,
            "stop_registered": self.stop_registered,
            "hooks_executable": self.hooks_executable,
            "validator_reachable": self.validator_reachable,
            "detail": list(self.detail),
        }


def _default_validator_probe() -> bool:
    """Reachability probe that never launches Claude or touches the network.

    It only confirms the validator bridge is importable in-process (a
    ``hook-check``-class dry probe).
    """
    try:
        from . import hook_check  # noqa: F401

        return True
    except Exception:  # pragma: no cover - import failure is the only false path
        return False


def _pretooluse_registered(hooks_cfg: dict) -> bool:
    for entry in hooks_cfg.get("PreToolUse", []) or []:
        matcher = entry.get("matcher", "") if isinstance(entry, dict) else ""
        tools = {part for part in str(matcher).split("|") if part}
        if EXPECTED_PRETOOLUSE_TOOLS <= tools:
            return True
    return False


def _stop_registered(hooks_cfg: dict) -> bool:
    for entry in hooks_cfg.get("Stop", []) or []:
        if isinstance(entry, dict) and entry.get("hooks"):
            return True
    return False


def confirm_hook_pack(
    repo_root: Path | str, *, validator_probe: ValidatorProbe | None = None
) -> HookPackConfirmation:
    """Confirm the committed Claude hook-pack under ``repo_root``.

    Pure I/O: reads ``.claude/settings.json`` and stats ``.claude/hooks/*.sh``
    only. The ``validator_probe`` defaults to an in-process import probe; pass a
    callable to inject reachability in tests.
    """
    root = Path(repo_root)
    claude_dir = root / ".claude"
    settings_path = claude_dir / "settings.json"
    hooks_dir = claude_dir / "hooks"
    detail: list[str] = []

    present = settings_path.is_file() and hooks_dir.is_dir()
    if not present:
        detail.append(f"hook-pack not present at {claude_dir}")

    settings_parsed = False
    hooks_cfg: dict = {}
    if settings_path.is_file():
        try:
            parsed = json.loads(settings_path.read_text(encoding="utf-8"))
            settings_parsed = isinstance(parsed, dict)
            hooks_cfg = parsed.get("hooks", {}) if settings_parsed else {}
        except (OSError, json.JSONDecodeError) as exc:
            detail.append(f"settings.json did not parse: {exc}")

    pretooluse_registered = settings_parsed and _pretooluse_registered(hooks_cfg)
    if settings_parsed and not pretooluse_registered:
        detail.append(
            "PreToolUse matcher does not cover " + "|".join(sorted(EXPECTED_PRETOOLUSE_TOOLS))
        )
    stop_registered = settings_parsed and _stop_registered(hooks_cfg)
    if settings_parsed and not stop_registered:
        detail.append("no Stop hook registered")

    hooks_executable = True
    for name in EXPECTED_HOOK_SCRIPTS:
        script = hooks_dir / name
        if not script.is_file():
            hooks_executable = False
            detail.append(f"missing hook script {name}")
            continue
        if not os.access(script, os.X_OK):
            hooks_executable = False
            detail.append(f"hook script {name} is not executable")

    probe = validator_probe or _default_validator_probe
    try:
        validator_reachable = bool(probe())
    except Exception as exc:  # a misbehaving probe is a reachability failure
        validator_reachable = False
        detail.append(f"validator probe raised: {exc}")
    if not validator_reachable:
        detail.append("validator not reachable")

    return HookPackConfirmation(
        present=present,
        settings_parsed=settings_parsed,
        pretooluse_registered=pretooluse_registered,
        stop_registered=stop_registered,
        hooks_executable=hooks_executable,
        validator_reachable=validator_reachable,
        detail=tuple(detail),
    )
