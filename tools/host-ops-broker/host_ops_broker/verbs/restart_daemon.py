"""``restart-daemon`` implementation with injectable systemd adapter."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SystemdAdapter:
    """Interface used by ``restart-daemon``; live implementation is a later slice."""

    def get_state(self, unit: str) -> Mapping[str, Any]:
        raise NotImplementedError

    def restart(self, unit: str, mode: str) -> None:
        raise NotImplementedError

    def wait_ready(self, unit: str, timeout_seconds: int) -> bool:
        raise NotImplementedError


class NoopSystemdAdapter(SystemdAdapter):
    def get_state(self, unit: str) -> Mapping[str, Any]:
        return {"active_state": "active", "sub_state": "running"}

    def restart(self, unit: str, mode: str) -> None:
        return None

    def wait_ready(self, unit: str, timeout_seconds: int) -> bool:
        return True


def run_restart_daemon(params: Mapping[str, Any], *, unit: str, adapter: SystemdAdapter) -> dict[str, Any]:
    daemon = str(params["daemon"])
    mode = str(params.get("mode") or "restart")
    wait_ready_seconds = int(params.get("wait_ready_seconds", 30))
    pre_state = dict(adapter.get_state(unit))
    if mode == "try-restart" and pre_state.get("active_state") != "active":
        return {
            "result": "already-converged",
            "changed": False,
            "details": {
                "daemon": daemon,
                "unit": unit,
                "mode": mode,
                "pre_state": pre_state,
                "post_state": pre_state,
                "wait_ready_seconds": wait_ready_seconds,
                "changed": False,
                "result": "already-converged",
            },
        }
    adapter.restart(unit, mode)
    ready = adapter.wait_ready(unit, wait_ready_seconds) if wait_ready_seconds else True
    post_state = dict(adapter.get_state(unit))
    ok = ready and post_state.get("active_state") == "active"
    result = "ok" if ok else "failed"
    return {
        "result": result,
        "changed": True,
        "details": {
            "daemon": daemon,
            "unit": unit,
            "mode": mode,
            "pre_state": pre_state,
            "post_state": post_state,
            "wait_ready_seconds": wait_ready_seconds,
            "changed": True,
            "result": result,
        },
    }
