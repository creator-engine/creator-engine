"""The egress-broker per-App config schema + fail-closed loader (read AS DATA).

The broker is configured host-side with: the target ``repo``, the ``installation_owner`` (the
org an App is installed on — ``creator-engine`` — used for installation-id discovery), the
publish :class:`~egress_broker.policy.BrokerPolicy`, and a per-seat App table covering
dev-1/2/3/4. Each seat entry is the per-App identity the broker mints+pushes AS: ``app_id``
(the JWT ``iss`` — the App's numeric id or client id), ``app_owner`` (the GitHub identity that
owns the App, e.g. ``cedev4vps-coder``), and the App private key source — EITHER ``pem_path``
(legacy, host-local, RAM-only by convention — ``/dev/shm/ce-dev4/ce-forge-dev4.pem``) OR a
``secret_ref`` (vault-backed KV v2 reference ``{mount, path, field}`` for OpenBao custody;
preferred per ce-ops#266; ``secret_ref`` wins when both are present). ``installation_id`` is
the App installation to mint from (``None`` → discovered at run time, filtered to the org).

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
from typing import Optional

from egress_broker.policy import BrokerPolicy

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


class BrokerConfigError(Exception):
    """The broker config is missing / malformed / under-specified — a fail-closed refusal."""


@dataclass(frozen=True)
class VaultSecretRef:
    """A value-free KV v2 pointer to an App private key stored in OpenBao/Vault.

    ``mount`` is the KV v2 mount (e.g. ``ce-kv``); ``path`` is the secret path under that
    mount (e.g. ``forge/dev-3``); ``field`` is the field name inside the secret
    (e.g. ``private_key``). The secret VALUE is never present here — only the address.
    """

    mount: str
    path: str
    field: str

    def __repr__(self) -> str:
        return (
            f"VaultSecretRef(mount={self.mount!r}, path={self.path!r}, field={self.field!r})"
        )

    __str__ = __repr__


@dataclass(frozen=True)
class SeatAppConfig:
    """The per-App identity the broker mints + pushes AS for one seat.

    ``app_id`` is the GitHub App JWT issuer; ``app_owner`` the owning GitHub identity;
    ``pem_path`` the host-local (RAM-only by convention) App private key the openssl signer
    reads — it NEVER enters the broker process (legacy path, still valid for dev-2/dev-4);
    ``secret_ref`` the vault-backed KV v2 reference for the App private key (preferred per
    ce-ops#266; ``secret_ref`` wins over ``pem_path`` when both are present);
    ``installation_id`` is the App installation to mint from (``None`` → discovered at run
    time, filtered to the org).

    Exactly one of ``pem_path`` or ``secret_ref`` must be non-None. The config loader
    enforces this and the ``repr`` keeps the App id / pem path out of incidental log surfaces.
    """

    seat_id: str
    app_id: str
    app_owner: str
    pem_path: Optional[str]
    installation_id: int | None
    secret_ref: Optional[VaultSecretRef] = None

    def __repr__(self) -> str:  # keep App id / pem path out of incidental log/repr surfaces
        key_source = (
            f"secret_ref={self.secret_ref!r}"
            if self.secret_ref is not None
            else "pem_path=<host-local>"
        )
        return (
            f"SeatAppConfig(seat_id={self.seat_id!r}, app_owner={self.app_owner!r}, "
            f"app_id=<redacted>, {key_source}, "
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
    # require_signed_commits: fail-closed default True when key is absent. Explicitly False
    # (boolean) is the only accepted opt-out; any other falsy value (null, 0, "") keeps the
    # default True so a typo or missing key is never silently permissive.
    raw_rsc = raw.get("require_signed_commits")
    require_signed_commits = False if raw_rsc is False else True

    return BrokerPolicy(
        base_branch=base_branch,
        allowed_branch_namespaces=namespaces,
        forbidden_branches=forbidden,
        authorized_emails=emails,
        authorized_logins=logins,
        max_pushes_per_window=cap,
        window_seconds=window,
        require_signed_commits=require_signed_commits,
    )


def _build_vault_secret_ref(raw_ref: object, where: str) -> VaultSecretRef:
    """Parse and validate a ``secret_ref`` mapping from the config; fail-closed."""
    if not isinstance(raw_ref, Mapping):
        raise BrokerConfigError(f"{where} 'secret_ref' must be a mapping with mount/path/field")
    mount = str(raw_ref.get("mount") or "").strip()
    path = str(raw_ref.get("path") or "").strip()
    field = str(raw_ref.get("field") or "").strip()
    if not mount:
        raise BrokerConfigError(f"{where} 'secret_ref.mount' must be a non-empty string")
    if not path:
        raise BrokerConfigError(f"{where} 'secret_ref.path' must be a non-empty string")
    if not field:
        raise BrokerConfigError(f"{where} 'secret_ref.field' must be a non-empty string")
    return VaultSecretRef(mount=mount, path=path, field=field)


def _build_seat(seat_id: str, raw: object) -> SeatAppConfig:
    if not isinstance(raw, Mapping):
        raise BrokerConfigError(f"seat {seat_id!r} must be a mapping")
    where = f"seat {seat_id!r}"
    app_id = _require_str(raw, "app_id", where)
    app_owner = _require_str(raw, "app_owner", where)

    # Key source: prefer ``secret_ref`` (vault-backed); fall back to ``pem_path`` (legacy).
    # Exactly one of them must be provided.
    raw_secret_ref = raw.get("secret_ref")
    raw_pem_path = raw.get("pem_path")
    secret_ref: VaultSecretRef | None = None
    pem_path: str | None = None
    if raw_secret_ref is not None:
        secret_ref = _build_vault_secret_ref(raw_secret_ref, where)
    elif raw_pem_path is not None:
        pem_path_str = str(raw_pem_path).strip()
        if not pem_path_str:
            raise BrokerConfigError(f"{where} 'pem_path' must be a non-empty string when set")
        pem_path = str(Path(pem_path_str).expanduser())
    else:
        raise BrokerConfigError(
            f"{where} must specify exactly one of 'secret_ref' (vault-backed, preferred) "
            "or 'pem_path' (legacy host-local)"
        )

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
        secret_ref=secret_ref,
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
