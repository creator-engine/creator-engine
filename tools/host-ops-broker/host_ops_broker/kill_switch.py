"""Broker-wide and per-verb disable flag reader."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KillSwitchDecision:
    disabled: bool
    disabled_scope: str | None = None
    disabled_reason_ref: str | None = None


def check_kill_switch(path: str | Path, verb: str) -> KillSwitchDecision:
    """Read the kill-switch JSON file and fail closed if it cannot be read."""
    p = Path(path).expanduser()
    if not p.exists():
        return KillSwitchDecision(False)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return KillSwitchDecision(True, "broker", f"kill-switch-read-error:{p}")
    if not isinstance(raw, Mapping):
        return KillSwitchDecision(True, "broker", f"kill-switch-malformed:{p}")
    if raw.get("disabled") is True:
        return KillSwitchDecision(True, "broker", _reason(raw, "broker-wide-disabled"))
    disabled_verbs = raw.get("disabled_verbs", {})
    if disabled_verbs is None:
        disabled_verbs = {}
    if not isinstance(disabled_verbs, Mapping):
        return KillSwitchDecision(True, "broker", f"kill-switch-malformed:{p}")
    if verb in disabled_verbs:
        reason_raw: Any = disabled_verbs[verb]
        reason = str(reason_raw or f"verb-disabled:{verb}")
        return KillSwitchDecision(True, f"verb:{verb}", reason)
    return KillSwitchDecision(False)


def _reason(raw: Mapping[str, Any], fallback: str) -> str:
    reason = raw.get("reason_ref")
    if isinstance(reason, str) and reason.strip():
        return reason
    return fallback
