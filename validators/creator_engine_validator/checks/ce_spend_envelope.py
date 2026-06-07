"""Spend-envelope policy predicates (v3 G-5 tokenomics gate).

Validates the *semantic* spend-governance predicates over Runtime Policy records —
the cross-envelope rules that go beyond the schema shape (the runtime-policy schema
+ the ``ce_runtime_policy`` check already own the field shapes). This check fires
only on records that DECLARE spend governance; a policy without the G-5 fields is a
valid G-1.0/G-4 policy and passes trivially (green-on-day-one).

Predicates (each an explicit error class):

* **mandatory global ceiling** — whenever any ``$`` envelope is declared, a
  ``global``-scope ``$`` envelope MUST exist (the anti-catastrophe backstop; Fork
  B). The runaway-DETECTION net keeps this even when the CAP is opted out.
* **nested consistency** — for ``$`` envelopes sharing a window, the inner cap must
  not exceed the outer (``run`` <= ``fleet`` <= ``global``); most-restrictive-wins
  is otherwise unsatisfiable-by-construction.
* **two-regime unit correctness** — ``%`` (the single-seat subscription meter) is
  ``run``-scoped only (never a ``fleet``/``global`` scope); ``fleet``/``global``
  scopes are ``$`` (API-USD); and a ``%`` policy declares no ``fleet`` scope (a
  subscription seat is never a poolable fleet). Fork C.
* **ratified opt-out** — ``spend_cap_enforcement: off`` REQUIRES a
  ``spend_cap_optout`` binding with a valid ``ratified_prompt_sha`` +
  ``approver_ref`` (64-hex). The opt-out is a ratified-HUMAN-only choice; an
  agent can never set it (the gate is external), and the check refuses an
  unratified opt-out.

This check is **defensive** — it caps the Creator Engine's own runtime spend; it
NEVER allocates a container, meters a live runtime, or opens a socket. The pure
spend decision substrate (admission + circuit-breaker) is ``runner.spend_gate``.

See:
  - ``docs/contracts/spend-envelope.md``
  - ``schemas/runtime-policy.schema.yaml`` (the spend-envelope policy fields)
  - ``creator_engine_validator/runner/spend_gate.py``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .ce_runtime_policy import iter_runtime_policy_records

CHECK_NAME = "ce_spend_envelope"
CONTRACT = "docs/contracts/spend-envelope.md"

# Failure codes (explicit error classes).
CODE_NO_GLOBAL_CEILING = "VAL-SPEND-NO-GLOBAL-CEILING"
CODE_ENVELOPE_INCONSISTENT = "VAL-SPEND-ENVELOPE-INCONSISTENT"
CODE_REGIME_UNIT = "VAL-SPEND-REGIME-UNIT"
CODE_OPTOUT_UNRATIFIED = "VAL-SPEND-OPTOUT-UNRATIFIED"
CODE_INVALID = "runtime_policy_invalid_record"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SCOPE_RANK = {"run": 0, "fleet": 1, "global": 2}


def _as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _check_optout(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """When enforcement is off, require a valid ratification binding."""
    enforcement = record.get("spend_cap_enforcement", "enforce")
    if enforcement != "off":
        return []
    optout = record.get("spend_cap_optout")
    ok = (
        isinstance(optout, dict)
        and isinstance(optout.get("ratified_prompt_sha"), str)
        and bool(_HEX64_RE.match(optout["ratified_prompt_sha"]))
        and isinstance(optout.get("approver_ref"), str)
        and bool(_HEX64_RE.match(optout["approver_ref"]))
    )
    if ok:
        return []
    return [make_error(
        CODE_OPTOUT_UNRATIFIED,
        path,
        "spend_cap_optout",
        (
            "spend_cap_enforcement is 'off' but the spend_cap_optout ratification "
            "binding is absent or invalid; the opt-out is a ratified-HUMAN-only "
            "choice and REQUIRES a 64-hex ratified_prompt_sha + approver_ref (an "
            "agent can never opt out of cost enforcement)"
        ),
        CONTRACT,
    )]


def _check_regime_units(envelopes: list[dict[str, Any]], path: Path) -> list[ValidationError]:
    """Two-regime unit correctness (Fork C)."""
    errors: list[ValidationError] = []
    has_pct = any(env.get("unit") == "%" for env in envelopes)
    for index, env in enumerate(envelopes):
        scope = env.get("scope")
        unit = env.get("unit")
        if unit == "%" and scope != "run":
            errors.append(make_error(
                CODE_REGIME_UNIT,
                path,
                f"spend_envelopes[{index}]",
                (
                    f"a '%' (single-seat subscription) envelope must be 'run'-scoped, "
                    f"not '{scope}' — a subscription seat is never a poolable fleet"
                ),
                CONTRACT,
            ))
        if scope in ("fleet", "global") and unit != "$":
            errors.append(make_error(
                CODE_REGIME_UNIT,
                path,
                f"spend_envelopes[{index}]",
                f"a '{scope}'-scope envelope must be '$' (API-USD), not '{unit}'",
                CONTRACT,
            ))
        if has_pct and scope == "fleet":
            errors.append(make_error(
                CODE_REGIME_UNIT,
                path,
                f"spend_envelopes[{index}]",
                (
                    "a '%'-metered (subscription) policy must declare no 'fleet' scope "
                    "— a subscription seat is single-seat, never a fleet"
                ),
                CONTRACT,
            ))
    return errors


def _check_global_ceiling(envelopes: list[dict[str, Any]], path: Path) -> list[ValidationError]:
    """A global $ ceiling is mandatory whenever any $ envelope is declared (Fork B)."""
    dollar_envs = [env for env in envelopes if env.get("unit") == "$"]
    if not dollar_envs:
        return []
    has_global_dollar = any(
        env.get("scope") == "global" and env.get("unit") == "$" for env in envelopes
    )
    if has_global_dollar:
        return []
    return [make_error(
        CODE_NO_GLOBAL_CEILING,
        path,
        "spend_envelopes",
        (
            "a global '$' ceiling is mandatory whenever any '$' envelope is declared "
            "(the anti-catastrophe backstop); it stays even when the cap is opted out "
            "(the runaway-detection net). Add a {scope: global, unit: '$', ...} envelope"
        ),
        CONTRACT,
    )]


def _check_nested_consistency(envelopes: list[dict[str, Any]], path: Path) -> list[ValidationError]:
    """For $ envelopes sharing a window, inner cap must not exceed outer (Fork B)."""
    errors: list[ValidationError] = []
    by_window: dict[Any, list[dict[str, Any]]] = {}
    for env in envelopes:
        if env.get("unit") != "$":
            continue
        if _as_number(env.get("amount")) is None or env.get("scope") not in _SCOPE_RANK:
            continue
        by_window.setdefault(env.get("window"), []).append(env)
    for window, envs in by_window.items():
        ordered = sorted(envs, key=lambda e: _SCOPE_RANK[e["scope"]])
        # ordered = run, fleet, global; each inner amount must be <= every outer amount.
        for i, inner in enumerate(ordered):
            inner_amt = _as_number(inner.get("amount"))
            for outer in ordered[i + 1:]:
                outer_amt = _as_number(outer.get("amount"))
                if inner_amt is not None and outer_amt is not None and inner_amt > outer_amt:
                    errors.append(make_error(
                        CODE_ENVELOPE_INCONSISTENT,
                        path,
                        f"spend_envelopes[window={window!r}]",
                        (
                            f"inner '{inner['scope']}' cap {inner_amt} exceeds outer "
                            f"'{outer['scope']}' cap {outer_amt}; nested envelopes are "
                            "most-restrictive-wins (inner <= outer)"
                        ),
                        CONTRACT,
                    ))
    return errors


def validate_spend_envelope(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate the spend-governance predicates for one Runtime Policy record."""
    errors: list[ValidationError] = []
    errors.extend(_check_optout(record, path))
    raw = record.get("spend_envelopes")
    if not isinstance(raw, list) or not raw:
        return errors  # no spend governance declared — nothing further to check
    envelopes = [env for env in raw if isinstance(env, dict)]
    errors.extend(_check_global_ceiling(envelopes, path))
    errors.extend(_check_regime_units(envelopes, path))
    errors.extend(_check_nested_consistency(envelopes, path))
    return errors


@register(
    CHECK_NAME,
    [
        CODE_NO_GLOBAL_CEILING,
        CODE_ENVELOPE_INCONSISTENT,
        CODE_REGIME_UNIT,
        CODE_OPTOUT_UNRATIFIED,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_runtime_policy_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue  # ce_runtime_policy owns the non-mapping error
        errors.extend(validate_spend_envelope(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
