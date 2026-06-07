"""Unit tests for the v3 G-5 ``ce_spend_envelope`` check (spend-policy predicates)."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import ce_spend_envelope as chk
from creator_engine_validator.checks import registered_checks

PSHA = "a" * 64


def _policy(**overrides):
    base = {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "spend-pilot",
        "policy_sha": PSHA,
        "role": "implementer",
        "isolation_backend": "gvisor-proxy",
        "image_ref": {"name": "img", "sha": "sha256:" + ("b" * 64)},
        "mount_manifest": [],
        "egress_allowlist": [],
        "secret_allowlist": [],
        "grant_extensible": False,
        "grant_authority": "controller",
    }
    base.update(overrides)
    return base


def _codes(policy):
    return sorted({e.code for e in chk.validate_spend_envelope(policy, Path("policy.yml"))})


VALID_ENV = [
    {"scope": "global", "amount": 100.0, "unit": "$", "window": "total"},
    {"scope": "fleet", "amount": 50.0, "unit": "$", "window": "total", "fleet_id": "f1"},
    {"scope": "run", "amount": 10.0, "unit": "$", "window": "total"},
]


# --- registration ------------------------------------------------------------
def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg
    assert reg[chk.CHECK_NAME].frs  # error codes declared


# --- green: no spend governance + a valid declared envelope ------------------
def test_policy_without_spend_fields_passes():
    assert _codes(_policy()) == []


def test_valid_nested_dollar_envelopes_pass():
    assert _codes(_policy(spend_envelopes=VALID_ENV, spend_cap_enforcement="enforce")) == []


def test_valid_single_seat_percent_envelope_passes():
    env = [{"scope": "run", "amount": 80.0, "unit": "%", "window": "rolling_5h"}]
    assert _codes(_policy(spend_envelopes=env)) == []


# --- teeth: mandatory global ceiling (Fork B) -------------------------------
def test_dollar_envelope_without_global_ceiling_fires():
    env = [{"scope": "run", "amount": 10.0, "unit": "$", "window": "total"}]
    assert chk.CODE_NO_GLOBAL_CEILING in _codes(_policy(spend_envelopes=env))


# --- teeth: nested consistency (inner <= outer) ------------------------------
def test_inner_cap_exceeding_outer_fires():
    env = [
        {"scope": "global", "amount": 5.0, "unit": "$", "window": "total"},
        {"scope": "run", "amount": 10.0, "unit": "$", "window": "total"},
    ]
    assert chk.CODE_ENVELOPE_INCONSISTENT in _codes(_policy(spend_envelopes=env))


def test_consistent_caps_across_windows_do_not_cross_fire():
    env = [
        {"scope": "global", "amount": 100.0, "unit": "$", "window": "total"},
        {"scope": "run", "amount": 5.0, "unit": "$", "window": "per_run"},
    ]
    assert chk.CODE_ENVELOPE_INCONSISTENT not in _codes(_policy(spend_envelopes=env))


# --- teeth: two-regime unit correctness (Fork C) -----------------------------
def test_percent_on_fleet_scope_fires():
    env = [{"scope": "fleet", "amount": 80.0, "unit": "%", "window": "rolling_5h", "fleet_id": "f"}]
    assert chk.CODE_REGIME_UNIT in _codes(_policy(spend_envelopes=env))


def test_global_scope_non_dollar_fires():
    env = [{"scope": "global", "amount": 80.0, "unit": "%", "window": "rolling_weekly"}]
    assert chk.CODE_REGIME_UNIT in _codes(_policy(spend_envelopes=env))


def test_percent_policy_with_fleet_scope_fires():
    env = [
        {"scope": "run", "amount": 80.0, "unit": "%", "window": "rolling_5h"},
        {"scope": "fleet", "amount": 50.0, "unit": "$", "window": "total", "fleet_id": "f"},
        {"scope": "global", "amount": 100.0, "unit": "$", "window": "total"},
    ]
    assert chk.CODE_REGIME_UNIT in _codes(_policy(spend_envelopes=env))


# --- teeth: ratified-human-only opt-out --------------------------------------
def test_optout_off_without_binding_fires():
    assert chk.CODE_OPTOUT_UNRATIFIED in _codes(_policy(spend_cap_enforcement="off"))


def test_optout_off_with_invalid_binding_fires():
    p = _policy(spend_cap_enforcement="off", spend_cap_optout={"ratified_prompt_sha": "short", "approver_ref": "x"})
    assert chk.CODE_OPTOUT_UNRATIFIED in _codes(p)


def test_optout_off_with_valid_ratification_passes():
    p = _policy(
        spend_cap_enforcement="off",
        spend_cap_optout={"ratified_prompt_sha": "c" * 64, "approver_ref": "d" * 64},
    )
    assert chk.CODE_OPTOUT_UNRATIFIED not in _codes(p)


def test_optout_keeps_runaway_net_global_ceiling_still_required():
    # "off" disables sub-caps but the runaway-detection net (global ceiling) stays:
    # a $ envelope set without a global ceiling still fires even when opted out.
    p = _policy(
        spend_cap_enforcement="off",
        spend_cap_optout={"ratified_prompt_sha": "c" * 64, "approver_ref": "d" * 64},
        spend_envelopes=[{"scope": "run", "amount": 10.0, "unit": "$", "window": "total"}],
    )
    assert chk.CODE_NO_GLOBAL_CEILING in _codes(p)


# --- run() selects records from a directory ----------------------------------
def test_run_fires_on_malformed_spend_policy_in_dir(tmp_path):
    bad = _policy(spend_envelopes=[{"scope": "run", "amount": 10.0, "unit": "$", "window": "total"}])
    (tmp_path / "policy.yml").write_text(yaml.safe_dump(bad))
    result = chk.run([tmp_path])
    assert not result.ok
    assert any(e.code == chk.CODE_NO_GLOBAL_CEILING for e in result.errors)


def test_run_green_on_valid_spend_policy_in_dir(tmp_path):
    good = _policy(spend_envelopes=VALID_ENV)
    (tmp_path / "policy.yml").write_text(yaml.safe_dump(good))
    result = chk.run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]
