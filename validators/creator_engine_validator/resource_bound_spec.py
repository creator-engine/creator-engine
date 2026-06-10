"""v3.5-F Q1 — per-seat OS-enforced resource bounding (the systemd-run wrap).

PURE core + thin injectable-runner I/O edges, mirroring the
``claude_launch_spec`` (pure Ring-0 builder) / ``tmux_adapter`` (injectable
runner) split:

* :class:`ResourceBound` + :func:`build_bounded_command` — the PURE builder
  that prefixes an **already-governed** command with the
  ``systemd-run --user --scope`` bounding wrap. The wrap is applied to the
  *output* of Ring 0, never its input: the governed tokens are passed through
  byte-identical (``bound=None`` -> command unchanged).
* :func:`parse_resource_policy` — the PURE, fail-closed reader of the
  ``resource_envelopes`` / ``resource_enforcement`` / ``resource_optout``
  policy fragment (the v3 ``runtime-policy`` schema fields). The fragment is
  plain data read through the existing policy-read seam (``loader.load_yaml``
  in the launch runtimes); this module imports NO v3 module — it is
  V1-classified launch mechanics (``_versions.V1_RUNTIME``).
* :func:`host_class_defaults` — the PURE §4.4 host-class default
  materialization the installer / ``ce doctor`` emits INTO the policy. Bounds
  are never computed silently at launch; the ratified policy file is the
  single source of truth.
* I/O edges (all runner-injectable, no module-level side effects):
  :func:`probe_user_bounding` (refuse-loudly support probe),
  :func:`resolve_unit_name` (sanitize + collision probe),
  :func:`apply_fleet_cap` (idempotent ``set-property --runtime`` on the fleet
  slice), :func:`write_oom_group` (the one cgroupfs write that guarantees the
  kernel kills the SEAT, never a random child — systemd has no unit property
  for ``memory.oom.group``).

Enforcement semantics (Fork F-2, ratified): ``enforce`` by default —
refuse loudly at launch when user-level systemd bounding is unavailable;
``advisory`` / ``off`` are explicit ratified opt-downs that REQUIRE a
``resource_optout`` binding (fail-closed without it, mirroring
``spend_cap_optout``) and launch unbounded with the evidence stamped
``resource_bound: none (<mode>)``.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

#: This module is CE v1.0 launch mechanics (declared in ``_versions.V1_RUNTIME``).
__ce_version_line__ = "v1"

DEFAULT_SLICE = "ce-fleet.slice"
UNIT_PREFIX = "ce-seat-"

ENFORCE = "enforce"
ADVISORY = "advisory"
OFF = "off"
ENFORCEMENT_MODES = frozenset({ENFORCE, ADVISORY, OFF})

SCOPE_SEAT = "seat"
SCOPE_FLEET = "fleet"
_ENVELOPE_SCOPES = frozenset({SCOPE_SEAT, SCOPE_FLEET})

# systemd size string: bytes or K/M/G/T suffix (no spaces — the -p values must
# stay single shell-safe KEY=VALUE tokens through the tmux command join).
_SIZE_RE = re.compile(r"^[0-9]+(K|M|G|T)?$")
_CPU_QUOTA_RE = re.compile(r"^[0-9]+%$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
# systemd unit-name charset (conservative subset; ``@`` and ``\`` escapes are
# deliberately not generated).
_UNIT_UNSAFE_RE = re.compile(r"[^a-zA-Z0-9_.-]")

_ENVELOPE_KEYS = frozenset(
    {
        "scope",
        "memory_high",
        "memory_max",
        "memory_swap_max",
        "tasks_max",
        "cpu_weight",
        "cpu_quota",
    }
)
# The four named seat axes — a seat envelope under `enforce` must pin them all
# (a partially-specified seat bound would silently leave an axis unbounded).
_SEAT_REQUIRED = ("memory_high", "memory_max", "memory_swap_max", "tasks_max")

_UNIT_COLLISION_MAX_PROBES = 16
_CONFIRM_ATTEMPTS = 20
_CONFIRM_INTERVAL = 0.25  # seconds; ~5s worst case (mirrors the tmux cwd poll)


class ResourceBoundError(Exception):
    """Base class for resource-bounding errors. Carries a stable ``code``."""

    code = "RB-ERROR"


class ResourcePolicyError(ResourceBoundError):
    """The resource policy fragment is malformed or an opt-down is unratified."""

    code = "RB-POLICY-INVALID"


class ResourceBoundUnsupported(ResourceBoundError):
    """``enforce`` on a host without user-level systemd bounding — refuse loudly."""

    code = "RB-HOST-UNSUPPORTED"


class UnitNameCollision(ResourceBoundError):
    """No free ``ce-seat-…`` unit name within the probe bound — refuse loudly."""

    code = "RB-UNIT-COLLISION"


class SeatScopeUnavailable(ResourceBoundError):
    """The launched seat scope never materialized (or a confirm write failed)."""

    code = "RB-SCOPE-UNAVAILABLE"


# ---------------------------------------------------------------------------
# PURE core — the bound + the wrap builder
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceBound:
    """One seat's OS bound. Pure value; all fields are systemd property inputs."""

    unit: str            # "ce-seat-<seat>" — deterministic, sanitized
    slice: str           # "ce-fleet.slice" (policy-overridable later; fixed v1)
    memory_high: str     # e.g. "3500M" — kernel reclaim brake (brief)
    memory_max: str      # e.g. "4G" — kernel group-kill ceiling
    memory_swap_max: str  # e.g. "256M" — small: bounds the stall window
    tasks_max: int       # e.g. 512 — fork-bomb stop
    cpu_weight: int | None = None   # Tier-A; None = omit
    cpu_quota: str | None = None    # Tier-A; None = omit

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "unit": self.unit,
            "slice": self.slice,
            "memory_high": self.memory_high,
            "memory_max": self.memory_max,
            "memory_swap_max": self.memory_swap_max,
            "tasks_max": self.tasks_max,
        }
        if self.cpu_weight is not None:
            out["cpu_weight"] = self.cpu_weight
        if self.cpu_quota is not None:
            out["cpu_quota"] = self.cpu_quota
        return out


