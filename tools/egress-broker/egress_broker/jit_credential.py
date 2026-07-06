"""JIT seat credential mint/revoke lane for the host broker.

The contained seat asks the host broker for a named class; the host validates the
per-seat allowlist, mints at request time, and returns the secret only in the
already-authenticated Unix socket response. No Docker/env/argv/config delivery
surface is created here.
"""
from __future__ import annotations

import fcntl
import os
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from creator_engine_validator.forge.credential_runner import authenticated_gh_runner
from creator_engine_validator.forge.github_repo_config import ForgeConfigError, ForgeConfigRefused
from creator_engine_validator.forge.scoped_token import (
    ScopedToken,
    TokenRequest,
    revoke_scoped_token,
)
from egress_broker.audit import append_audit
from egress_broker.config import BrokerConfig, BrokerConfigError, SeatAppConfig
from egress_broker.minter import mint_egress_token, resolve_installation_id
from egress_broker.orchestrator import policy_binding_sha

SUPPORTED_CREDENTIAL_CLASSES = frozenset({"model-api", "forge-scoped"})
MODEL_API_TTL_SECONDS = 300
FORGE_SCOPED_TTL_SECONDS = 300
FORGE_SCOPED_PERMISSIONS = {"metadata": "read", "issues": "read", "pull_requests": "read"}
FORGE_SCOPED_SECRET_NAME = "forge_scoped_jit"
MODEL_API_SECRET_NAME = "model_api_jit"


class JitCredentialRefused(Exception):
    """A fail-closed credential mint/revoke refusal."""

    def __init__(self, message: str, *, status: int = 403, reason: str = "refused"):
        super().__init__(message)
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class ModelCredential:
    """Host-supplied model credential material.

    A production deployment should supply this from the host harness/secret broker.
    The value is returned only over the broker socket; ``credential_ref`` is a
    non-secret handle used for audit/state correlation.
    """

    value: str
    expires_at: str
    credential_ref: str


@dataclass
class _ActiveCredential:
    seat_id: str
    credential_class: str
    value: str
    expires_at: datetime
    credential_ref: str
    revoker: Callable[[], bool]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: datetime | float | int | None) -> datetime:
    if value is None:
        return _utc_now()
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_expires_at(value: str, *, fallback_now: datetime, ttl_seconds: int) -> datetime:
    raw = str(value or "").strip()
    if raw:
        try:
            normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return fallback_now + timedelta(seconds=ttl_seconds)


def _default_lock_path() -> Path:
    return Path(os.environ.get("CE_EGRESS_JIT_CREDENTIAL_LOCK", "/tmp/ce-egress-jit-credential.lock"))


