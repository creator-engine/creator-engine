"""Unit tests for the two-mode installer logic (``v3_installer``) — G-7.4.

Pure decision substrate. Asserts: verify-BEFORE-execute (accept signed, REJECT
tampered / unknown-key, refuse-on-fail); detect-don't-assume dependency planning
(present→skip, missing→permission-gated install, batched sudo, idempotent); the
Default-vs-Custom profile + the ratified-HUMAN-only cost opt-out (emits a fragment
``ce_spend_envelope`` accepts; refuses an unratified opt-out); the ``ce`` exposure;
and that the full plan verifies first. Module is v3-classified and pure.
"""
from __future__ import annotations

import pytest

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_installer as inst
from creator_engine_validator.checks.ce_spend_envelope import _check_optout

SPEC = b"# Install CE\nsteps: ...\n"
PINNED = inst.PINNED_KEYS
KEY = "ce-root-v1"
HEX = "a" * 64


# ---------------------------------------------------------------------------
# verify-before-execute
# ---------------------------------------------------------------------------
def test_sign_then_verify_against_pinned_key():
    sig = inst.sign_spec(SPEC, key_id=KEY)
    assert sig["algo"] == inst.CONTENT_ALGO
    r = inst.verify_spec(SPEC, sig, pinned_keys=PINNED)
    assert r.ok and r.key_id == KEY


def test_verify_rejects_tampered_spec():
    sig = inst.sign_spec(SPEC, key_id=KEY)
    r = inst.verify_spec(SPEC + b"  # tampered", sig, pinned_keys=PINNED)
    assert not r.ok and "did not verify" in r.reason


def test_verify_rejects_unknown_key():
    sig = inst.sign_spec(SPEC, key_id="rogue-key")
    r = inst.verify_spec(SPEC, sig, pinned_keys=PINNED)
    assert not r.ok and "unpinned" in r.reason


def test_verify_rejects_missing_signature():
    assert inst.verify_spec(SPEC, None, pinned_keys=PINNED).ok is False


def test_require_verified_raises_on_failure():
    sig = inst.sign_spec(SPEC, key_id=KEY)
    with pytest.raises(inst.InstallRefused):
        inst.require_verified(SPEC + b"x", sig, pinned_keys=PINNED)
    # the valid case returns the result
    assert inst.require_verified(SPEC, sig, pinned_keys=PINNED).ok


def test_injected_asymmetric_verifier_seam():
    # a real asymmetric algo needs the injected verifier; the floor rejects it
    sig = {"key_id": KEY, "algo": "ed25519", "value": "deadbeef"}
    assert inst.verify_spec(SPEC, sig, pinned_keys=PINNED).ok is False
    ok_verifier = lambda algo, raw, value, key: algo == "ed25519" and value == "deadbeef"
    assert inst.verify_spec(SPEC, sig, pinned_keys=PINNED, verifier=ok_verifier).ok is True


# ---------------------------------------------------------------------------
# detect-don't-assume dependency planning
# ---------------------------------------------------------------------------
def test_plan_present_skips_missing_installs():
    probe = {"git": True, "python": True, "runsc": False, "proxy": False, "uv": True}
    plan = inst.plan_dependencies(inst.REQUIRED_DEPENDENCIES, probe)
    assert set(plan.to_install) == {"runsc", "proxy"}
    assert {s.name for s in plan.steps if s.action == "skip"} == {"git", "python", "uv"}


def test_sudo_is_batched_for_system_tools_only():
    # uv missing (user-space) → no sudo; runsc missing → sudo
    assert inst.plan_dependencies(("uv",), {"uv": False}).needs_sudo is False
    assert inst.plan_dependencies(("runsc",), {"runsc": False}).needs_sudo is True


def test_plan_is_idempotent_all_present():
    probe = {t: True for t in inst.REQUIRED_DEPENDENCIES}
    plan = inst.plan_dependencies(inst.REQUIRED_DEPENDENCIES, probe)
    assert plan.to_install == () and plan.needs_sudo is False


# ---------------------------------------------------------------------------
# Default-vs-Custom profile + the ratified-human-only cost opt-out
# ---------------------------------------------------------------------------
def test_default_profile_enforces():
    p = inst.build_profile()
    assert p.mode == "default"
    assert p.runtime_policy == {"spend_cap_enforcement": "enforce"}
    assert p.educate is None


def test_custom_optout_requires_ratification():
    with pytest.raises(inst.InstallRefused):
        inst.build_profile(opt_out=True)  # no binding
    with pytest.raises(inst.InstallRefused):
        inst.build_profile(opt_out=True, optout_ratification={"ratified_prompt_sha": "short"})


def test_custom_optout_emits_valid_g5_fragment_and_educates():
    rat = {"ratified_prompt_sha": HEX, "approver_ref": "b" * 64}
    p = inst.build_profile(opt_out=True, optout_ratification=rat)
    assert p.mode == "custom"
    assert p.runtime_policy["spend_cap_enforcement"] == "off"
    assert p.runtime_policy["spend_cap_optout"] == rat
    assert p.educate == inst.EDUCATE_AT_OPTOUT
    # the emitted fragment is exactly what ce_spend_envelope accepts (no error)
    assert _check_optout(p.runtime_policy, __import__("pathlib").Path("x")) == []


def test_educate_copy_is_verbatim_from_contract():
    assert "won't speed up your runs" in inst.EDUCATE_AT_OPTOUT
    assert "runaway-detection net" in inst.EDUCATE_AT_OPTOUT


# ---------------------------------------------------------------------------
# the `ce` exposure + the full verify-first plan
# ---------------------------------------------------------------------------
def test_ce_exposure_targets_ce():
    step = inst.ce_exposure_plan()
    assert step["command"] == "ce" and step["via"] == "cev3"


def test_build_plan_verifies_first_then_plans():
    sig = inst.sign_spec(SPEC, key_id=KEY)
    probe = {"git": True, "python": True, "runsc": False, "proxy": True, "uv": True}
    plan = inst.build_install_plan(SPEC, sig, pinned_keys=PINNED, probe=probe)
    assert plan["verified"]["ok"] is True
    assert plan["dependencies"]["install"] == ["runsc"]
    assert plan["dependencies"]["needs_sudo"] is True
    assert plan["expose_cli"]["command"] == "ce"
    assert "the GitHub-App authorization click" in plan["human_approves"]
    assert any("sudo" in h for h in plan["human_approves"])


def test_build_plan_refuses_unverified_spec_nothing_planned():
    sig = inst.sign_spec(SPEC, key_id="rogue")
    with pytest.raises(inst.InstallRefused):
        inst.build_install_plan(SPEC, sig, pinned_keys=PINNED, probe={})


# ---------------------------------------------------------------------------
# classification / purity
# ---------------------------------------------------------------------------
def test_v3_classified_and_pure():
    assert ver.classify("v3_installer") == ver.V3
    import inspect
    src = inspect.getsource(inst)
    for io_marker in ("open(", "read_text", "write_text", "Path.home", "os.environ", "import subprocess"):
        assert io_marker not in src, f"installer logic must stay pure (found {io_marker!r})"
