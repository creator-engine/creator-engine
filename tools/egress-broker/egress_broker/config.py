"""The egress-broker per-App config schema + fail-closed loader (read AS DATA).

The broker is configured host-side with: the target ``repo``, the ``installation_owner`` (the
org an App is installed on — ``creator-engine`` — used for installation-id discovery), the
publish :class:`~egress_broker.policy.BrokerPolicy`, and a per-seat App table covering
dev-1/2/3/4. Each seat entry is the per-App identity the broker mints+pushes AS: ``app_id``
(the JWT ``iss`` — the App's numeric id or client id), ``app_owner`` (the GitHub identity that
owns the App, e.g. ``cedev4vps-coder``), ``pem_path`` (host-local, RAM-only by convention —
``/dev/shm/ce-dev4/ce-forge-dev4.pem``), and an optional ``installation_id`` (discovered at
run time when absent — dev-4's env does not record it).

Fail-closed (mirrors ``v3_forge_join.load_app_config``): a missing file, malformed JSON, a bad
``repo``, an empty seat table, an empty author allow-list (a broker that could authorize no one
is misconfigured), or a malformed seat is a :class:`BrokerConfigError` — never a silent
default. The loader reads the config as DATA and copies no secret anywhere; the per-seat
``repr`` keeps the App id / pem path out of incidental log surfaces.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from egress_broker.policy import BrokerPolicy

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


class BrokerConfigError(Exception):
    """The broker config is missing / malformed / under-specified — a fail-closed refusal."""


@dataclass(frozen=True)
class SeatAppConfig:
    """The per-App identity the broker mints + pushes AS for one seat.

    ``app_id`` is the GitHub App JWT issuer; ``app_owner`` the owning GitHub identity;
    ``pem_path`` the host-local (RAM-only by convention) App private key the openssl signer
    reads — it NEVER enters the broker process; ``installation_id`` is the App installation to
    mint from (``None`` → discovered at run time, filtered to the org).
    """

    seat_id: str
    app_id: str
    app_owner: str
    pem_path: str
    installation_id: int | None

    def __repr__(self) -> str:  # keep App id / pem path out of incidental log/repr surfaces
        return (
            f"SeatAppConfig(seat_id={self.seat_id!r}, app_owner={self.app_owner!r}, "
            f"app_id=<redacted>, pem_path=<host-local>, "
            f"installation_id={'<discover>' if self.installation_id is None else '<set>'})"
        )

    __str__ = __repr__


@dataclass(frozen=True)
class BrokerConfig:
    """The whole host-side broker config — repo, installation owner, policy, per-seat Apps."""

    repo: str
    installation_owner: str
    audit_log: str
    policy: BrokerPolicy
    seats: Mapping[str, SeatAppConfig]

    def seat(self, seat_id: str) -> SeatAppConfig:
        """Return the seat's App config; refuse an unknown seat (fail-closed)."""
        cfg = self.seats.get(seat_id)
        if cfg is None:
            raise BrokerConfigError(
                f"seat {seat_id!r} is not in the broker config (known: {sorted(self.seats)})"
            )
        return cfg


def _require_str(d: Mapping, key: str, where: str) -> str:
    val = str(d.get(key) or "").strip()
    if not val:
        raise BrokerConfigError(f"{where} is missing required non-empty '{key}'")
    return val


