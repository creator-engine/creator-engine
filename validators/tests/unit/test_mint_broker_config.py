"""S3 (ce-ops#157) — the mint-broker host-side config schema + fail-closed loader.

The standing shared-App mint broker is configured host-side with: the App ``client_id`` (the
JWT issuer), the App key reference (``pem_path`` — RAM-only by convention, read only by the
openssl signer, never into the process), the v0 PERMISSION CEILING the broker may ever mint, an
explicit declared minimum grant callers may request, and a per-user rate cap. The ceiling and
declared grant deliberately EXCLUDE ``administration:write`` (G3 two-token split: the standing
broker never mints admin scope — the protection floor is a separate one-shot op). Fail-closed:
a missing/malformed/empty config, a bad client_id/pem_path, an empty ceiling/minimum grant, or an
out-of-ceiling/admin entry is a :class:`MintBrokerConfigError`.
"""

from __future__ import annotations

import json

import pytest

from mint_broker.config import MintBrokerConfigError, load_mint_broker_config


def _valid(**over):
    base = {
        "app_client_id": "Iv1.shared0000",
        "pem_path": "/dev/shm/ce-shared/creator-engine-shared-app.pem",
        "audit_log": "/var/log/ce/mint-broker-audit.jsonl",
        "permission_ceiling": {
            "metadata": "read",
            "contents": "write",
            "pull_requests": "write",
        },
        "declared_minimum_grant": {
            "metadata": "read",
            "contents": "write",
            "pull_requests": "write",
        },
        "per_user_rate_cap": 30,
        "rate_window_seconds": 3600,
    }
    base.update(over)
    return base


def test_loads_a_valid_config_and_exposes_the_ceiling_and_cap():
    cfg = load_mint_broker_config(_valid())
    assert cfg.app_client_id == "Iv1.shared0000"
    assert cfg.pem_path.endswith("creator-engine-shared-app.pem")
    assert cfg.permission_ceiling["contents"] == "write"
    assert cfg.permission_ceiling["pull_requests"] == "write"
    assert cfg.declared_minimum_grant["metadata"] == "read"
    assert cfg.declared_minimum_grant["contents"] == "write"
    assert "administration" not in cfg.permission_ceiling
    assert "administration" not in cfg.declared_minimum_grant
    assert cfg.per_user_rate_cap == 30
    assert cfg.rate_window_seconds == 3600


def test_loads_from_a_json_path(tmp_path):
    p = tmp_path / "mint-broker.json"
    p.write_text(json.dumps(_valid()), encoding="utf-8")
    cfg = load_mint_broker_config(p)
    assert cfg.app_client_id == "Iv1.shared0000"


def test_missing_file_is_fail_closed(tmp_path):
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(tmp_path / "nope.json")


def test_malformed_json_is_fail_closed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(p)


def test_empty_config_is_fail_closed():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config({})


def test_missing_client_id_is_fail_closed():
    bad = _valid()
    del bad["app_client_id"]
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(bad)


def test_missing_pem_path_is_fail_closed():
    bad = _valid()
    del bad["pem_path"]
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(bad)


def test_empty_ceiling_is_fail_closed():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(permission_ceiling={}))


def test_missing_declared_minimum_grant_is_fail_closed():
    bad = _valid()
    del bad["declared_minimum_grant"]
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(bad)


def test_empty_declared_minimum_grant_is_fail_closed():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(declared_minimum_grant={}))


def test_administration_write_in_ceiling_is_rejected():
    # G3: the standing broker may NEVER mint administration:write.
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(
            _valid(
                permission_ceiling={
                    "contents": "write",
                    "administration": "write",
                }
            )
        )


def test_admin_level_in_ceiling_is_rejected():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(permission_ceiling={"contents": "admin"}))


def test_admin_level_in_declared_minimum_grant_is_rejected():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(declared_minimum_grant={"contents": "admin"}))


def test_never_scope_in_declared_minimum_grant_is_rejected():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(declared_minimum_grant={"secrets": "read"}))


def test_declared_minimum_grant_must_be_within_ceiling():
    with pytest.raises(MintBrokerConfigError, match="exceeds permission_ceiling"):
        load_mint_broker_config(
            _valid(
                permission_ceiling={"metadata": "read", "contents": "read"},
                declared_minimum_grant={"contents": "write"},
            )
        )


def test_declared_minimum_grant_scope_must_exist_in_ceiling():
    with pytest.raises(MintBrokerConfigError, match="not present in permission_ceiling"):
        load_mint_broker_config(
            _valid(
                permission_ceiling={"metadata": "read"},
                declared_minimum_grant={"contents": "read"},
            )
        )


def test_negative_rate_cap_is_fail_closed():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(per_user_rate_cap=-1))


def test_non_int_rate_cap_is_fail_closed():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(per_user_rate_cap="lots"))


def test_non_positive_window_is_fail_closed():
    with pytest.raises(MintBrokerConfigError):
        load_mint_broker_config(_valid(rate_window_seconds=0))


def test_permits_returns_true_only_within_ceiling():
    cfg = load_mint_broker_config(_valid())
    assert cfg.permits({"contents": "write", "metadata": "read"}) is True
    assert cfg.permits({"contents": "read"}) is True  # read <= write is in-ceiling
    assert cfg.permits({"administration": "write"}) is False  # not in ceiling
    assert cfg.permits({"pull_requests": "write", "secrets": "read"}) is False  # unknown scope
    assert cfg.permits({}) is False  # empty request is never in-ceiling


def test_within_declared_minimum_is_separate_from_ceiling():
    cfg = load_mint_broker_config(
        _valid(declared_minimum_grant={"metadata": "read", "contents": "read"})
    )
    assert cfg.permits({"contents": "write"}) is True
    assert cfg.within_declared_minimum({"contents": "read"}) is True
    assert cfg.within_declared_minimum({"contents": "write"}) is False
    assert cfg.within_declared_minimum({"pull_requests": "write"}) is False
    assert cfg.within_declared_minimum({}) is False


def test_pem_path_and_client_id_kept_out_of_repr():
    cfg = load_mint_broker_config(_valid())
    text = repr(cfg)
    assert "Iv1.shared0000" not in text
    assert "creator-engine-shared-app.pem" not in text