class SeatCredentialStore:
    """In-memory active credential registry protected by a host flock.

    The registry is deliberately process-local. Cross-process single-active behavior depends on
    the deployment's one live broker process per seat/socket guard, while the flock serializes
    concurrent request handling inside that process.
    """

    def __init__(self, lock_path: str | Path | None = None):
        self.lock_path = Path(lock_path) if lock_path is not None else _default_lock_path()
        self._active: dict[tuple[str, str], _ActiveCredential] = {}
        self._timers: dict[tuple[str, str], threading.Timer] = {}

    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        return _Flock(fd)

    def revoke_if_active(
        self,
        seat_id: str,
        credential_class: str,
        *,
        now: datetime,
        audit: Callable[[str, str | None, str | None], None],
    ) -> bool:
        with self._locked():
            self._expire_locked(now=now, audit=audit)
            active = self._active.pop((seat_id, credential_class), None)
            if active is None:
                return False
            self._cancel_timer((seat_id, credential_class))
            _best_effort_revoke(active)
            return True

    def replace_active(
        self,
        active: _ActiveCredential,
        *,
        now: datetime,
        audit: Callable[[str, str | None, str | None], None],
        mint: Callable[[], _ActiveCredential],
    ) -> _ActiveCredential:
        with self._locked():
            self._expire_locked(now=now, audit=audit)
            previous = self._active.pop((active.seat_id, active.credential_class), None)
            if previous is not None:
                self._cancel_timer((previous.seat_id, previous.credential_class))
                _best_effort_revoke(previous)
                audit("replace", previous.credential_ref, "single_active_replaced")
            minted = mint()
            key = (minted.seat_id, minted.credential_class)
            self._active[key] = minted
            self._schedule_expiry(key, minted, audit=audit, now=now)
            return minted

    def _expire_locked(
        self,
        *,
        now: datetime,
        audit: Callable[[str, str | None, str | None], None],
    ) -> None:
        expired = [key for key, active in self._active.items() if active.expires_at <= now]
        for key in expired:
            active = self._active.pop(key)
            self._cancel_timer(key)
            _best_effort_revoke(active)
            audit("expire", active.credential_ref, "ttl_expired")

    def _schedule_expiry(
        self,
        key: tuple[str, str],
        active: _ActiveCredential,
        *,
        audit: Callable[[str, str | None, str | None], None],
        now: datetime,
    ) -> None:
        delay = max(0.0, (active.expires_at - now).total_seconds())
        timer = threading.Timer(delay, self._expire_one, args=(key, active.credential_ref, audit))
        timer.daemon = True
        self._timers[key] = timer
        timer.start()

    def _expire_one(
        self,
        key: tuple[str, str],
        credential_ref: str,
        audit: Callable[[str, str | None, str | None], None],
    ) -> None:
        with self._locked():
            active = self._active.get(key)
            if active is None or active.credential_ref != credential_ref:
                return
            self._active.pop(key, None)
            self._timers.pop(key, None)
            _best_effort_revoke(active)
            audit("expire", active.credential_ref, "ttl_expired")

    def _cancel_timer(self, key: tuple[str, str]) -> None:
        timer = self._timers.pop(key, None)
        if timer is not None:
            timer.cancel()


class _Flock:
    def __init__(self, fd: int):
        self.fd = fd

    def __enter__(self):
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)


_DEFAULT_STORE = SeatCredentialStore()


def _best_effort_revoke(active: _ActiveCredential) -> None:
    try:
        active.revoker()
    except Exception:
        pass


def _audit(
    config: BrokerConfig,
    *,
    seat_id: str,
    credential_class: str,
    action: str,
    decision: str,
    reason: str | None = None,
    credential_ref: str | None = None,
    expires_at: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "event": "seat_jit_credential",
        "seat_id": seat_id,
        "class": credential_class,
        "action": action,
        "decision": decision,
    }
    if reason:
        record["reason"] = reason
    if credential_ref:
        record["ref"] = credential_ref
    if expires_at:
        record["expires_at"] = expires_at
    return append_audit(config.audit_log, record, now=now)


def _validate_class(config: BrokerConfig, seat_id: str, credential_class: str) -> SeatAppConfig:
    if credential_class not in SUPPORTED_CREDENTIAL_CLASSES:
        raise JitCredentialRefused(
            f"unknown credential class {credential_class!r}",
            status=403,
            reason="unknown_credential_class",
        )
    try:
        seat = config.seat(seat_id)
    except BrokerConfigError as exc:
        raise JitCredentialRefused(str(exc), status=403, reason="unknown_seat") from exc
    if credential_class not in seat.allowed_credential_classes:
        raise JitCredentialRefused(
            f"credential class {credential_class!r} is not allowed for seat {seat_id!r}",
            status=403,
            reason="credential_class_not_allowed",
        )
    return seat