def _build_policy(raw: object) -> BrokerPolicy:
    if not isinstance(raw, Mapping):
        raise BrokerConfigError("'policy' must be a mapping")
    base_branch = _require_str(raw, "base_branch", "policy")
    namespaces = tuple(str(x) for x in (raw.get("allowed_branch_namespaces") or ()) if str(x))
    if not namespaces:
        raise BrokerConfigError(
            "policy.allowed_branch_namespaces must list at least one allowed namespace prefix"
        )
    forbidden = frozenset(str(x).strip() for x in (raw.get("forbidden_branches") or ()) if str(x).strip())
    emails = frozenset(str(x).strip().lower() for x in (raw.get("authorized_emails") or ()) if str(x).strip())
    logins = frozenset(str(x).strip() for x in (raw.get("authorized_logins") or ()) if str(x).strip())
    if not emails and not logins:
        raise BrokerConfigError(
            "policy must authorize at least one identity (authorized_emails / authorized_logins); "
            "an empty allow-list could never authorize a push (fail-closed)"
        )
    try:
        cap = int(raw.get("max_pushes_per_window", 0))
    except (TypeError, ValueError):
        raise BrokerConfigError("policy.max_pushes_per_window must be an integer") from None
    if cap < 0:
        raise BrokerConfigError("policy.max_pushes_per_window must be >= 0 (0 disables the guard)")
    try:
        window = int(raw.get("window_seconds", 3600))
    except (TypeError, ValueError):
        raise BrokerConfigError("policy.window_seconds must be an integer") from None
    if window <= 0:
        raise BrokerConfigError("policy.window_seconds must be positive")
    return BrokerPolicy(
        base_branch=base_branch,
        allowed_branch_namespaces=namespaces,
        forbidden_branches=forbidden,
        authorized_emails=emails,
        authorized_logins=logins,
        max_pushes_per_window=cap,
        window_seconds=window,
    )


def _build_seat(seat_id: str, raw: object) -> SeatAppConfig:
    if not isinstance(raw, Mapping):
        raise BrokerConfigError(f"seat {seat_id!r} must be a mapping")
    where = f"seat {seat_id!r}"
    app_id = _require_str(raw, "app_id", where)
    app_owner = _require_str(raw, "app_owner", where)
    pem_path = _require_str(raw, "pem_path", where)
    pem_path = str(Path(pem_path).expanduser())
    raw_inst = raw.get("installation_id")
    installation_id: int | None
    if raw_inst is None:
        installation_id = None
    else:
        try:
            installation_id = int(raw_inst)
        except (TypeError, ValueError):
            raise BrokerConfigError(
                f"{where} 'installation_id' must be a positive int or null (got {raw_inst!r})"
            ) from None
        if installation_id <= 0:
            raise BrokerConfigError(f"{where} 'installation_id' must be positive when set")
    return SeatAppConfig(
        seat_id=seat_id,
        app_id=app_id,
        app_owner=app_owner,
        pem_path=pem_path,
        installation_id=installation_id,
    )


def load_broker_config(source: str | Path | Mapping) -> BrokerConfig:
    """Read the broker config (a path or an already-parsed mapping) AS DATA; fail-closed.

    Validates the repo, installation owner, policy, and per-seat App table; refuses a
    missing/malformed file, an empty seat table, an empty author allow-list, an empty namespace
    list, or a malformed seat. Copies no secret; ``pem_path`` is ``~``-expanded but never read.
    """
    if isinstance(source, Mapping):
        data: object = source
    else:
        cfg_path = Path(source).expanduser()
        if not cfg_path.is_file():
            raise BrokerConfigError(f"broker config not found at {cfg_path}")
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            raise BrokerConfigError(f"broker config at {cfg_path} is not valid JSON: {exc}") from exc

    if not isinstance(data, Mapping):
        raise BrokerConfigError("broker config must be a JSON object / mapping")

    repo = _require_str(data, "repo", "broker config")
    if not _REPO_RE.match(repo):
        raise BrokerConfigError(f"broker config 'repo' {repo!r} is not in owner/name form")
    installation_owner = _require_str(data, "installation_owner", "broker config")
    audit_log = str(data.get("audit_log") or "").strip()

    policy = _build_policy(data.get("policy"))

    seats_raw = data.get("seats")
    if not isinstance(seats_raw, Mapping) or not seats_raw:
        raise BrokerConfigError("broker config 'seats' must be a non-empty mapping of seat_id -> App")
    seats = {sid: _build_seat(sid, entry) for sid, entry in seats_raw.items()}

    return BrokerConfig(
        repo=repo,
        installation_owner=installation_owner,
        audit_log=audit_log,
        policy=policy,
        seats=seats,
    )
