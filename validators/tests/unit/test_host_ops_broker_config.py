"""Tests for BrokerConfig resolution methods."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.config import BrokerConfig, BrokerConfigError


def _minimal_raw(**overrides):
    raw = {
        "audit_log_path": "/tmp/test-audit.jsonl",
        "kill_switch_path": "/tmp/test-ks.json",
        "broker_identity": "test-broker",
    }
    raw.update(overrides)
    return raw


def test_config_loads_container_image_allowlist():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(container_image_allowlist=["ghcr.io/creator-engine/", "registry.local/ce-"])
    )
    assert cfg.container_image_allowlist == ("ghcr.io/creator-engine/", "registry.local/ce-")


def test_config_default_container_image_allowlist_is_empty():
    cfg = BrokerConfig.from_mapping(_minimal_raw())
    assert cfg.container_image_allowlist == ()


def test_resolve_container_image_accepts_allowed_prefix():
    cfg = BrokerConfig.from_mapping(_minimal_raw(container_image_allowlist=["ghcr.io/creator-engine/"]))
    image = "ghcr.io/creator-engine/ce-worker@sha256:" + "a" * 64
    assert cfg.resolve_container_image(image) == image


def test_resolve_container_image_rejects_disallowed_registry():
    cfg = BrokerConfig.from_mapping(_minimal_raw(container_image_allowlist=["ghcr.io/creator-engine/"]))
    image = "docker.io/randomuser/image@sha256:" + "b" * 64
    with pytest.raises(BrokerConfigError, match="not.*CE-owned registry"):
        cfg.resolve_container_image(image)


def test_resolve_container_image_rejects_all_when_allowlist_empty():
    cfg = BrokerConfig.from_mapping(_minimal_raw())
    image = "ghcr.io/creator-engine/ce-worker@sha256:" + "c" * 64
    with pytest.raises(BrokerConfigError, match="allowlist is empty"):
        cfg.resolve_container_image(image)


def test_resolve_state_root_accepts_exact_match():
    cfg = BrokerConfig.from_mapping(_minimal_raw(state_roots={"ce-work": "/var/ce/work"}))
    assert cfg.resolve_state_root("ce-work") == "ce-work"


def test_resolve_state_root_accepts_prefix_match():
    cfg = BrokerConfig.from_mapping(_minimal_raw(state_root_prefixes=["ce-tenant-"]))
    assert cfg.resolve_state_root("ce-tenant-abc123") == "ce-tenant-abc123"


def test_resolve_state_root_rejects_unknown_root():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(
            state_roots={"ce-work": "/var/ce/work"},
            state_root_prefixes=["ce-tenant-"],
        )
    )
    with pytest.raises(BrokerConfigError, match="not CE-owned"):
        cfg.resolve_state_root("untrusted-root")


def test_resolve_state_root_prefix_does_not_match_partial_stem():
    """Prefix 'ce-tenant-' must not match 'ce-tenant'."""
    cfg = BrokerConfig.from_mapping(_minimal_raw(state_root_prefixes=["ce-tenant-"]))
    with pytest.raises(BrokerConfigError):
        cfg.resolve_state_root("ce-tenant")