def build_bounded_command(
    command: Sequence[str], bound: ResourceBound | None
) -> list[str]:
    """PURE: prefix the (already-governed) command with the systemd-run wrap.

    ``bound=None`` -> command unchanged (policy: no resource governance, or an
    explicit ratified opt-down). The governed command tokens are passed through
    byte-identical after the ``--`` separator — the wrap is strictly additive
    to the OUTPUT of Ring 0 and removing the prefix reproduces the input
    exactly.

    ``--expand-environment=no`` (systemd >= 254) is load-bearing for that
    byte-fidelity: without it systemd-run expands ``$VAR``/``${VAR}`` tokens
    inside the wrapped command at exec time (OBSERVED on systemd 259 — a
    ``${…}`` token evaluated to empty), silently mutating Ring-0 output such
    as the inert lane placeholder's ``"${SHELL:-/bin/sh}"``.
    """
    if bound is None:
        return list(command)
    return [
        "systemd-run", "--user", "--scope", "--collect",
        "--expand-environment=no",
        "--unit", bound.unit, "--slice", bound.slice,
        "-p", f"MemoryHigh={bound.memory_high}",
        "-p", f"MemoryMax={bound.memory_max}",
        "-p", f"MemorySwapMax={bound.memory_swap_max}",
        "-p", f"TasksMax={bound.tasks_max}",
        *(["-p", f"CPUWeight={bound.cpu_weight}"] if bound.cpu_weight else []),
        *(["-p", f"CPUQuota={bound.cpu_quota}"] if bound.cpu_quota else []),
        "--", *command,
    ]


