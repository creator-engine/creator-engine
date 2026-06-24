"""The mint-broker host-side config schema + fail-closed loader (ce-ops#157, S3).

The standing shared-App mint broker is configured host-side (NOT from user input) with:

* ``app_client_id`` — the shared GitHub App's client id (the JWT ``iss``);
* ``pem_path`` — the App private key reference (RAM-only by convention, e.g.
  ``/dev/shm/…``). The openssl signer reads it directly; it NEVER enters the broker process;
* ``permission_ceiling`` — the v0 installation/broker ceiling the broker may EVER mint. v0 is
  read + ``contents:write`` + ``pull_requests:write`` and DELIBERATELY EXCLUDES
  ``administration:write`` (G3 two-token split: the standing broker never mints admin scope —
  the branch-protection floor is a separate one-shot elevated op);
* ``declared_minimum_grant`` — the explicit per-broker/task grant contract callers may request,
  itself bounded by ``permission_ceiling``. Requests outside this declared grant fail closed
  before binding or minting;
* ``per_user_rate_cap`` / ``rate_window_seconds`` — the per-user mint rate guard.

Fail-closed (mirrors ``egress_broker.config.load_broker_config``): a missing/malformed/empty
file, a missing client_id/pem_path, an empty ceiling/minimum grant, an ``administration:write``
(or any ``admin``-level) permission entry, a non-least-privilege level, a declared minimum above
the ceiling, or a bad rate cap/window is a
:class:`MintBrokerConfigError` — never a silent default. The loader reads the config as DATA and
copies no secret; the ``repr`` keeps the client id / pem path out of incidental log surfaces.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

#: Least-privilege levels the ceiling may grant (never ``admin``). ``read`` < ``write``.
_ALLOWED_LEVELS = ("read", "write")
_LEVEL_RANK = {"read": 0, "write": 1}
#: G3 — scopes the standing broker may NEVER mint, at any level (the protection floor is a
#: separate one-shot elevated op, not part of the default mint).
_NEVER_PERMISSION_SCOPES = frozenset(
    {"administration", "organization_administration", "secrets"}
)


class MintBrokerConfigError(Exception):
    """The mint-broker config is missing / malformed / over-ceiling — a fail-closed refusal."""


@dataclass(frozen=True)
class MintBrokerConfig:
    """The whole host-side mint-broker config — shared-App identity, key ref, grants, rate cap."""

    app_client_id: str
    pem_path: str
    audit_log: str
    permission_ceiling: Mapping[str, str]
    declared_minimum_grant: Mapping[str, str]
    per_user_rate_cap: int
    rate_window_seconds: int

    def permits(self, permissions: Mapping[str, str]) -> bool:
        """True iff EVERY requested ``(scope, level)`` is within the ceiling (read <= write).

        An empty request is never in-ceiling (a mint must name an explicit least-privilege set);
        an unknown scope or a level above the ceiling's level for that scope is out-of-ceiling.
        """
        return _permissions_within(permissions, self.permission_ceiling)

    def within_declared_minimum(self, permissions: Mapping[str, str]) -> bool:
        """True iff EVERY requested ``(scope, level)`` is within the declared grant.

        This is intentionally separate from :meth:`permits`: ``permission_ceiling`` is the
        installation/broker maximum, while ``declared_minimum_grant`` is the explicit grant
        surface this broker/task claims it needs. Over-asks fail against this narrower contract
        before rate accounting, binding, or minting.
        """
        return _permissions_within(permissions, self.declared_minimum_grant)

    def __repr__(self) -> str:  # keep the client id / pem path out of incidental log surfaces
        return (
            f"MintBrokerConfig(app_client_id=<redacted>, pem_path=<host-local>, "
            f"ceiling={dict(self.permission_ceiling)!r}, "
            f"declared_minimum_grant={dict(self.declared_minimum_grant)!r}, "
            f"per_user_rate_cap={self.per_user_rate_cap}, "
            f"rate_window_seconds={self.rate_window_seconds})"
        )

    __str__ = __repr__


def _require_str(d: Mapping, key: str) -> str:
    val = str(d.get(key) or "").strip()
    if not val:
        raise MintBrokerConfigError(f"mint-broker config is missing required non-empty '{key}'")
    return val


def _permissions_within(permissions: Mapping[str, str], grant: Mapping[str, str]) -> bool:
    if not permissions:
        return False
    for scope, level in permissions.items():
        grant_level = grant.get(str(scope))
        if grant_level is None:
            return False
        req_rank = _LEVEL_RANK.get(str(level))
        if req_rank is None:  # an unknown/admin level is never permitted
            return False
        if req_rank > _LEVEL_RANK[grant_level]:
            return False
    return True


def _build_permission_mapping(raw: object, *, field_name: str) -> dict[str, str]:
    if not isinstance(raw, Mapping) or not raw:
        raise MintBrokerConfigError(
            f"mint-broker config '{field_name}' must be a non-empty mapping "
            "(an empty permission grant could never authorize a mint — fail-closed)"
        )
    grant: dict[str, str] = {}
    for scope, level in raw.items():
        scope_s = str(scope).strip()
        level_s = str(level).strip()
        if not scope_s or not level_s:
            raise MintBrokerConfigError(f"{field_name} entries must be non-empty scope:level")
        if level_s not in _ALLOWED_LEVELS:
            raise MintBrokerConfigError(
                f"{field_name} level {level_s!r} for {scope_s!r} is not least-privilege "
                f"(allowed: {', '.join(_ALLOWED_LEVELS)}; the standing broker never mints admin)"
            )
        if scope_s in _NEVER_PERMISSION_SCOPES:
            raise MintBrokerConfigError(
                f"{field_name} may not include {scope_s!r} — the standing broker never mints "
                "it (G3: the protection floor is a separate one-shot elevated op)"
            )
        grant[scope_s] = level_s
    return grant


def _validate_declared_minimum_within_ceiling(
    declared_minimum_grant: Mapping[str, str], permission_ceiling: Mapping[str, str]
) -> None:
    for scope, level in declared_minimum_grant.items():
        ceiling_level = permission_ceiling.get(scope)
        if ceiling_level is None:
            raise MintBrokerConfigError(
                f"declared_minimum_grant scope {scope!r} is not present in permission_ceiling"
            )
        if _LEVEL_RANK[level] > _LEVEL_RANK[ceiling_level]:
            raise MintBrokerConfigError(
                f"declared_minimum_grant level {level!r} for {scope!r} exceeds "
                f"permission_ceiling level {ceiling_level!r}"
            )


def _require_int(d: Mapping, key: str, *, default: object = None, min_value: int) -> int:
    raw = d.get(key, default)
    try:
        val = int(raw)
    except (TypeError, ValueError):
        raise MintBrokerConfigError(f"mint-broker config '{key}' must be an integer") from None
    if val < min_value:
        raise MintBrokerConfigError(f"mint-broker config '{key}' must be >= {min_value}")
    return val


def load_mint_broker_config(source: str | Path | Mapping) -> MintBrokerConfig:
    """Read the mint-broker config (a path or an already-parsed mapping) AS DATA; fail-closed.

    Validates the shared-App client id, the key reference, the v0 permission ceiling and declared
    grant (rejecting ``administration:write`` / any admin level per G3), and the per-user rate
    cap/window. Refuses a missing/malformed file or any under-/over-specified field with
    :class:`MintBrokerConfigError`. Copies no secret; ``pem_path`` is ``~``-expanded but never read.
    """
    if isinstance(source, Mapping):
        data: object = source
    else:
        cfg_path = Path(source).expanduser()
        if not cfg_path.is_file():
            raise MintBrokerConfigError(f"mint-broker config not found at {cfg_path}")
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            raise MintBrokerConfigError(
                f"mint-broker config at {cfg_path} is not valid JSON: {exc}"
            ) from exc

    if not isinstance(data, Mapping) or not data:
        raise MintBrokerConfigError("mint-broker config must be a non-empty JSON object / mapping")

    app_client_id = _require_str(data, "app_client_id")
    pem_path = str(Path(_require_str(data, "pem_path")).expanduser())
    audit_log = str(data.get("audit_log") or "").strip()
    ceiling = _build_permission_mapping(
        data.get("permission_ceiling"), field_name="permission_ceiling"
    )
    declared_minimum_grant = _build_permission_mapping(
        data.get("declared_minimum_grant"), field_name="declared_minimum_grant"
    )
    _validate_declared_minimum_within_ceiling(declared_minimum_grant, ceiling)
    per_user_rate_cap = _require_int(data, "per_user_rate_cap", default=0, min_value=0)
    rate_window_seconds = _require_int(data, "rate_window_seconds", default=3600, min_value=1)

    return MintBrokerConfig(
        app_client_id=app_client_id,
        pem_path=pem_path,
        audit_log=audit_log,
        permission_ceiling=ceiling,
        declared_minimum_grant=declared_minimum_grant,
        per_user_rate_cap=per_user_rate_cap,
        rate_window_seconds=rate_window_seconds,
    )
