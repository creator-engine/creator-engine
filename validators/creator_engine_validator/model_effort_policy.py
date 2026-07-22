"""CE-620 launch-time model and reasoning-effort policy.

This is deliberately a pure, shared resolver.  Launchers use its result to
rewrite harness argv and receipt writers use its canonical status line, so a
human-entered status string cannot drift from the policy actually enforced at
the launch boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_EFFORT = "high"
MINIMUM_EFFORT = "medium"
LUNA_MODEL = "gpt-5.6-luna"
TERRA_MODEL = "gpt-5.6-terra"
SOL_MODEL = "gpt-5.6-sol"

MODEL_FLAGS = frozenset({"--model", "-m"})
EFFORT_FLAGS = frozenset({"--reasoning-effort", "--effort"})
_VALUE_FLAGS = MODEL_FLAGS | EFFORT_FLAGS
_EFFORT_RANK = {"low": 0, "medium": 1, "high": 2, "xhigh": 3}
_SEAT_ROLES = frozenset({"seat", "foreman", "controller", "implementation"})
_VERIFY_ROLES = frozenset({"verify", "mechanical", "advisory"})
_AUTHORITY_ADJACENT_ROLE = "authority-adjacent"
_RATIFIED_MODELS = frozenset({LUNA_MODEL, TERRA_MODEL, SOL_MODEL})


class ModelEffortPolicyRefused(ValueError):
    """A requested model/effort cannot create a governed seat."""


@dataclass(frozen=True)
class ResolvedModelEffort:
    """The only model/effort pair a governed wrapper may hand to a harness."""

    model: str
    effort: str
    role: str
    warnings: tuple[str, ...] = ()

    @property
    def status_line(self) -> str:
        return f"model={self.model}; effort={self.effort}"

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "effort": self.effort,
            "role": self.role,
            "warnings": list(self.warnings),
            "status_line": self.status_line,
        }


def _flag_values(argv: Sequence[str]) -> tuple[str | None, str | None]:
    """Extract final model/effort values from both split and ``=`` spellings.

    The returned values are *requests*, never values to pass through.  Callers
    must use :func:`strip_model_effort_args` plus the resolved result, which
    prevents a stale or conflicting raw flag from surviving a relaunch.
    """
    model: str | None = None
    effort: str | None = None
    tokens = list(argv)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        name, equals, inline = token.partition("=")
        if name not in _VALUE_FLAGS:
            index += 1
            continue
        if equals:
            value = inline
        elif index + 1 < len(tokens):
            index += 1
            value = tokens[index]
        else:
            raise ModelEffortPolicyRefused(f"{name} requires a value")
        if not value:
            raise ModelEffortPolicyRefused(f"{name} requires a non-empty value")
        if name in MODEL_FLAGS:
            model = value
        else:
            effort = value
        index += 1
    return model, effort


def resolve_model_effort(
    argv: Sequence[str] | None,
    *,
    role: str | None = None,
) -> ResolvedModelEffort:
    """Resolve the ratified model tier and fleet-wide effort floor.

    ``None`` role is a normal visible seat.  Luna is intentionally usable only
    for explicit verify/mechanical/advisory organs, never for any role that can
    be a foreman or a persistent seat.  Low is clamped, rather than silently
    accepted, and the warning is carried in the result/audit stamp.
    """
    requested_model, requested_effort = _flag_values(argv or ())
    resolved_role = role or "seat"
    model = requested_model or DEFAULT_MODEL
    effort = requested_effort or DEFAULT_EFFORT
    if model not in _RATIFIED_MODELS:
        raise ModelEffortPolicyRefused(
            f"unratified model {model!r}; governed launches require one of "
            f"{', '.join(sorted(_RATIFIED_MODELS))}"
        )
    if effort not in _EFFORT_RANK:
        raise ModelEffortPolicyRefused(
            f"unsupported reasoning effort {effort!r}; expected one of "
            f"{', '.join(_EFFORT_RANK)}"
        )
    if model == LUNA_MODEL and resolved_role in _SEAT_ROLES:
        raise ModelEffortPolicyRefused(
            "gpt-5.6-luna is verify/mechanical/advisory-organ tier and is refused "
            f"for governed {resolved_role} sessions"
        )
    if model == LUNA_MODEL and resolved_role not in _VERIFY_ROLES:
        raise ModelEffortPolicyRefused(
            "gpt-5.6-luna is limited to explicit verify/mechanical/advisory-organ roles"
        )
    if model == SOL_MODEL and resolved_role != _AUTHORITY_ADJACENT_ROLE:
        raise ModelEffortPolicyRefused(
            "gpt-5.6-sol is escalation tier and requires a controller-approved "
            "authority-adjacent launch role"
        )
    if model == TERRA_MODEL and effort == "xhigh":
        raise ModelEffortPolicyRefused(
            "gpt-5.6-terra xhigh is deferred by the ratified routing table"
        )
    warnings: list[str] = []
    if _EFFORT_RANK[effort] < _EFFORT_RANK[MINIMUM_EFFORT]:
        warnings.append(
            f"requested reasoning effort {effort!r} clamped to fleet minimum "
            f"{MINIMUM_EFFORT!r}"
        )
        effort = MINIMUM_EFFORT
    return ResolvedModelEffort(
        model=model,
        effort=effort,
        role=resolved_role,
        warnings=tuple(warnings),
    )


def strip_model_effort_args(argv: Sequence[str] | None) -> list[str]:
    """Remove every raw model/effort spelling and its split-form value."""
    out: list[str] = []
    tokens = list(argv or ())
    index = 0
    while index < len(tokens):
        name, equals, _value = tokens[index].partition("=")
        if name in _VALUE_FLAGS:
            if not equals:
                index += 1
            index += 1
            continue
        out.append(tokens[index])
        index += 1
    return out


def canonical_status_line(value: ResolvedModelEffort) -> str:
    """Return the receipt-safe status line for an already-resolved launch."""
    return value.status_line


def parse_canonical_status_line(line: str) -> ResolvedModelEffort:
    """Validate a receipt line and reconstruct its bound policy result."""
    prefix = "model="
    separator = "; effort="
    if not isinstance(line, str) or not line.startswith(prefix) or separator not in line:
        raise ModelEffortPolicyRefused(
            "model_effort_line must be canonical 'model=<model>; effort=<effort>'"
        )
    model, effort = line[len(prefix):].split(separator, 1)
    if not model or not effort or separator in effort:
        raise ModelEffortPolicyRefused(
            "model_effort_line must be canonical 'model=<model>; effort=<effort>'"
        )
    resolved = resolve_model_effort(["--model", model, "--effort", effort])
    if resolved.status_line != line:
        raise ModelEffortPolicyRefused(
            "model_effort_line is not the resolved launch policy (it may be below the effort floor)"
        )
    return resolved