def sanitize_unit_name(seat_id: str) -> str:
    """PURE: deterministic systemd-safe unit name for a seat (no ``.scope`` suffix).

    Maps every character outside the conservative unit charset to ``-`` and
    collapses runs, so e.g. session ``v35f q1/exec`` -> ``ce-seat-v35f-q1-exec``.
    """
    cleaned = _UNIT_UNSAFE_RE.sub("-", str(seat_id).strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-.")
    if not cleaned:
        raise ResourcePolicyError("seat id sanitizes to an empty systemd unit name")
    return f"{UNIT_PREFIX}{cleaned}"


# ---------------------------------------------------------------------------
# PURE policy fragment reader (fail-closed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourcePolicy:
    """Validated view of the resource fragment of one runtime policy."""

    enforcement: str                       # enforce | advisory | off
    seat: Mapping[str, Any] | None         # validated seat envelope, else None
    fleet: Mapping[str, Any] | None        # validated fleet envelope, else None

    @property
    def governed(self) -> bool:
        """True when the policy declares any resource envelope."""
        return self.seat is not None or self.fleet is not None

    @property
    def opted_down(self) -> bool:
        return self.enforcement in (ADVISORY, OFF)

    def seat_bound(self, unit: str, *, slice_name: str = DEFAULT_SLICE) -> ResourceBound | None:
        """Materialize the per-seat bound for ``unit`` (None when no seat envelope)."""
        if self.seat is None:
            return None
        return ResourceBound(
            unit=unit,
            slice=slice_name,
            memory_high=str(self.seat["memory_high"]),
            memory_max=str(self.seat["memory_max"]),
            memory_swap_max=str(self.seat["memory_swap_max"]),
            tasks_max=int(self.seat["tasks_max"]),
            cpu_weight=self.seat.get("cpu_weight"),
            cpu_quota=self.seat.get("cpu_quota"),
        )

    @property
    def fleet_memory_max(self) -> str | None:
        return str(self.fleet["memory_max"]) if self.fleet else None


def _valid_optout(binding: Any) -> bool:
    """Mirror of ``v3_installer._valid_optout`` / ``spend_cap_optout`` validation."""
    return (
        isinstance(binding, Mapping)
        and isinstance(binding.get("ratified_prompt_sha"), str)
        and bool(_HEX64_RE.match(binding["ratified_prompt_sha"]))
        and isinstance(binding.get("approver_ref"), str)
        and bool(_HEX64_RE.match(binding["approver_ref"]))
    )


def _validate_envelope(entry: Any, index: int) -> Mapping[str, Any]:
    if not isinstance(entry, Mapping):
        raise ResourcePolicyError(f"resource_envelopes[{index}] is not a mapping")
    unknown = set(entry) - _ENVELOPE_KEYS
    if unknown:
        raise ResourcePolicyError(
            f"resource_envelopes[{index}] carries unknown keys {sorted(unknown)}"
        )
    scope = entry.get("scope")
    if scope not in _ENVELOPE_SCOPES:
        raise ResourcePolicyError(
            f"resource_envelopes[{index}].scope {scope!r} is not one of "
            f"{sorted(_ENVELOPE_SCOPES)}"
        )
    for key in ("memory_high", "memory_max", "memory_swap_max"):
        value = entry.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not _SIZE_RE.match(value):
            raise ResourcePolicyError(
                f"resource_envelopes[{index}].{key} {value!r} is not a systemd size "
                "string (digits + optional K/M/G/T suffix)"
            )
    if "memory_max" not in entry:
        raise ResourcePolicyError(f"resource_envelopes[{index}] is missing memory_max")
    tasks_max = entry.get("tasks_max")
    if tasks_max is not None and (
        not isinstance(tasks_max, int) or isinstance(tasks_max, bool) or tasks_max < 1
    ):
        raise ResourcePolicyError(
            f"resource_envelopes[{index}].tasks_max {tasks_max!r} is not a positive integer"
        )
    cpu_weight = entry.get("cpu_weight")
    if cpu_weight is not None and (
        not isinstance(cpu_weight, int)
        or isinstance(cpu_weight, bool)
        or not 1 <= cpu_weight <= 10000
    ):
        raise ResourcePolicyError(
            f"resource_envelopes[{index}].cpu_weight {cpu_weight!r} is not an integer in 1..10000"
        )
    cpu_quota = entry.get("cpu_quota")
    if cpu_quota is not None and (
        not isinstance(cpu_quota, str) or not _CPU_QUOTA_RE.match(cpu_quota)
    ):
        raise ResourcePolicyError(
            f"resource_envelopes[{index}].cpu_quota {cpu_quota!r} is not a percent string (e.g. '200%')"
        )
    return entry


def parse_resource_policy(policy: Any) -> ResourcePolicy:
    """PURE, fail-closed reader of a policy mapping's resource fragment.

    Accepts either a full ``runtime-policy-record`` mapping or a fragment
    sidecar carrying only the ``resource_*`` keys (the same dual shape the
    spend fragment supports). Raises :class:`ResourcePolicyError` on any
    malformed value and on an ``advisory``/``off`` opt-down that lacks a valid
    ``resource_optout`` ratification binding (an agent can never opt a seat
    out of resource enforcement — mirrors ``build_profile``).
    """
    if not isinstance(policy, Mapping):
        raise ResourcePolicyError("runtime policy is not a YAML/JSON mapping")

    enforcement = policy.get("resource_enforcement", ENFORCE)
    if enforcement not in ENFORCEMENT_MODES:
        raise ResourcePolicyError(
            f"resource_enforcement {enforcement!r} is not one of {sorted(ENFORCEMENT_MODES)}"
        )
    if enforcement in (ADVISORY, OFF) and not _valid_optout(policy.get("resource_optout")):
        raise ResourcePolicyError(
            f"resource_enforcement is {enforcement!r} but the resource_optout "
            "ratification binding is absent or invalid; the opt-down is a "
            "ratified-HUMAN-only choice and REQUIRES a 64-hex "
            "ratified_prompt_sha + approver_ref"
        )

    raw = policy.get("resource_envelopes")
    if raw is None:
        return ResourcePolicy(enforcement=enforcement, seat=None, fleet=None)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ResourcePolicyError("resource_envelopes is not a list")

    seat: Mapping[str, Any] | None = None
    fleet: Mapping[str, Any] | None = None
    for index, entry in enumerate(raw):
        validated = _validate_envelope(entry, index)
        if validated["scope"] == SCOPE_SEAT:
            if seat is not None:
                raise ResourcePolicyError("resource_envelopes declares more than one seat envelope")
            seat = validated
        else:
            if fleet is not None:
                raise ResourcePolicyError("resource_envelopes declares more than one fleet envelope")
            fleet = validated

    if seat is not None and enforcement == ENFORCE:
        missing = [key for key in _SEAT_REQUIRED if key not in seat]
        if missing:
            raise ResourcePolicyError(
                f"seat resource envelope under 'enforce' is missing {missing}; "
                "a partially-specified seat bound would silently leave an axis unbounded"
            )
    if seat is None and fleet is not None and enforcement == ENFORCE:
        raise ResourcePolicyError(
            "resource_envelopes declares a fleet envelope but no seat envelope "
            "under 'enforce'; the fleet slice is populated by per-seat wraps, so a "
            "fleet-only policy would look governed while enforcing nothing at launch"
        )

    return ResourcePolicy(enforcement=enforcement, seat=seat, fleet=fleet)


# ---------------------------------------------------------------------------
# PURE §4.4 host-class default materialization (installer / `ce doctor` output)
# ---------------------------------------------------------------------------

_GIB = 1024 ** 3
_DESKTOP_FLOOR_BYTES = 12 * _GIB


def host_class_defaults(mem_total_bytes: int) -> dict[str, Any]:
    """PURE: the §4.4 host-class default resource policy fragment.

    Emitted by the installer / ``ce doctor`` INTO the policy file (the
    ratified policy stays the single source of truth; nothing is computed
    silently at launch). Two host classes:

    * desktop-class (MemTotal >= 12 GiB, shared with a UI): seat
      3.5G/4G/256M, fleet 9G — kills a 9.1 GB-class leak at <30% of RAM while
      leaving >=5G for the desktop + page cache.
    * small-host class (e.g. the 8 GB headless VPS pilot): seat 2G/2.5G/128M,
      fleet 5.5G — survives one runaway with no systemd-oomd mediator.
    """
    if not isinstance(mem_total_bytes, int) or mem_total_bytes <= 0:
        raise ResourcePolicyError(f"mem_total_bytes {mem_total_bytes!r} is not a positive integer")
    if mem_total_bytes >= _DESKTOP_FLOOR_BYTES:
        host_class = "desktop-14g"
        seat_high, seat_max, swap_max, fleet_max = "3500M", "4G", "256M", "9G"
    else:
        host_class = "small-host-8g"
        seat_high, seat_max, swap_max, fleet_max = "2G", "2500M", "128M", "5500M"
    return {
        "host_class": host_class,
        "resource_envelopes": [
            {
                "scope": SCOPE_SEAT,
                "memory_high": seat_high,
                "memory_max": seat_max,
                "memory_swap_max": swap_max,
                "tasks_max": 512,
                "cpu_weight": 100,
            },
            {"scope": SCOPE_FLEET, "memory_max": fleet_max},
        ],
        "resource_enforcement": ENFORCE,
    }


# ---------------------------------------------------------------------------
# I/O edges — injectable systemctl runner + cgroupfs writes (no side effects
# at import; every function takes its runner so tests stay process-free)
# ---------------------------------------------------------------------------

Runner = Callable[..., subprocess.CompletedProcess]


def _default_runner(argv: Sequence[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=check, capture_output=True, text=True)


def probe_user_bounding(
    runner: Runner | None = None,
    *,
    controllers_path: Path | str | None = None,
) -> tuple[bool, str]:
    """Probe whether user-level systemd bounding is available on this host.

    Returns ``(ok, reason)``. ``enforce`` callers refuse loudly on ``ok=False``
    (non-systemd host, no live user manager / session D-Bus — e.g. a stripped
    SSH context without linger — or no memory/pids controller delegation).
    """
    run = runner or _default_runner
    try:
        proc = run(["systemctl", "--user", "show-environment"], check=False)
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        return False, f"systemctl is unavailable: {exc}"
    if proc.returncode != 0:
        return False, (
            "no live per-user systemd manager / session D-Bus "
            "(on a headless host enable lingering: loginctl enable-linger)"
        )
    path = (
        Path(controllers_path)
        if controllers_path is not None
        else Path(
            f"/sys/fs/cgroup/user.slice/user-{os.getuid()}.slice/"
            f"user@{os.getuid()}.service/cgroup.controllers"
        )
    )
    try:
        controllers = path.read_text(encoding="utf-8").split()
    except OSError as exc:
        return False, f"cannot read user-manager cgroup.controllers ({exc})"
    missing = [c for c in ("memory", "pids") if c not in controllers]
    if missing:
        return False, f"user manager lacks delegated controllers: {missing}"
    return True, "user-level systemd bounding available"


def _active_state(unit_name: str, run: Runner) -> str:
    proc = run(
        ["systemctl", "--user", "show", "-p", "ActiveState", "--value", f"{unit_name}.scope"],
        check=False,
    )
    return (proc.stdout or "").strip()


def resolve_unit_name(
    seat_id: str,
    runner: Runner | None = None,
    *,
    max_probes: int = _UNIT_COLLISION_MAX_PROBES,
) -> str:
    """Sanitize ``seat_id`` and resolve a collision-free unit name (live probe).

    Probes ``ce-seat-<seat>``, then ``-2``, ``-3``, … via
    ``systemctl --user show``; a name is free when its scope is ``inactive``
    (an active scope = a still-running prior seat). Refuses loudly
    (:class:`UnitNameCollision`) when no free name exists within the bound or
    the probe itself fails — a relaunch into a taken unit would otherwise fail
    inside the pane, invisibly.
    """
    run = runner or _default_runner
    base = sanitize_unit_name(seat_id)
    candidates = [base] + [f"{base}-{n}" for n in range(2, max_probes + 1)]
    for candidate in candidates:
        try:
            state = _active_state(candidate, run)
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
            raise UnitNameCollision(
                f"cannot probe unit name {candidate!r} via systemctl --user show: {exc}"
            ) from exc
        if state in ("", "inactive"):
            return candidate
    raise UnitNameCollision(
        f"no free seat unit name for {base!r} within {max_probes} probes; "
        "retire stale seat scopes before relaunch"
    )


def apply_fleet_cap(
    memory_max: str,
    *,
    slice_name: str = DEFAULT_SLICE,
    runner: Runner | None = None,
    attempts: int = _CONFIRM_ATTEMPTS,
    sleeper: Callable[[float], None] | None = None,
    interval: float = _CONFIRM_INTERVAL,
) -> None:
    """Idempotently apply the collective fleet cap from the policy.

    ``systemctl --user set-property --runtime <slice> MemoryMax=<fleet>`` —
    runtime-only (clears on session end) and re-applied at every launch FROM
    THE POLICY, so nothing durable hides in ``~/.config/systemd/``. The slice
    is created by the seat's own ``systemd-run --slice``, which may land
    moments after the pane spawns, so the call is retried (bounded) while the
    slice is not yet loaded; exhaustion refuses loudly
    (:class:`SeatScopeUnavailable`) — it doubles as confirmation that the
    wrap actually started.
    """
    run = runner or _default_runner
    sleep = sleeper or time.sleep
    if not _SIZE_RE.match(str(memory_max)):
        raise ResourcePolicyError(f"fleet memory_max {memory_max!r} is not a systemd size string")
    last_err = ""
    for attempt in range(attempts):
        try:
            proc = run(
                [
                    "systemctl", "--user", "set-property", "--runtime",
                    slice_name, f"MemoryMax={memory_max}",
                ],
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
            raise SeatScopeUnavailable(f"cannot apply fleet cap on {slice_name!r}: {exc}") from exc
        if proc.returncode == 0:
            return
        last_err = (proc.stderr or "").strip()
        if attempt < attempts - 1:
            sleep(interval)
    raise SeatScopeUnavailable(
        f"fleet cap on {slice_name!r} not applied within {attempts} attempts "
        f"(last error: {last_err or 'unknown'}); the bounding wrap may not have started"
    )


def write_oom_group(
    unit_name: str,
    *,
    runner: Runner | None = None,
    cgroupfs_root: Path | str = "/sys/fs/cgroup",
    attempts: int = _CONFIRM_ATTEMPTS,
    sleeper: Callable[[float], None] | None = None,
    interval: float = _CONFIRM_INTERVAL,
) -> Path:
    """Write ``memory.oom.group=1`` into the seat scope at launch-confirm.

    One cgroupfs write inside the delegated subtree (systemd exposes NO unit
    property for it). Without the group bit the kernel kills only the biggest
    *task* in the scope — a random child — instead of the seat as a unit. The
    scope's cgroup path is resolved via ``systemctl --user show -p
    ControlGroup`` (robust to slice dash-expansion), polled (bounded) because
    the scope materializes moments after the pane spawns. Refuses loudly
    (:class:`SeatScopeUnavailable`) when the scope never appears or the write
    fails — at launch-confirm time that means the seat is not provably
    group-killable.
    """
    run = runner or _default_runner
    sleep = sleeper or time.sleep
    control_group = ""
    for attempt in range(attempts):
        try:
            proc = run(
                [
                    "systemctl", "--user", "show", "-p", "ControlGroup",
                    "--value", f"{unit_name}.scope",
                ],
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
            raise SeatScopeUnavailable(
                f"cannot resolve ControlGroup for {unit_name!r}: {exc}"
            ) from exc
        control_group = (proc.stdout or "").strip()
        if control_group:
            break
        if attempt < attempts - 1:
            sleep(interval)
    if not control_group:
        raise SeatScopeUnavailable(
            f"seat scope {unit_name!r} never reported a ControlGroup within "
            f"{attempts} polls; the bounding wrap may not have started"
        )
    target = Path(cgroupfs_root) / control_group.lstrip("/") / "memory.oom.group"
    try:
        target.write_text("1\n", encoding="ascii")
    except OSError as exc:
        raise SeatScopeUnavailable(
            f"cannot write memory.oom.group for {unit_name!r} at {target}: {exc}"
        ) from exc
    return target
