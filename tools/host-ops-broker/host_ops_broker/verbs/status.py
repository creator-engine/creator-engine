"""Read-only ``status`` verb implementation with injectable adapters."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from host_ops_broker.verb_schema import STATUS_CLASSES


class StatusAdapter:
    """Interface for host subsystem status checks."""

    def check_daemons(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        raise NotImplementedError

    def check_systemd(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        raise NotImplementedError

    def check_containers(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        raise NotImplementedError

    def check_state_roots(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        raise NotImplementedError

    def check_openbao(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        raise NotImplementedError


class EmptyStatusAdapter(StatusAdapter):
    """Safe default for tests that only exercise broker ordering."""

    def _ok(self) -> Mapping[str, Any]:
        return {"state": "ok"}

    def check_daemons(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        return self._ok()

    def check_systemd(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        return self._ok()

    def check_containers(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        return self._ok()

    def check_state_roots(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        return self._ok()

    def check_openbao(self, *, target: str | None, detail: str) -> Mapping[str, Any]:
        return self._ok()


def run_status(params: Mapping[str, Any], adapter: StatusAdapter) -> dict[str, Any]:
    include = list(params.get("include") or STATUS_CLASSES)
    target = params.get("target")
    detail = str(params.get("detail") or "summary")
    health_summary: dict[str, Any] = {}
    degraded_checks: list[str] = []
    for check in include:
        method = getattr(adapter, f"check_{check}")
        try:
            health_summary[check] = dict(method(target=target, detail=detail))
        except Exception as exc:
            degraded_checks.append(check)
            health_summary[check] = {"state": "degraded", "error_class": exc.__class__.__name__}
    result = "degraded" if degraded_checks else "ok"
    return {
        "result": result,
        "changed": False,
        "details": {
            "include": include,
            "target": target,
            "detail": detail,
            "health_summary": health_summary,
            "degraded_checks": degraded_checks,
            "result": result,
        },
    }
