"""Dict-in/dict-out dispatcher for host-ops broker v1 Slice 1."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from host_ops_broker.audit import append_audit, build_record, now_z
from host_ops_broker.config import BrokerConfig, BrokerConfigError
from host_ops_broker.envelope import EnvelopeError, RequestEnvelope, response_envelope, validate_request
from host_ops_broker.kill_switch import check_kill_switch
from host_ops_broker.rate_limit import InMemoryRateLimiter
from host_ops_broker.verb_schema import MUTATING_VERBS, target_value
from host_ops_broker.verbs.restart_daemon import NoopSystemdAdapter, SystemdAdapter, run_restart_daemon
from host_ops_broker.verbs.status import EmptyStatusAdapter, StatusAdapter, run_status


class HostOpsBroker:
    def __init__(
        self,
        config: BrokerConfig,
        *,
        rate_limiter: InMemoryRateLimiter | None = None,
        status_adapter: StatusAdapter | None = None,
        systemd_adapter: SystemdAdapter | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.now = now or (lambda: datetime.now(timezone.utc))
        rules = dict(config.rate_limit_overrides)
        self.rate_limiter = rate_limiter or InMemoryRateLimiter(now=self.now, rules=rules)
        self.status_adapter = status_adapter or EmptyStatusAdapter()
        self.systemd_adapter = systemd_adapter or NoopSystemdAdapter()

    def dispatch(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        started_at = now_z(self.now)
        try:
            request = validate_request(raw)
        except (EnvelopeError, ValueError) as exc:
            request_id = str(raw.get("request_id", "unknown")) if isinstance(raw, Mapping) else "unknown"
            verb = str(raw.get("verb", "unknown")) if isinstance(raw, Mapping) else "unknown"
            return response_envelope(
                request_id,
                verb,
                "refused",
                details={"error_class": exc.__class__.__name__},
            )

        kill = check_kill_switch(self.config.kill_switch_path, request.verb)
        if kill.disabled:
            evidence_ref = self._append_final(
                request,
                started_at=started_at,
                target_ref=None,
                params_redacted=request.params,
                result="disabled",
                changed=False,
                rate_limit_key=None,
                disabled_scope=kill.disabled_scope,
                disabled_reason_ref=kill.disabled_reason_ref,
                evidence={"disabled_scope": kill.disabled_scope, "disabled_reason_ref": kill.disabled_reason_ref},
            )
            return response_envelope(
                request.request_id,
                request.verb,
                "disabled",
                evidence_ref=evidence_ref,
                details={"disabled_scope": kill.disabled_scope, "disabled_reason_ref": kill.disabled_reason_ref},
            )

        try:
            resolved = self._resolve_target(request)
        except BrokerConfigError as exc:
            evidence_ref = self._append_final(
                request,
                started_at=started_at,
                target_ref=None,
                params_redacted=request.params,
                result="refused",
                changed=False,
                rate_limit_key=None,
                disabled_scope=None,
                disabled_reason_ref=None,
                evidence={"error_class": "boundary", "message": str(exc)},
            )
            return response_envelope(
                request.request_id,
                request.verb,
                "refused",
                evidence_ref=evidence_ref,
                details={"error_class": "boundary"},
            )

        rate_target = target_value(request.verb, request.params)
        decision = self.rate_limiter.check_and_record(request.caller.identity, request.verb, rate_target)
        if not decision.allowed:
            evidence_ref = self._append_final(
                request,
                started_at=started_at,
                target_ref=resolved["target_ref"],
                params_redacted=request.params,
                result="rate-limited",
                changed=False,
                rate_limit_key=decision.key,
                disabled_scope=None,
                disabled_reason_ref=None,
                evidence={"limit": decision.limit, "window_seconds": decision.window_seconds, "used": decision.used},
            )
            return response_envelope(
                request.request_id,
                request.verb,
                "rate-limited",
                evidence_ref=evidence_ref,
                details={"rate_limit_key": decision.key},
            )

        if request.verb in MUTATING_VERBS:
            try:
                self._append_pre_mutation(request, started_at=started_at, target_ref=resolved["target_ref"], rate_limit_key=decision.key)
            except Exception as exc:
                return response_envelope(
                    request.request_id,
                    request.verb,
                    "failed",
                    details={"error_class": "audit-pre-mutation", "message": exc.__class__.__name__},
                )

        try:
            outcome = self._dispatch_handler(request, resolved)
        except Exception as exc:
            outcome = {
                "result": "failed",
                "changed": False,
                "details": {"error_class": exc.__class__.__name__, "result": "failed"},
            }
        try:
            evidence_ref = self._append_final(
                request,
                started_at=started_at,
                target_ref=resolved["target_ref"],
                params_redacted=request.params,
                result=outcome["result"],
                changed=bool(outcome.get("changed", False)),
                rate_limit_key=decision.key,
                disabled_scope=None,
                disabled_reason_ref=None,
                evidence=dict(outcome.get("details", {})),
            )
        except Exception:
            if bool(outcome.get("changed", False)):
                return response_envelope(
                    request.request_id,
                    request.verb,
                    "degraded",
                    changed=True,
                    details={"error_class": "audit-final"},
                )
            return response_envelope(
                request.request_id,
                request.verb,
                "failed",
                changed=False,
                details={"error_class": "audit-final"},
            )
        return response_envelope(
            request.request_id,
            request.verb,
            outcome["result"],
            changed=bool(outcome.get("changed", False)),
            evidence_ref=evidence_ref,
            details=dict(outcome.get("details", {})),
        )

    def _resolve_target(self, request: RequestEnvelope) -> dict[str, str | None]:
        if request.verb == "status":
            return {"target_ref": self.config.resolve_status_target(request.params.get("target")), "unit": None}
        if request.verb == "restart-daemon":
            unit = self.config.resolve_daemon(str(request.params["daemon"]))
            return {"target_ref": f"daemon:{request.params['daemon']}", "unit": unit}
        if request.verb == "repair-systemd-unit":
            unit = self.config.resolve_unit(str(request.params["unit"]))
            return {"target_ref": f"unit:{unit}", "unit": unit}
        # Deferred verbs still pass through a conservative config-bound target check.
        if request.verb == "prepare-owned-state-root" and request.params["root_name"] in self.config.state_roots:
            return {"target_ref": f"state-root:{request.params['root_name']}", "unit": None}
        if request.verb == "rotate-attempt-log" and request.params["subsystem"] in self.config.log_subsystems:
            return {"target_ref": f"log-subsystem:{request.params['subsystem']}", "unit": None}
        if request.verb == "run-ephemeral-container" and request.params["task"] in self.config.maintenance_tasks:
            return {"target_ref": f"task:{request.params['task']}", "unit": None}
        if request.verb == "prune-stopped-owned-containers" and request.params["namespace"] in self.config.container_namespaces:
            return {"target_ref": f"namespace:{request.params['namespace']}", "unit": None}
        if request.verb == "snapshot-openbao" and request.params["profile"] in self.config.backup_profiles:
            return {"target_ref": f"backup-profile:{request.params['profile']}", "unit": None}
        if request.verb == "restore-drill-openbao" and request.params["profile"] in self.config.backup_profiles:
            return {"target_ref": f"backup-profile:{request.params['profile']}", "unit": None}
        raise BrokerConfigError(f"{request.verb} target is not CE-owned or not implemented in Slice 1")

    def _dispatch_handler(self, request: RequestEnvelope, resolved: Mapping[str, str | None]) -> dict[str, Any]:
        if request.verb == "status":
            return run_status(request.params, self.status_adapter)
        if request.verb == "restart-daemon":
            return run_restart_daemon(request.params, unit=str(resolved["unit"]), adapter=self.systemd_adapter)
        return {"result": "refused", "changed": False, "details": {"error_class": "not-implemented", "result": "refused"}}

    def _append_pre_mutation(self, request: RequestEnvelope, *, started_at: str, target_ref: str | None, rate_limit_key: str) -> str:
        finished_at = now_z(self.now)
        record = build_record(
            request_id=request.request_id,
            verb=request.verb,
            caller_identity=request.caller.identity,
            caller_role=request.caller.role,
            work_claim=request.caller.work_claim,
            target_ref=target_ref,
            params_redacted=request.params,
            result="ok",
            changed=False,
            rate_limit_key=rate_limit_key,
            disabled_scope=None,
            disabled_reason_ref=None,
            broker_identity=self.config.broker_identity,
            evidence={"pre_mutation": True},
            started_at=started_at,
            finished_at=finished_at,
            event="pre-mutation",
        )
        append_audit(self.config.audit_log_path, record, now=self.now)
        return f"hostops-audit:{request.request_id}:pre-mutation"

    def _append_final(
        self,
        request: RequestEnvelope,
        *,
        started_at: str,
        target_ref: str | None,
        params_redacted: Mapping[str, Any],
        result: str,
        changed: bool,
        rate_limit_key: str | None,
        disabled_scope: str | None,
        disabled_reason_ref: str | None,
        evidence: Mapping[str, Any],
    ) -> str:
        finished_at = now_z(self.now)
        record = build_record(
            request_id=request.request_id,
            verb=request.verb,
            caller_identity=request.caller.identity,
            caller_role=request.caller.role,
            work_claim=request.caller.work_claim,
            target_ref=target_ref,
            params_redacted=params_redacted,
            result=result,
            changed=changed,
            rate_limit_key=rate_limit_key,
            disabled_scope=disabled_scope,
            disabled_reason_ref=disabled_reason_ref,
            broker_identity=self.config.broker_identity,
            evidence=evidence,
            started_at=started_at,
            finished_at=finished_at,
        )
        append_audit(self.config.audit_log_path, record, now=self.now)
        return f"hostops-audit:{request.request_id}:final"


def dispatch(raw: Mapping[str, Any], config: BrokerConfig, **kwargs: Any) -> dict[str, Any]:
    return HostOpsBroker(config, **kwargs).dispatch(raw)
