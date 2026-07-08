"""Fail-closed JSON config model for host-ops broker v1."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from host_ops_broker.rate_limit import RateLimitRule


class BrokerConfigError(Exception):
    """The broker config is missing, malformed, or under-specified."""


@dataclass(frozen=True)
class BrokerConfig:
    audit_log_path: str
    kill_switch_path: str
    broker_identity: str
    unit_allowlist: frozenset[str] = field(default_factory=frozenset)
    unit_prefixes: tuple[str, ...] = ()
    daemon_map: Mapping[str, str] = field(default_factory=dict)
    state_roots: Mapping[str, str] = field(default_factory=dict)
    state_root_prefixes: tuple[str, ...] = ()
    container_namespaces: frozenset[str] = field(default_factory=frozenset)
    backup_profiles: frozenset[str] = field(default_factory=frozenset)
    backup_destinations: frozenset[str] = field(default_factory=frozenset)
    log_subsystems: frozenset[str] = field(default_factory=frozenset)
    maintenance_tasks: frozenset[str] = field(default_factory=frozenset)
    rate_limit_overrides: Mapping[str, RateLimitRule] = field(default_factory=dict)
    repeated_failure_policy: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "BrokerConfig":
        p = Path(path).expanduser()
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise BrokerConfigError(f"config file {p} is missing") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise BrokerConfigError(f"config file {p} is unreadable or malformed") from exc
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "BrokerConfig":
        if not isinstance(raw, Mapping):
            raise BrokerConfigError("config must be a mapping")
        audit_log_path = _required_str(raw, "audit_log_path")
        kill_switch_path = _required_str(raw, "kill_switch_path")
        broker_identity = _required_str(raw, "broker_identity")
        daemon_map = _str_mapping(raw.get("daemon_map", {}), "daemon_map")
        unit_allowlist = frozenset(_str_list(raw.get("unit_allowlist", []), "unit_allowlist"))
        unit_prefixes = tuple(_str_list(raw.get("unit_prefixes", []), "unit_prefixes"))
        state_roots = _str_mapping(raw.get("state_roots", {}), "state_roots")
        state_root_prefixes = tuple(_str_list(raw.get("state_root_prefixes", []), "state_root_prefixes"))
        container_namespaces = frozenset(_str_list(raw.get("container_namespaces", []), "container_namespaces"))
        backup_profiles = frozenset(_str_list(raw.get("backup_profiles", []), "backup_profiles"))
        backup_destinations = frozenset(_str_list(raw.get("backup_destinations", []), "backup_destinations"))
        log_subsystems = frozenset(_str_list(raw.get("log_subsystems", []), "log_subsystems"))
        maintenance_tasks = frozenset(_str_list(raw.get("maintenance_tasks", []), "maintenance_tasks"))
        overrides = _rate_overrides(raw.get("rate_limit_overrides", {}))
        repeated = raw.get("repeated_failure_policy", {})
        if not isinstance(repeated, Mapping):
            raise BrokerConfigError("repeated_failure_policy must be a mapping")
        return cls(
            audit_log_path=audit_log_path,
            kill_switch_path=kill_switch_path,
            broker_identity=broker_identity,
            unit_allowlist=unit_allowlist,
            unit_prefixes=unit_prefixes,
            daemon_map=daemon_map,
            state_roots=state_roots,
            state_root_prefixes=state_root_prefixes,
            container_namespaces=container_namespaces,
            backup_profiles=backup_profiles,
            backup_destinations=backup_destinations,
            log_subsystems=log_subsystems,
            maintenance_tasks=maintenance_tasks,
            rate_limit_overrides=overrides,
            repeated_failure_policy=dict(repeated),
        )

    def resolve_unit(self, unit: str) -> str:
        if unit in self.unit_allowlist or any(unit.startswith(prefix) for prefix in self.unit_prefixes):
            return unit
        raise BrokerConfigError(f"unit {unit!r} is not CE-owned")

    def resolve_daemon(self, daemon: str) -> str:
        unit = self.daemon_map.get(daemon)
        if not unit:
            raise BrokerConfigError(f"daemon {daemon!r} is not CE-owned")
        return self.resolve_unit(unit)

    def resolve_status_target(self, target: str | None) -> str:
        if target is None:
            return "status:global"
        if target in self.daemon_map:
            return f"daemon:{target}"
        if target in self.unit_allowlist or any(target.startswith(prefix) for prefix in self.unit_prefixes):
            return f"unit:{target}"
        if target in self.container_namespaces:
            return f"namespace:{target}"
        if target in self.state_roots:
            return f"state-root:{target}"
        if target in self.backup_profiles:
            return f"backup-profile:{target}"
        raise BrokerConfigError(f"target {target!r} is not CE-owned")


def _required_str(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BrokerConfigError(f"{key} is required")
    return value


def _str_list(value: object, where: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise BrokerConfigError(f"{where} must be a list")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BrokerConfigError(f"{where} must contain non-empty strings")
        out.append(item)
    return out


def _str_mapping(value: object, where: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise BrokerConfigError(f"{where} must be a mapping")
    out = {}
    for key, val in value.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(val, str) or not val.strip():
            raise BrokerConfigError(f"{where} must map non-empty strings to non-empty strings")
        out[key] = val
    return out


def _rate_overrides(value: object) -> dict[str, RateLimitRule]:
    if not isinstance(value, Mapping):
        raise BrokerConfigError("rate_limit_overrides must be a mapping")
    out: dict[str, RateLimitRule] = {}
    for verb, raw_rule in value.items():
        if not isinstance(raw_rule, Mapping):
            raise BrokerConfigError("rate limit override entries must be mappings")
        try:
            limit = int(raw_rule["limit"])
            window_seconds = int(raw_rule["window_seconds"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BrokerConfigError("rate limit overrides require integer limit and window_seconds") from exc
        out[str(verb)] = RateLimitRule(limit=limit, window_seconds=window_seconds)
    return out
