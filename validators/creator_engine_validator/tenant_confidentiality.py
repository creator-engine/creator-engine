"""Tenant confidentiality denylist matrix.

Tenant records name a ``confidentiality.denylist_ref``. This module turns those
refs into a small, explicit matrix used by the public-repo confidentiality
guard:

* tenant identifiers are forbidden on CE public surfaces and other tenants'
  venues;
* CE's standing forbidden patterns remain owned by the caller and are always
  applied outside this module;
* per-tenant allowlists are exact file/pattern debt ratchets.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable

from .loader import LoaderError, load_yaml

TENANT_RECORD_ROOTS = (
    Path("governance/tenants"),
    Path(".ce/tenants"),
    Path("tenants"),
)


class TenantConfidentialityError(ValueError):
    """Raised when a tenant denylist record is malformed or unreadable."""


@dataclass(frozen=True)
class TenantPattern:
    tenant_id: str
    label: str
    pattern: re.Pattern[str]

    @property
    def formatted_label(self) -> str:
        return f"tenant {self.tenant_id} denylist: {self.label}"


@dataclass(frozen=True)
class TenantAllowlistEntry:
    tenant_id: str
    path: str
    pattern_label: str
    reason: str

    @property
    def formatted_label(self) -> str:
        return f"tenant {self.tenant_id} denylist: {self.pattern_label}"

    def format_stale(self, detail: str) -> str:
        return f"{self.path}:0 [tenant allowlist stale] {self.formatted_label} ({detail})"


@dataclass(frozen=True)
class TenantDenylist:
    tenant_id: str
    patterns: tuple[TenantPattern, ...]
    venue_paths: tuple[str, ...]
    allowlist: tuple[TenantAllowlistEntry, ...] = ()

    def owns_path(self, rel: str) -> bool:
        return any(_matches_path_prefix(rel, prefix) for prefix in self.venue_paths)


@dataclass(frozen=True)
class TenantDenylistMatrix:
    tenants: tuple[TenantDenylist, ...] = ()

    def tenant_for_path(self, rel: str) -> str | None:
        matches = [tenant for tenant in self.tenants if tenant.owns_path(rel)]
        if not matches:
            return None
        matches.sort(key=lambda tenant: max(len(path) for path in tenant.venue_paths), reverse=True)
        return matches[0].tenant_id

    def patterns_for_path(self, rel: str) -> tuple[tuple[str, re.Pattern[str]], ...]:
        target_tenant = self.tenant_for_path(rel)
        pairs: list[tuple[str, re.Pattern[str]]] = []
        for tenant in self.tenants:
            if target_tenant == tenant.tenant_id:
                continue
            pairs.extend((pattern.formatted_label, pattern.pattern) for pattern in tenant.patterns)
        return tuple(pairs)

    def allowlist_entries(self) -> tuple[TenantAllowlistEntry, ...]:
        return tuple(entry for tenant in self.tenants for entry in tenant.allowlist)

    def is_allowlisted(self, rel: str, label: str) -> bool:
        return any(entry.path == rel and entry.formatted_label == label for entry in self.allowlist_entries())

    def stale_allowlist_lines(
        self,
        *,
        raw_offense_keys: set[tuple[str, str]],
        existing_paths: set[str],
    ) -> list[str]:
        stale: list[str] = []
        for entry in self.allowlist_entries():
            if entry.path not in existing_paths:
                stale.append(entry.format_stale("file no longer exists"))
                continue
            if (entry.path, entry.formatted_label) not in raw_offense_keys:
                stale.append(entry.format_stale("file no longer has this tenant offense"))
        return stale


EMPTY_TENANT_DENYLIST_MATRIX = TenantDenylistMatrix()


def _matches_path_prefix(rel: str, prefix: str) -> bool:
    normalized = _normalize_rel(prefix)
    if normalized.endswith("/"):
        return rel.startswith(normalized)
    return rel == normalized or rel.startswith(f"{normalized}/")


def _normalize_rel(value: str) -> str:
    rel = value.replace("\\", "/").lstrip("/")
    if not rel or rel == "." or rel.startswith("../") or "/../" in rel:
        raise TenantConfidentialityError(f"invalid repo-relative path: {value!r}")
    return rel


def _resolve_repo_ref(root: Path, ref: str) -> Path:
    rel = _normalize_rel(ref)
    target = (root / rel).resolve()
    root_resolved = root.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise TenantConfidentialityError(f"denylist_ref escapes repo root: {ref!r}") from exc
    return target


def _as_mapping(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TenantConfidentialityError(f"{context} must be a mapping")
    return value


def _required_str(mapping: dict[str, Any], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TenantConfidentialityError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _check_keys(mapping: dict[str, Any], allowed: set[str], *, context: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise TenantConfidentialityError(f"{context} has unsupported keys: {', '.join(unknown)}")


def _parse_patterns(raw: Any, *, tenant_id: str, path: Path) -> tuple[TenantPattern, ...]:
    if not isinstance(raw, list) or not raw:
        raise TenantConfidentialityError(f"{path}: patterns must be a non-empty list")
    patterns: list[TenantPattern] = []
    labels: set[str] = set()
    for index, item in enumerate(raw):
        mapping = _as_mapping(item, context=f"{path}: patterns[{index}]")
        _check_keys(mapping, {"label", "pattern", "case_sensitive"}, context=f"{path}: patterns[{index}]")
        label = _required_str(mapping, "label", context=f"{path}: patterns[{index}]")
        if label in labels:
            raise TenantConfidentialityError(f"{path}: duplicate pattern label {label!r}")
        pattern_text = _required_str(mapping, "pattern", context=f"{path}: patterns[{index}]")
        flags = 0 if mapping.get("case_sensitive") is True else re.IGNORECASE
        try:
            compiled = re.compile(pattern_text, flags)
        except re.error as exc:
            raise TenantConfidentialityError(f"{path}: invalid regex for pattern {label!r}: {exc}") from exc
        labels.add(label)
        patterns.append(TenantPattern(tenant_id=tenant_id, label=label, pattern=compiled))
    return tuple(patterns)


def _parse_venue_paths(raw: Any, *, path: Path) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise TenantConfidentialityError(f"{path}: venue_paths must be a non-empty list")
    return tuple(_normalize_rel(str(item)) for item in raw)


def _parse_allowlist(
    raw: Any,
    *,
    tenant_id: str,
    pattern_labels: set[str],
    path: Path,
) -> tuple[TenantAllowlistEntry, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise TenantConfidentialityError(f"{path}: allowlist must be a list")
    entries: list[TenantAllowlistEntry] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(raw):
        mapping = _as_mapping(item, context=f"{path}: allowlist[{index}]")
        _check_keys(mapping, {"path", "pattern_label", "reason"}, context=f"{path}: allowlist[{index}]")
        rel = _normalize_rel(_required_str(mapping, "path", context=f"{path}: allowlist[{index}]"))
        label = _required_str(mapping, "pattern_label", context=f"{path}: allowlist[{index}]")
        if label not in pattern_labels:
            raise TenantConfidentialityError(f"{path}: allowlist references unknown pattern label {label!r}")
        reason = _required_str(mapping, "reason", context=f"{path}: allowlist[{index}]")
        key = (rel, label)
        if key in seen:
            raise TenantConfidentialityError(f"{path}: duplicate allowlist entry for {rel!r} / {label!r}")
        seen.add(key)
        entries.append(
            TenantAllowlistEntry(
                tenant_id=tenant_id,
                path=rel,
                pattern_label=label,
                reason=reason,
            )
        )
    return tuple(entries)


def load_tenant_denylist(path: Path, *, expected_tenant_id: str | None = None) -> TenantDenylist:
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        raise TenantConfidentialityError(str(exc)) from exc
    mapping = _as_mapping(data, context=str(path))
    _check_keys(mapping, {"version", "tenant_id", "patterns", "venue_paths", "allowlist"}, context=str(path))
    if mapping.get("version") != 1:
        raise TenantConfidentialityError(f"{path}: version must be 1")
    tenant_id = _required_str(mapping, "tenant_id", context=str(path))
    if expected_tenant_id is not None and tenant_id != expected_tenant_id:
        raise TenantConfidentialityError(
            f"{path}: tenant_id {tenant_id!r} does not match tenant record {expected_tenant_id!r}"
        )
    patterns = _parse_patterns(mapping.get("patterns"), tenant_id=tenant_id, path=path)
    pattern_labels = {pattern.label for pattern in patterns}
    return TenantDenylist(
        tenant_id=tenant_id,
        patterns=patterns,
        venue_paths=_parse_venue_paths(mapping.get("venue_paths"), path=path),
        allowlist=_parse_allowlist(
            mapping.get("allowlist"),
            tenant_id=tenant_id,
            pattern_labels=pattern_labels,
            path=path,
        ),
    )


def iter_active_tenant_records(root: Path) -> list[Path]:
    records: list[Path] = []
    for rel_root in TENANT_RECORD_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for candidate in sorted(base.rglob("*.yml")) + sorted(base.rglob("*.yaml")):
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if isinstance(data, dict) and data.get("kind") == "tenant-record":
                records.append(candidate)
    return records


def load_tenant_denylist_matrix(root: Path, *, tenant_records: Iterable[Path] | None = None) -> TenantDenylistMatrix:
    records = list(tenant_records) if tenant_records is not None else iter_active_tenant_records(root)
    tenants: list[TenantDenylist] = []
    seen: set[str] = set()
    for record_path in records:
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            raise TenantConfidentialityError(str(exc)) from exc
        mapping = _as_mapping(record, context=str(record_path))
        tenant_id = _required_str(mapping, "tenant_id", context=str(record_path))
        if tenant_id in seen:
            raise TenantConfidentialityError(f"{record_path}: duplicate tenant_id {tenant_id!r}")
        confidentiality = _as_mapping(mapping.get("confidentiality"), context=f"{record_path}: confidentiality")
        denylist_ref = _required_str(confidentiality, "denylist_ref", context=f"{record_path}: confidentiality")
        tenants.append(load_tenant_denylist(_resolve_repo_ref(root, denylist_ref), expected_tenant_id=tenant_id))
        seen.add(tenant_id)
    return TenantDenylistMatrix(tuple(tenants))
