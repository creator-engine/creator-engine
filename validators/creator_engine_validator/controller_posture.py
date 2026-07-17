"""Read-only Controller posture banner.

The banner is intentionally a projection, not an authority surface: it reads
repo-local launch state and explicit posture environment markers, emits a
deterministic record, and never starts daemons, resolves secrets, signs,
merges, changes settings, or performs takeover.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import launch_runtime
from ._versions import V3_LOCAL_STATE_ROOT

_APPROVAL_WALL_STATE_RELATIVE = Path("approval-capability-wall") / "state.json"

FIELD_ORDER: tuple[str, ...] = (
    "role",
    "harness",
    "launch_mode",
    "ring0_confirmed",
    "ring1_active",
    "ring2_closeout_support",
    "credential_scrub_status",
    "remote_control_status",
    "approval_wall_armed",
    "signing_deputy_status",
    "allowed_posture",
)

_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_TRUE_VALUES = frozenset({"1", "true", "yes", "on", "armed", "enabled", "active", "pass", "passed"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off", "unarmed", "disabled", "inactive", "fail", "failed"})
_CREDENTIAL_STATUSES = frozenset({"clean", "scrubbed", "not-reported", "not-applicable", "unknown", "failed"})
_REMOTE_STATUSES = frozenset({"disabled", "brokered", "enabled-supervisory-only", "enabled", "unknown"})
_SIGNING_STATUSES = frozenset({"unavailable", "interim-ce-signer", "openbao-backed", "unknown"})
_GATE_CAPABLE_SIGNING_STATUSES = frozenset({"interim-ce-signer", "openbao-backed"})


@dataclass(frozen=True)
class PostureBanner:
    role: str
    harness: str
    launch_mode: str
    ring0_confirmed: bool
    ring1_active: bool
    ring2_closeout_support: bool
    credential_scrub_status: str
    remote_control_status: str
    approval_wall_armed: bool
    signing_deputy_status: str
    allowed_posture: str

    def to_dict(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in FIELD_ORDER}


def _clean_token(value: str | None, *, default: str = "unknown") -> str:
    raw = (value or "").strip()
    if not raw:
        return default
    cleaned = _TOKEN_RE.sub("-", raw).strip("-._").lower()
    return cleaned or default


def _first_env(environ: Mapping[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = environ.get(name)
        if value and value.strip():
            return value
    return None


def _env_bool(environ: Mapping[str, str], names: tuple[str, ...]) -> bool | None:
    value = _first_env(environ, names)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return None


def _env_false_override(environ: Mapping[str, str], names: tuple[str, ...]) -> bool | None:
    value = _first_env(environ, names)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _FALSE_VALUES:
        return False
    return None


def _choice_status(value: str | None, allowed: frozenset[str], default: str) -> str:
    token = _clean_token(value, default=default)
    return token if token in allowed else default


def _ring0_confirmed(*, harness: str, repo_root: Path) -> bool:
    report = launch_runtime.preflight_launch(
        harness=harness,
        repo_root=repo_root,
        visible=True,
        # No tmux adapter: the report may include tmux/runtime gates, but the
        # posture banner only consumes the deterministic Ring-0 gate names below.
    )
    gates = {gate.name: gate.status for gate in report.gates}
    return all(
        gates.get(name) == "PASS"
        for name in (
            "plan",
            "foreman-dispatch-contract",
            "harness-governance",
            "visibility",
            "harness-binary",
        )
    )


def _ring1_active(*, harness: str, repo_root: Path) -> bool:
    if harness == "codex":
        return bool(launch_runtime._confirm_codex_managed_pack(repo_root))
    if harness == "claude":
        return bool(launch_runtime._confirm_pack(repo_root))
    return False


def _approval_wall_armed(repo_root: Path) -> bool:
    state_root = repo_root / V3_LOCAL_STATE_ROOT
    state_path = state_root / _APPROVAL_WALL_STATE_RELATIVE
    if not state_path.exists():
        return False
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return payload.get("armed") is True


def _default_credential_scrub_status(harness: str) -> str:
    if harness == "codex":
        return "unknown"
    if harness in launch_runtime.SUPPORTED_HARNESSES:
        return "not-applicable"
    return "unknown"


def _derive_allowed_posture(
    *,
    role: str,
    ring0_confirmed: bool,
    ring1_active: bool,
    approval_wall_armed: bool,
    signing_deputy_status: str,
) -> str:
    if role in {"controller", "foreman"} and ring0_confirmed and ring1_active:
        if approval_wall_armed and signing_deputy_status in _GATE_CAPABLE_SIGNING_STATUSES:
            return "gate-capable"
        return "foreman"
    return "read-only"


def collect_posture(
    *,
    repo_root: str | Path = ".",
    environ: Mapping[str, str] | None = None,
    role: str | None = None,
    harness: str | None = None,
    launch_mode: str | None = None,
) -> PostureBanner:
    env = environ if environ is not None else os.environ
    root = Path(repo_root)

    resolved_role = _clean_token(
        role or _first_env(env, ("CE_CONTROLLER_ROLE", "CE_SEAT_ROLE", "CE_ROLE")),
        default="unknown",
    )
    resolved_harness = _clean_token(
        harness or _first_env(env, ("CE_CONTROLLER_HARNESS", "CE_LAUNCH_HARNESS", "CE_HARNESS")),
        default=launch_runtime.DEFAULT_HARNESS,
    )

    try:
        ring0 = _ring0_confirmed(harness=resolved_harness, repo_root=root)
    except launch_runtime.LaunchError:
        ring0 = False
    ring0_override = _env_false_override(env, ("CE_RING0_CONFIRMED", "CE_POSTURE_RING0_CONFIRMED"))
    if ring0_override is not None:
        ring0 = ring0_override

    ring1 = _ring1_active(harness=resolved_harness, repo_root=root)
    ring1_override = _env_false_override(env, ("CE_RING1_ACTIVE", "CE_POSTURE_RING1_ACTIVE"))
    if ring1_override is not None:
        ring1 = ring1_override

    ring2 = _env_bool(env, ("CE_RING2_CLOSEOUT_SUPPORT", "CE_CLOSEOUT_SUPPORT"))
    if ring2 is None:
        ring2 = bool(_first_env(env, ("CE_CLOSEOUT_FILE", "CE_COMPLETION_REPORT_REF")))

    approval_wall = _approval_wall_armed(root)
    approval_wall_override = _env_false_override(env, ("CE_APPROVAL_WALL_ARMED", "CE_APPROVAL_CAPABILITY_WALL_ARMED"))
    if approval_wall_override is not None:
        approval_wall = approval_wall_override

    resolved_launch_mode = _clean_token(
        launch_mode or _first_env(env, ("CE_LAUNCH_MODE", "CE_POSTURE_LAUNCH_MODE")),
        default="governed" if ring0 else "raw-or-unconfirmed",
    )
    credential_scrub = _choice_status(
        _first_env(env, ("CE_CREDENTIAL_SCRUB_STATUS", "CE_POSTURE_CREDENTIAL_SCRUB_STATUS")),
        _CREDENTIAL_STATUSES,
        _default_credential_scrub_status(resolved_harness),
    )
    remote_control = _choice_status(
        _first_env(env, ("CE_REMOTE_CONTROL_STATUS", "CE_POSTURE_REMOTE_CONTROL_STATUS")),
        _REMOTE_STATUSES,
        "disabled",
    )
    signing_deputy = _choice_status(
        _first_env(env, ("CE_SIGNING_DEPUTY_STATUS", "CE_POSTURE_SIGNING_DEPUTY_STATUS")),
        _SIGNING_STATUSES,
        "unavailable",
    )
    allowed = _derive_allowed_posture(
        role=resolved_role,
        ring0_confirmed=bool(ring0),
        ring1_active=bool(ring1),
        approval_wall_armed=bool(approval_wall),
        signing_deputy_status=signing_deputy,
    )
    return PostureBanner(
        role=resolved_role,
        harness=resolved_harness,
        launch_mode=resolved_launch_mode,
        ring0_confirmed=bool(ring0),
        ring1_active=bool(ring1),
        ring2_closeout_support=bool(ring2),
        credential_scrub_status=credential_scrub,
        remote_control_status=remote_control,
        approval_wall_armed=bool(approval_wall),
        signing_deputy_status=signing_deputy,
        allowed_posture=allowed,
    )


def render_text(banner: PostureBanner) -> str:
    lines = ["CE controller posture"]
    for field in FIELD_ORDER:
        value = getattr(banner, field)
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        lines.append(f"{field}: {rendered}")
    return "\n".join(lines) + "\n"


def render_json(banner: PostureBanner) -> str:
    return json.dumps(banner.to_dict(), indent=2, sort_keys=False) + "\n"