def mint_seat_credential(
    seat_id: str,
    credential_class: str,
    *,
    config: BrokerConfig,
    store: SeatCredentialStore | None = None,
    signer=None,
    transport=None,
    gh_spawn=None,
    now: Callable[[], datetime | float | int] | None = None,
    audit_now: Callable[[], datetime] | None = None,
    resolve_id_fn: Callable[[SeatAppConfig], int] | None = None,
    mint_fn: Callable[[TokenRequest], ScopedToken] | None = None,
    revoke_fn: Callable[[Any], bool] | None = None,
    model_mint_fn: Callable[[str, int], ModelCredential] | None = None,
) -> dict[str, Any]:
    """Mint one active credential for ``seat_id``/``credential_class``."""
    current = _coerce_datetime((now or _utc_now)())
    state = store or _DEFAULT_STORE

    def audit(action: str, ref: str | None, reason: str | None) -> None:
        _audit(
            config,
            seat_id=seat_id,
            credential_class=credential_class,
            action=action,
            decision="allow",
            reason=reason,
            credential_ref=ref,
            now=audit_now,
        )

    try:
        seat = _validate_class(config, seat_id, credential_class)
    except JitCredentialRefused as exc:
        audit_record = _audit(
            config,
            seat_id=seat_id,
            credential_class=credential_class,
            action="mint",
            decision="deny",
            reason=exc.reason,
            now=audit_now,
        )
        return {"status": exc.status, "reason": exc.reason, "detail": str(exc), "audit_record": audit_record}

    placeholder = _ActiveCredential(
        seat_id=seat_id,
        credential_class=credential_class,
        value="",
        expires_at=current,
        credential_ref="pending",
        revoker=lambda: True,
    )

    try:
        active = state.replace_active(
            placeholder,
            now=current,
            audit=audit,
            mint=lambda: _mint_active(
                seat,
                credential_class,
                config=config,
                signer=signer,
                transport=transport,
                gh_spawn=gh_spawn,
                now=current,
                resolve_id_fn=resolve_id_fn,
                mint_fn=mint_fn,
                revoke_fn=revoke_fn,
                model_mint_fn=model_mint_fn,
            ),
        )
    except (JitCredentialRefused, ForgeConfigError, ForgeConfigRefused) as exc:
        reason = getattr(exc, "reason", "mint_refused")
        audit_record = _audit(
            config,
            seat_id=seat_id,
            credential_class=credential_class,
            action="mint",
            decision="deny",
            reason=str(reason),
            now=audit_now,
        )
        return {"status": 403, "reason": str(reason), "detail": str(exc), "audit_record": audit_record}

    audit_record = _audit(
        config,
        seat_id=seat_id,
        credential_class=credential_class,
        action="mint",
        decision="allow",
        credential_ref=active.credential_ref,
        expires_at=_iso(active.expires_at),
        now=audit_now,
    )
    return {
        "status": 200,
        "seat_id": seat_id,
        "credential_class": credential_class,
        "credential": active.value,
        "expires_at": _iso(active.expires_at),
        "credential_ref": active.credential_ref,
        "delivery": "broker-socket-stream",
        "audit_record": audit_record,
    }


def _mint_active(
    seat: SeatAppConfig,
    credential_class: str,
    *,
    config: BrokerConfig,
    signer,
    transport,
    gh_spawn,
    now: datetime,
    resolve_id_fn: Callable[[SeatAppConfig], int] | None,
    mint_fn: Callable[[TokenRequest], ScopedToken] | None,
    revoke_fn: Callable[[Any], bool] | None,
    model_mint_fn: Callable[[str, int], ModelCredential] | None,
) -> _ActiveCredential:
    if credential_class == "model-api":
        if model_mint_fn is None:
            raise JitCredentialRefused(
                "no host model-api credential supplier configured",
                status=403,
                reason="model_api_supplier_missing",
            )
        material = model_mint_fn(seat.seat_id, MODEL_API_TTL_SECONDS)
        if not material.value:
            raise JitCredentialRefused(
                "model-api credential supplier returned no value",
                status=403,
                reason="empty_model_api_credential",
            )
        expires_at = _parse_expires_at(
            material.expires_at, fallback_now=now, ttl_seconds=MODEL_API_TTL_SECONDS
        )

        def revoke_model() -> bool:
            if revoke_fn is not None:
                return bool(revoke_fn(material))
            return True

        return _ActiveCredential(
            seat_id=seat.seat_id,
            credential_class=credential_class,
            value=material.value,
            expires_at=expires_at,
            credential_ref=material.credential_ref,
            revoker=revoke_model,
        )

    if credential_class == "forge-scoped":
        if signer is None:
            from egress_broker.minter import make_signer_for_seat

            signer = make_signer_for_seat(seat)
        resolver = resolve_id_fn or (
            lambda s: resolve_installation_id(
                s,
                installation_owner=config.installation_owner,
                signer=signer,
                transport=transport,
            )
        )
        installation_id = resolver(seat)
        request = TokenRequest(
            repo=seat.repo,
            installation_id=installation_id,
            run_id=f"jit-{seat.seat_id}-{credential_class}",
            policy_sha=policy_binding_sha(config, repo=seat.repo),
            permissions=dict(FORGE_SCOPED_PERMISSIONS),
            secret_name=FORGE_SCOPED_SECRET_NAME,
            requested_ttl_seconds=FORGE_SCOPED_TTL_SECONDS,
            escalation_authority=(),
        )

        def default_mint(token_request: TokenRequest) -> ScopedToken:
            return mint_egress_token(
                replace(seat, installation_id=token_request.installation_id),
                repo=token_request.repo,
                installation_owner=config.installation_owner,
                signer=signer,
                run_id=token_request.run_id,
                policy_sha=token_request.policy_sha,
                permissions=token_request.permissions,
                escalation_authority=token_request.escalation_authority,
                ttl_seconds=token_request.requested_ttl_seconds,
                secret_name=token_request.secret_name,
                transport=transport,
            )

        token = (mint_fn or default_mint)(request)
        expires_at = _parse_expires_at(
            token.expires_at, fallback_now=now, ttl_seconds=FORGE_SCOPED_TTL_SECONDS
        )

        def revoke_forge() -> bool:
            if revoke_fn is not None:
                return bool(revoke_fn(token))
            runner = authenticated_gh_runner(token, spawn=gh_spawn)
            return revoke_scoped_token(token, gh_runner=runner)

        return _ActiveCredential(
            seat_id=seat.seat_id,
            credential_class=credential_class,
            value=token.value,
            expires_at=expires_at,
            credential_ref=token.token_ref,
            revoker=revoke_forge,
        )

    raise JitCredentialRefused(
        f"unknown credential class {credential_class!r}",
        status=403,
        reason="unknown_credential_class",
    )


def revoke_seat_credential(
    seat_id: str,
    credential_class: str,
    *,
    config: BrokerConfig,
    store: SeatCredentialStore | None = None,
    now: Callable[[], datetime | float | int] | None = None,
    audit_now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Explicitly revoke the active credential for ``seat_id``/``credential_class``."""
    current = _coerce_datetime((now or _utc_now)())
    state = store or _DEFAULT_STORE

    def audit(action: str, ref: str | None, reason: str | None) -> None:
        _audit(
            config,
            seat_id=seat_id,
            credential_class=credential_class,
            action=action,
            decision="allow",
            reason=reason,
            credential_ref=ref,
            now=audit_now,
        )

    try:
        _validate_class(config, seat_id, credential_class)
    except JitCredentialRefused as exc:
        audit_record = _audit(
            config,
            seat_id=seat_id,
            credential_class=credential_class,
            action="revoke",
            decision="deny",
            reason=exc.reason,
            now=audit_now,
        )
        return {"status": exc.status, "reason": exc.reason, "detail": str(exc), "audit_record": audit_record}

    revoked = state.revoke_if_active(
        seat_id,
        credential_class,
        now=current,
        audit=audit,
    )
    if not revoked:
        audit_record = _audit(
            config,
            seat_id=seat_id,
            credential_class=credential_class,
            action="revoke",
            decision="deny",
            reason="no_active_credential",
            now=audit_now,
        )
        return {
            "status": 404,
            "reason": "no_active_credential",
            "seat_id": seat_id,
            "credential_class": credential_class,
            "audit_record": audit_record,
        }

    audit_record = _audit(
        config,
        seat_id=seat_id,
        credential_class=credential_class,
        action="revoke",
        decision="allow",
        now=audit_now,
    )
    return {
        "status": 200,
        "seat_id": seat_id,
        "credential_class": credential_class,
        "revoked": True,
        "audit_record": audit_record,
    }
