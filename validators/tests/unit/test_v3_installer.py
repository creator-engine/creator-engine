"""Unit tests for the two-mode installer logic (``v3_installer``) — G-7.4 + E.3.

Pure decision substrate. Asserts: verify-BEFORE-execute (accept signed, REJECT
tampered / unknown-key, refuse-on-fail); detect-don't-assume dependency planning
(present→skip, missing→permission-gated install, batched sudo, idempotent); the
Default-vs-Custom profile + the ratified-HUMAN-only cost opt-out (emits a fragment
``ce_spend_envelope`` accepts; refuses an unratified opt-out); the ``ce`` exposure;
and that the full plan verifies first. Module is v3-classified and pure.

v3.5-E.3 (the unified two-mode engine): the answers schema is valid + the
single source of truth; answers validation fails closed (unknown keys, raw
secrets, unratified governance weakenings); SecretRef is pattern-only; the
precedence merge (`interactive > answers > detected > default`) surfaces
detected-fact conflicts; the inventory/missing-list derive from the schema;
the scoped sudo-grant diff refuses drift outside the grant.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_installer as inst
from creator_engine_validator.checks.ce_spend_envelope import _check_optout

SPEC = b"# Install CE\nsteps: ...\n"
PINNED = inst.PINNED_KEYS
KEY = "ce-root-v1"
HEX = "a" * 64

_REPO_ROOT = Path(__file__).resolve().parents[3]
ANSWERS_SCHEMA = yaml.safe_load(
    (_REPO_ROOT / inst.ANSWERS_SCHEMA_PATH).read_text(encoding="utf-8")
)

#: A representative full answers document (the design-of-record skeleton).
GOOD_ANSWERS = {
    "answers_version": 1,
    "profile": "solo-pilot",
    "host": {
        "sudo_grant": ["runsc", "proxy"],
        "workspace_root": "~/ce-workspaces",
    },
    "cost": {"profile": "default"},
    "provider": {
        "harness": "claude-code",
        "anthropic_api_key": "env://ANTHROPIC_API_KEY",
    },
    "github": {
        "mode": "existing",
        "repo": "chmod735/creator-engine-canonical",
        "bootstrap_token": "prompt://github-bootstrap-token",
        "app": {"kind": "shared", "installation_id": 12345678},
        "protections": "reference",
        "actions": {"install_validate_workflow": True},
        "reviewer": "chmod735",
    },
    "pilot": {"target_repo": "chmod735/creator-engine-canonical"},
}


def _answers(**overrides):
    import copy

    doc = copy.deepcopy(GOOD_ANSWERS)
    for dotted, value in overrides.items():
        node = doc
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        if value is _DELETE:
            node.pop(parts[-1], None)
        else:
            node[parts[-1]] = value
    return doc


_DELETE = object()


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
# E.4-fix: the ssh-ed25519 SSHSIG verifier (injected runner) + trust root
# ---------------------------------------------------------------------------
import base64 as _b64
import hashlib as _hashlib
import re as _re
import shutil as _shutil
import subprocess as _subprocess
import tempfile as _tempfile

_LLMS_INSTALL = _REPO_ROOT / "docs" / "llms-install.md"
_KEY_FILE = _REPO_ROOT / "docs" / "keys" / "ce-root-v1"
_ALLOWED_SIGNERS = "ce-root-v1 ssh-ed25519 AAAAB3Nza-fake-blob"


def _capturing_runner(accept=True, record=None):
    """A fake ssh-keygen runner: records the kwargs it was handed; returns accept."""
    def _run(**kwargs):
        if record is not None:
            record.update(kwargs)
        return accept
    return _run


def test_ssh_ed25519_verifier_passes_with_accepting_runner():
    rec: dict = {}
    sig = {"key_id": KEY, "algo": inst.SSH_ED25519_ALGO, "value": _b64.b64encode(b"SIG").decode()}
    v = inst.ssh_ed25519_verifier(_capturing_runner(True, rec))
    r = inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=v)
    assert r.ok and r.key_id == KEY
    # the runner received the DECODED sig, the canonical message, the identity + fixed namespace
    assert rec["signature"] == b"SIG"
    assert rec["message"] == b"spec"
    assert rec["identity"] == "ce-root-v1"
    assert rec["namespace"] == inst.SSH_SIG_NAMESPACE
    assert rec["allowed_signers"] == _ALLOWED_SIGNERS


def test_ssh_ed25519_verifier_fails_when_runner_rejects():
    sig = {"key_id": KEY, "algo": inst.SSH_ED25519_ALGO, "value": _b64.b64encode(b"SIG").decode()}
    v = inst.ssh_ed25519_verifier(_capturing_runner(False))
    assert inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=v).ok is False


def test_ssh_ed25519_verifier_fail_closed_no_runner_or_missing_binary():
    # a missing ssh-keygen (runner None) ⇒ fail-closed, never half-open
    sig = {"key_id": KEY, "algo": inst.SSH_ED25519_ALGO, "value": _b64.b64encode(b"SIG").decode()}
    v = inst.ssh_ed25519_verifier(None)
    assert inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=v).ok is False


def test_ssh_ed25519_verifier_fail_closed_on_runner_exception():
    def _boom(**kwargs):
        raise OSError("ssh-keygen: not found")
    sig = {"key_id": KEY, "algo": inst.SSH_ED25519_ALGO, "value": _b64.b64encode(b"SIG").decode()}
    v = inst.ssh_ed25519_verifier(_boom)
    assert inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=v).ok is False


def test_ssh_ed25519_verifier_rejects_bad_base64():
    sig = {"key_id": KEY, "algo": inst.SSH_ED25519_ALGO, "value": "not valid base64 !!!"}
    v = inst.ssh_ed25519_verifier(_capturing_runner(True))
    assert inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=v).ok is False


def test_ssh_ed25519_verifier_rejects_non_ssh_algo():
    sig = {"key_id": KEY, "algo": "sha256-content", "value": _b64.b64encode(b"x").decode()}
    v = inst.ssh_ed25519_verifier(_capturing_runner(True))
    # the ssh verifier only accepts ssh-ed25519; another algo ⇒ False
    assert v("sha256-content", b"spec", sig["value"], _ALLOWED_SIGNERS) is False


def test_ssh_ed25519_verify_rejects_unknown_key():
    sig = {"key_id": "rogue", "algo": inst.SSH_ED25519_ALGO, "value": _b64.b64encode(b"SIG").decode()}
    v = inst.ssh_ed25519_verifier(_capturing_runner(True))
    r = inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=v)
    assert not r.ok and "unpinned" in r.reason


def test_wrong_namespace_factory_fails_a_faithful_runner():
    # a runner that only honors the fixed namespace rejects a verifier built wrong
    def _ns_strict(**kwargs):
        return kwargs["namespace"] == inst.SSH_SIG_NAMESPACE
    sig = {"key_id": KEY, "algo": inst.SSH_ED25519_ALGO, "value": _b64.b64encode(b"SIG").decode()}
    good = inst.ssh_ed25519_verifier(_ns_strict)
    bad = inst.ssh_ed25519_verifier(_ns_strict, namespace="ce-spec-WRONG")
    assert inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=good).ok is True
    assert inst.verify_spec(b"spec", sig, pinned_keys={KEY: _ALLOWED_SIGNERS}, verifier=bad).ok is False


def test_parse_allowed_signers_and_pinned_key_matches_served_root():
    text = _KEY_FILE.read_text(encoding="utf-8")
    pinned = inst.parse_allowed_signers(text)
    for principal in ("ce-root-v1", "ce-dev1-root-v1"):
        assert principal in pinned
        line = pinned[principal]
        assert line.split()[:2] == [principal, "ssh-ed25519"]
        # the module-pinned key mirrors the served allowed_signers line byte-for-byte
        assert inst.PINNED_KEYS[principal] == line
    # comments / blank lines never pin anything
    assert inst.parse_allowed_signers("# just a comment\n\n") == {}


def test_public_key_fingerprint_matches_out_of_band_anchor_record():
    line = inst.PINNED_KEYS["ce-root-v1"]
    fingerprint = inst.public_key_fingerprint(line)
    anchors = inst.parse_trust_anchor_records(
        f"# DNS TXT form\nce-root-v1={fingerprint}\n",
        source="dns-txt",
    )

    evidence = inst.verify_trust_anchors("ce-root-v1", line, anchors)

    assert fingerprint.startswith("SHA256:")
    assert evidence.ok is True
    assert evidence.status == "verified"
    assert evidence.agreed == ("dns-txt",)


def test_out_of_band_anchor_missing_is_degraded_not_verified():
    evidence = inst.verify_trust_anchors(
        "ce-root-v1",
        inst.PINNED_KEYS["ce-root-v1"],
        (),
    )

    assert evidence.ok is False
    assert evidence.status == "same_origin_only"
    assert "out-of-band" in evidence.reason


def test_out_of_band_anchor_mismatch_is_refused():
    anchors = inst.parse_trust_anchor_records(
        "ce-root-v1=SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        source="github-org-profile",
    )

    evidence = inst.verify_trust_anchors("ce-root-v1", inst.PINNED_KEYS["ce-root-v1"], anchors)

    assert evidence.ok is False
    assert evidence.status == "mismatch"
    assert evidence.mismatched == ("github-org-profile",)


def test_canonical_spec_bytes_normalizes_dynamic_fields_and_is_idempotent():
    spec = (
        "head\n  key_id: ce-root-v1\n  value: AAAAREALbase64==\n"
        "  content_sha256: " + ("a" * 64) + "\ntail\n"
    )
    canon = inst.canonical_spec_bytes(spec)
    assert b"  value: <published-with-this-spec>\n" in canon
    assert b"  content_sha256: <published-with-this-spec>\n" in canon
    assert b"AAAAREALbase64" not in canon and (b"a" * 64) not in canon
    # idempotent: re-canonicalizing changes nothing (embedding never moves the target)
    assert inst.canonical_spec_bytes(canon) == canon
    # matches the §0 stock-sed rule byte-for-byte
    import subprocess as sp
    out = sp.run(
        ["sed", "-E",
         r"s#^(  value: ).*#\1<published-with-this-spec>#; "
         r"s#^(  content_sha256: ).*#\1<published-with-this-spec>#"],
        input=spec.encode("utf-8"), capture_output=True,
    )
    assert out.stdout == canon


def test_content_floor_regression_unbroken():
    # the in-tree sha256-content floor still verifies/refuses exactly as before
    sig = inst.sign_spec(SPEC, key_id=KEY)
    assert sig["algo"] == inst.CONTENT_ALGO
    assert inst.verify_spec(SPEC, sig, pinned_keys=PINNED).ok is True
    assert inst.verify_spec(SPEC + b"x", sig, pinned_keys=PINNED).ok is False


def _fixture_signed_install_spec() -> str:
    canonical = """\
kind: ce-install-spec
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: <published-with-this-spec>
  content_sha256: <published-with-this-spec>
"""
    digest = inst.content_digest(inst.canonical_spec_bytes(canonical))
    return canonical.replace("  value: <published-with-this-spec>", "  value: c2ln").replace(
        "  content_sha256: <published-with-this-spec>",
        f"  content_sha256: {digest}",
    )


def test_parse_signed_install_spec_extracts_embedded_sshsig_and_content_floor():
    signed = inst.parse_signed_install_spec(_fixture_signed_install_spec())
    assert signed.signature == {
        "key_id": "ce-root-v1",
        "algo": inst.SSH_ED25519_ALGO,
        "value": "c2ln",
    }
    assert signed.content_sha256 == signed.canonical_sha256


def test_parse_signed_install_spec_rejects_tampered_content_floor():
    with pytest.raises(inst.InstallRefused, match="content_sha256 does not match"):
        inst.parse_signed_install_spec(_fixture_signed_install_spec() + "\ntamper\n")


def test_v3_installer_parses_bootstrap_artifact_manifest_from_current_spec():
    manifest = inst.parse_bootstrap_manifest(_SPEC_TEXT)
    assert manifest.artifact_manifest_version == 1
    assert manifest.package_name == "creator-engine-validator"
    assert manifest.package_version == "0.2.0"
    assert manifest.python_requires == ">=3.14"
    assert manifest.app_wheel == "creator_engine_validator-0.2.0-py3-none-any.whl"
    assert manifest.answers_schema_url == "https://creator-engine.dev/schemas/install-answers.schema.yaml"
    assert manifest.python_acquisition.tool == "uv"
    assert manifest.python_acquisition.version == "0.11.21"
    assert manifest.python_acquisition.platform == "linux-x86_64-cp314"
    assert manifest.python_acquisition_for_platform("linux-aarch64-cp314").url.endswith(
        "/uv-aarch64-unknown-linux-gnu.tar.gz"
    )
    wheels = manifest.wheel_by_filename()
    assert manifest.app_wheel in wheels
    assert wheels["attrs-26.1.0-py3-none-any.whl"].sha256 == (
        "c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309"
    )
    assert wheels[
        "pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl"
    ].platforms == ("linux-aarch64-cp314",)


def test_v3_installer_rejects_bad_bootstrap_manifest():
    bad_missing_app = _SPEC_TEXT.replace(
        "  app_wheel: creator_engine_validator-0.2.0-py3-none-any.whl\n",
        "",
    )
    with pytest.raises(inst.InstallRefused, match="missing app_wheel"):
        inst.parse_bootstrap_manifest(bad_missing_app)
    bad_version = _SPEC_TEXT.replace("  artifact_manifest_version: 1\n", "  artifact_manifest_version: 2\n")
    with pytest.raises(inst.InstallRefused, match="unsupported version 2"):
        inst.parse_bootstrap_manifest(bad_version)
    bad_hash = _SPEC_TEXT.replace(
        "    sha256: c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309",
        "    sha256: nope",
    )
    with pytest.raises(inst.InstallRefused, match="sha256 is not 64-hex"):
        inst.parse_bootstrap_manifest(bad_hash)


def test_sha256s_parser_and_platform_plan():
    sums = "a" * 64 + "  install.sh\n" + "b" * 64 + "  *wheel.whl\n"
    assert inst.parse_sha256s(sums) == {"install.sh": "a" * 64, "wheel.whl": "b" * 64}
    manifest = inst.parse_bootstrap_manifest(_SPEC_TEXT)
    plan = inst.build_bootstrap_artifact_plan(manifest, os_name="Linux", machine="x86_64")
    assert plan["platform"] == "linux-x86_64-cp314"
    wheel_names = {wheel["filename"] for wheel in plan["wheels"]}
    assert "pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl" in wheel_names
    assert "rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" in wheel_names
    assert "uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" in wheel_names
    assert not any("aarch64" in name for name in wheel_names)

    arm_plan = inst.build_bootstrap_artifact_plan(manifest, os_name="Linux", machine="arm64")
    assert arm_plan["platform"] == "linux-aarch64-cp314"
    arm_wheel_names = {wheel["filename"] for wheel in arm_plan["wheels"]}
    assert "attrs-26.1.0-py3-none-any.whl" in arm_wheel_names
    assert "creator_engine_validator-0.2.0-py3-none-any.whl" in arm_wheel_names
    assert "pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl" in arm_wheel_names
    assert "rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl" in arm_wheel_names
    assert "uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl" in arm_wheel_names
    assert not any("x86_64" in name for name in arm_wheel_names)
    assert arm_plan["python_acquisition"]["url"].endswith("/uv-aarch64-unknown-linux-gnu.tar.gz")

    with pytest.raises(inst.InstallRefused, match="unsupported_platform"):
        inst.build_bootstrap_artifact_plan(manifest, os_name="Darwin", machine="arm64")
    with pytest.raises(inst.InstallRefused, match="unsupported_platform"):
        inst.build_bootstrap_artifact_plan(manifest, os_name="Linux", machine="s390x")


# --- the E2E proof: a REAL detached SSHSIG, stock ssh-keygen, clean dir --------
def _real_ssh_keygen_runner(**kwargs):
    """The injected runner the CLI/live-drive uses: shell `ssh-keygen -Y verify`
    in a clean scratch dir. Tests MAY use subprocess; the engine never does."""
    with _tempfile.TemporaryDirectory() as d:
        from pathlib import Path as _P
        sd = _P(d)
        (sd / "allowed_signers").write_text(kwargs["allowed_signers"] + "\n", encoding="utf-8")
        (sd / "msg").write_bytes(kwargs["message"])
        (sd / "sig").write_bytes(kwargs["signature"])
        proc = _subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", "allowed_signers",
             "-I", kwargs["identity"], "-n", kwargs["namespace"], "-s", "sig"],
            cwd=d, stdin=(sd / "msg").open("rb"),
            capture_output=True,
        )
        return proc.returncode == 0


def _embedded_signature_value(spec_text: str):
    m = _re.search(r"(?m)^  value: (.+)$", spec_text)
    return m.group(1).strip() if m else None


_SSH_KEYGEN = _shutil.which("ssh-keygen")
_SPEC_TEXT = _LLMS_INSTALL.read_text(encoding="utf-8") if _LLMS_INSTALL.exists() else ""
_EMBEDDED_VALUE = _embedded_signature_value(_SPEC_TEXT)
_SIGNED = (
    _EMBEDDED_VALUE is not None
    and _EMBEDDED_VALUE != inst.SIGNATURE_PLACEHOLDER
    and not _EMBEDDED_VALUE.startswith("<")
)


@pytest.mark.skipif(_SSH_KEYGEN is None, reason="stock ssh-keygen not available")
@pytest.mark.skipif(not _SIGNED, reason="spec not yet signed (value still placeholder)")
def test_e2e_real_sshsig_through_require_verified_positive_and_tampered():
    pinned = inst.parse_allowed_signers(_KEY_FILE.read_text(encoding="utf-8"))
    canonical = inst.canonical_spec_bytes(_SPEC_TEXT)
    sig = {"key_id": "ce-root-v1", "algo": inst.SSH_ED25519_ALGO, "value": _EMBEDDED_VALUE}
    verifier = inst.ssh_ed25519_verifier(_real_ssh_keygen_runner)
    # positive: require_verified (the real onboard gate) accepts the signed spec
    assert inst.require_verified(canonical, sig, pinned_keys=pinned, verifier=verifier).ok
    # the retained content_sha256 floor matches sha256 of the SAME canonical bytes
    m = _re.search(r"(?m)^  content_sha256: (.+)$", _SPEC_TEXT)
    assert m and m.group(1).strip() == _hashlib.sha256(canonical).hexdigest()
    # tampered: one extra byte in the signed region FAILS both checks
    with pytest.raises(inst.InstallRefused):
        inst.require_verified(canonical + b"x", sig, pinned_keys=pinned, verifier=verifier)


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


# ===========================================================================
# v3.5-E.3 — the answers file + the operator-input inventory
# ===========================================================================

# ---------------------------------------------------------------------------
# the schema document (the single source of truth)
# ---------------------------------------------------------------------------
def test_answers_schema_is_valid_draft202012():
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(ANSWERS_SCHEMA)


def test_answers_schema_is_declared_v3_surface():
    assert inst.ANSWERS_SCHEMA_PATH in ver.V3_SCHEMAS


def test_good_answers_validate_clean():
    assert inst.validate_answers(GOOD_ANSWERS, schema=ANSWERS_SCHEMA) == ()
    assert inst.require_valid_answers(GOOD_ANSWERS, schema=ANSWERS_SCHEMA) is GOOD_ANSWERS


def test_minimal_answers_validate_clean():
    assert inst.validate_answers({"answers_version": 1}, schema=ANSWERS_SCHEMA) == ()


def test_unknown_key_fails_closed_top_level_and_nested():
    # the classic IaC footgun: a typo'd key must ERROR, never look consumed
    problems = inst.validate_answers(_answers(workspce_root="x"), schema=ANSWERS_SCHEMA)
    assert any("workspce_root" in p for p in problems)
    problems = inst.validate_answers(
        _answers(**{"github.protectons": "reference"}), schema=ANSWERS_SCHEMA
    )
    assert any("protectons" in p for p in problems)
    with pytest.raises(inst.InstallRefused):
        inst.require_valid_answers(_answers(workspce_root="x"), schema=ANSWERS_SCHEMA)


def test_answers_version_is_required_and_pinned():
    assert inst.validate_answers({}, schema=ANSWERS_SCHEMA)
    assert inst.validate_answers({"answers_version": 2}, schema=ANSWERS_SCHEMA)


# ---------------------------------------------------------------------------
# SecretRef — secrets never by value
# ---------------------------------------------------------------------------
def test_secret_ref_parses_every_scheme():
    for ref in (
        "env://ANTHROPIC_API_KEY",
        "file:///dev/shm/ce-app.pem",
        "prompt://github-bootstrap-token",
        "keychain://ce-bootstrap",
    ):
        parsed = inst.parse_secret_ref(ref)
        assert parsed is not None and parsed.ref == ref


def test_secret_ref_rejects_raw_values_and_non_strings():
    for raw in ("ghp_abc123secret", "sk-ant-xyz", "", None, 42, "http://not-a-scheme"):
        assert inst.parse_secret_ref(raw) is None
    with pytest.raises(inst.InstallRefused):
        inst.require_secret_ref("ghp_abc123secret", field_key="github.bootstrap_token")


def test_raw_secret_in_answers_refused_by_schema_and_belt():
    doc = _answers(**{"github.bootstrap_token": "ghp_rawtoken123"})
    problems = inst.validate_answers(doc, schema=ANSWERS_SCHEMA)
    # both layers fire: the schema pattern AND the belt-and-braces parser
    assert any(p.startswith("schema:") and "bootstrap_token" in p for p in problems)
    assert any(p.startswith("secret: github.bootstrap_token") for p in problems)


# ---------------------------------------------------------------------------
# the generalized ratification binding (one shape, every weakening)
# ---------------------------------------------------------------------------
def test_valid_ratification_generalizes_the_optout_shape():
    binding = {"ratified_prompt_sha": HEX, "approver_ref": "b" * 64}
    assert inst.valid_ratification(binding) is True
    assert inst.valid_ratification(binding, require_ack=True) is False
    assert inst.valid_ratification({**binding, "educate_acknowledged": True}, require_ack=True)
    assert inst.valid_ratification(None) is False
    assert inst.valid_ratification({"ratified_prompt_sha": "short", "approver_ref": HEX}) is False
    # the legacy alias build_profile uses is the same predicate
    assert inst._valid_optout(binding) is True


def test_custom_cost_profile_requires_acked_binding():
    doc = _answers(**{"cost.profile": "custom"})
    problems = inst.validate_answers(doc, schema=ANSWERS_SCHEMA)
    assert any("cost.optout" in p for p in problems)
    doc = _answers(**{
        "cost.profile": "custom",
        "cost.optout": {"ratified_prompt_sha": HEX, "approver_ref": "b" * 64,
                        "educate_acknowledged": True},
    })
    assert inst.validate_answers(doc, schema=ANSWERS_SCHEMA) == ()


def test_optout_binding_bridge_strips_ack_for_the_g5_fragment():
    doc = _answers(**{
        "cost.profile": "custom",
        "cost.optout": {"ratified_prompt_sha": HEX, "approver_ref": "b" * 64,
                        "educate_acknowledged": True},
    })
    binding = inst.optout_binding_from_answers(doc)
    assert binding == {"ratified_prompt_sha": HEX, "approver_ref": "b" * 64}
    # the stripped binding feeds build_profile → exactly what ce_spend_envelope accepts
    profile = inst.build_profile(opt_out=True, optout_ratification=binding)
    assert _check_optout(profile.runtime_policy, Path("x")) == []
    # default profile → no binding
    assert inst.optout_binding_from_answers(GOOD_ANSWERS) is None
    with pytest.raises(inst.InstallRefused):
        inst.optout_binding_from_answers(_answers(**{"cost.profile": "custom"}))


# ---------------------------------------------------------------------------
# the governance floor (reference posture as data) + weakening detection
# ---------------------------------------------------------------------------
def test_reference_protections_come_from_the_schema():
    floor = inst.reference_protections(ANSWERS_SCHEMA)
    assert floor["required_reviews"] == 1
    assert floor["strict"] is True and floor["enforce_admins"] is True
    assert floor["squash_only"] is True and floor["dismiss_stale"] is True
    assert floor["required_checks"], "the CE required check must be on the floor"


def test_protection_weakenings_detect_each_axis():
    floor = inst.reference_protections(ANSWERS_SCHEMA)
    assert inst.protection_weakenings({}, floor=floor) == ()
    assert inst.protection_weakenings({"required_reviews": 2}, floor=floor) == ()  # strengthen
    weak = inst.protection_weakenings(
        {"required_reviews": 0, "enforce_admins": False, "required_checks": [],
         "squash_only": False},
        floor=floor,
    )
    assert len(weak) == 4


def test_weakened_protections_require_acked_binding():
    doc = _answers(**{"github.protections": {"required_reviews": 0}})
    problems = inst.validate_answers(doc, schema=ANSWERS_SCHEMA)
    assert any("weaker grader" in p for p in problems)
    doc = _answers(**{"github.protections": {
        "required_reviews": 0,
        "ratification": {"ratified_prompt_sha": HEX, "approver_ref": "b" * 64,
                         "educate_acknowledged": True},
    }})
    assert inst.validate_answers(doc, schema=ANSWERS_SCHEMA) == ()


def test_strengthened_protections_need_no_binding():
    doc = _answers(**{"github.protections": {"required_reviews": 2, "strict": True}})
    assert inst.validate_answers(doc, schema=ANSWERS_SCHEMA) == ()


def test_bare_sudo_true_is_schema_invalid():
    doc = _answers(**{"host.sudo_grant": True})
    problems = inst.validate_answers(doc, schema=ANSWERS_SCHEMA)
    assert any("sudo_grant" in p for p in problems)


# ---------------------------------------------------------------------------
# the precedence merge — interactive > answers > detected > default
# ---------------------------------------------------------------------------
def test_merge_precedence_order():
    merged = inst.merge_answers(
        ANSWERS_SCHEMA,
        answers={"answers_version": 1, "provider": {"harness": "codex"}},
        detected={"provider.harness": "claude-code"},
        interactive={"provider.harness": "both"},
    )
    entry = merged.resolved["provider.harness"]
    assert entry.value == "both" and entry.source == "interactive"
    merged = inst.merge_answers(
        ANSWERS_SCHEMA,
        answers={"answers_version": 1},
        detected={"provider.harness": "claude-code"},
    )
    assert merged.resolved["provider.harness"].source == "detected"
    merged = inst.merge_answers(ANSWERS_SCHEMA)
    assert merged.resolved["cost.profile"].value == "default"
    assert merged.resolved["cost.profile"].source == "default"


def test_merge_surfaces_detected_fact_conflict():
    merged = inst.merge_answers(
        ANSWERS_SCHEMA,
        answers=GOOD_ANSWERS,
        detected={"github.repo": "someone-else/other-repo"},
    )
    assert any(c.key == "github.repo" for c in merged.conflicts)
    # the conflict joins the missing list (ask interactively / refuse non-interactively)
    missing = inst.missing_answers(ANSWERS_SCHEMA, merged)
    assert any(m.key == "github.repo" and m.reason == "conflict" for m in missing)
    # an interactive answer settles it
    merged = inst.merge_answers(
        ANSWERS_SCHEMA,
        answers=GOOD_ANSWERS,
        detected={"github.repo": "someone-else/other-repo"},
        interactive={"github.repo": "chmod735/creator-engine-canonical"},
    )
    missing = inst.missing_answers(ANSWERS_SCHEMA, merged)
    assert not any(m.key == "github.repo" for m in missing)


def test_cross_key_default_seeds_pilot_target():
    merged = inst.merge_answers(ANSWERS_SCHEMA, answers={
        "answers_version": 1,
        "github": {"repo": "owner/name"},
    })
    entry = merged.resolved["pilot.target_repo"]
    assert entry.value == "owner/name" and entry.source == "default"


# ---------------------------------------------------------------------------
# the missing list + the fail-closed non-interactive gate
# ---------------------------------------------------------------------------
def test_missing_answers_on_empty_input_names_the_load_bearing_keys():
    merged = inst.merge_answers(ANSWERS_SCHEMA)
    missing = {m.key: m for m in inst.missing_answers(ANSWERS_SCHEMA, merged)}
    assert "provider.harness" in missing
    assert "github.mode" in missing and "github.repo" in missing
    assert missing["github.bootstrap_token"].reason == "secret_ref_required"
    assert "github.reviewer" in missing
    # conditional inputs stay out while their condition is unmet
    assert "github.app.pem" not in missing            # app.kind defaults to shared
    assert "github.new_repo.visibility" not in missing  # mode is not "new"
    assert "cost.optout" not in missing               # profile defaults to "default"


def test_conditional_inputs_join_when_condition_holds():
    merged = inst.merge_answers(ANSWERS_SCHEMA, answers={
        "answers_version": 1,
        "github": {"mode": "new", "app": {"kind": "own"}},
    })
    missing = {m.key for m in inst.missing_answers(ANSWERS_SCHEMA, merged)}
    assert {"github.app.app_id", "github.app.client_id", "github.app.pem"} <= missing
    assert "project.name" not in missing
    # new_repo fields with defaults resolve; only true gaps ask
    assert "github.new_repo.visibility" not in missing
    assert "project.scaffold.kind" not in missing


def test_complete_answers_resolve_everything():
    merged = inst.merge_answers(ANSWERS_SCHEMA, answers=GOOD_ANSWERS)
    assert inst.missing_answers(ANSWERS_SCHEMA, merged) == ()
    inst.require_complete(())  # no-op on a complete merge


def test_require_complete_refuses_with_the_exact_list():
    merged = inst.merge_answers(ANSWERS_SCHEMA)
    missing = inst.missing_answers(ANSWERS_SCHEMA, merged)
    with pytest.raises(inst.InstallRefused) as exc:
        inst.require_complete(missing)
    message = str(exc.value)
    assert "fail-closed" in message
    for item in missing:
        assert item.key in message


# ---------------------------------------------------------------------------
# the scoped sudo pre-grant diff (fork F4)
# ---------------------------------------------------------------------------
def test_sudo_grant_diff_scoped_grant_covers_planned_installs():
    plan = inst.plan_dependencies(
        inst.REQUIRED_DEPENDENCIES,
        {"git": True, "python": True, "runsc": False, "proxy": False, "uv": True},
    )
    diff = inst.sudo_grant_diff(["runsc", "proxy"], plan)
    assert diff.converged and set(diff.covered) == {"runsc", "proxy"}


def test_sudo_grant_diff_refuses_drift_outside_the_grant():
    # ce-ops#71 §A.1: only runsc/proxy are privileged now (git/python/uv are
    # user-level ALWAYS); a privileged install OUTSIDE the grant → refuse.
    plan = inst.plan_dependencies(
        2,
        {"git": True, "python": True, "runsc": False, "proxy": False, "uv": True},
    )
    diff = inst.sudo_grant_diff(["runsc"], plan)   # proxy drifted outside the grant
    assert not diff.converged and diff.uncovered == ("proxy",)
    # no grant at all → every privileged install needs the ask
    diff = inst.sudo_grant_diff(None, plan)
    assert set(diff.uncovered) == {"runsc", "proxy"}
    # git/python/uv missing is now user-level → never a sudo install, converges
    user_level = inst.plan_dependencies(
        2, {"git": False, "python": False, "runsc": True, "proxy": True, "uv": False}
    )
    assert inst.sudo_grant_diff([], user_level).converged


# ---------------------------------------------------------------------------
# ce-ops#71 §A.1–A.3 — the tier-aware planner + the three-tier fail-closed walk.
# The tier only changes WHAT is in the plan; the SAME sudo_grant_diff converges
# for Tier 0/1 (zero root) and refuses for Tier 2 — no new fail-closed machinery.
# ---------------------------------------------------------------------------
def test_tier_deps_shape_and_sudo_set():
    assert inst.TIER_DEPS[0] == ("git", "python", "uv")
    assert inst.TIER_DEPS[1] == ("git", "python", "uv")
    assert inst.TIER_DEPS[2] == ("git", "python", "uv", "runsc", "proxy")
    # only the gVisor pairing is privileged; git/python/uv are user-level always
    assert inst._SUDO_TOOLS == frozenset({"runsc", "proxy"})
    # the flat default name still points at the heavy Tier-2 set (back-compat)
    assert inst.REQUIRED_DEPENDENCIES == inst.TIER_DEPS[2]
    assert inst.DEFAULT_ISOLATION_TIER == 2


def test_plan_dependencies_default_tier_preserves_today():
    # no tier arg == the flat Tier-2 set, preserving today's plan
    probe = {"git": True, "python": True, "runsc": False, "proxy": False, "uv": True}
    assert (
        inst.plan_dependencies(probe=probe).to_install
        == inst.plan_dependencies(2, probe).to_install
    )


def test_plan_dependencies_accepts_explicit_iterable_backcompat():
    # the pre-tier flat call (callers pass REQUIRED_DEPENDENCIES) still works
    plan = inst.plan_dependencies(inst.REQUIRED_DEPENDENCIES, {"uv": False})
    assert "uv" in plan.to_install


def test_plan_dependencies_rejects_unknown_tier():
    with pytest.raises(inst.InstallRefused):
        inst.plan_dependencies(3, {})


def test_tier0_converges_with_empty_grant():
    # governance-only: git/python/uv only, none privileged — even all-missing
    plan = inst.plan_dependencies(0, {"git": False, "python": False, "uv": False})
    assert plan.needs_sudo is False
    assert "runsc" not in {s.name for s in plan.steps}
    assert "proxy" not in {s.name for s in plan.steps}
    diff = inst.sudo_grant_diff([], plan)
    assert diff.converged and diff.uncovered == ()


def test_tier1_converges_with_empty_grant_zero_root():
    # unprivileged OS-native sandbox: same dep set; sandbox primitives are
    # probe-only, never auto-sudo → zero root with sudo_grant: []
    plan = inst.plan_dependencies(1, {"git": True, "python": True, "uv": True})
    assert plan.needs_sudo is False
    # the privileged pairing is NEVER in a Tier-1 plan
    assert "runsc" not in {s.name for s in plan.steps}
    assert "proxy" not in {s.name for s in plan.steps}
    assert inst.sudo_grant_diff([], plan).converged


def test_tier2_fails_closed_with_empty_grant():
    # the heavy opt-in: runsc/proxy missing → privileged installs → NOT converged
    probe = {"git": True, "python": True, "runsc": False, "proxy": False, "uv": True}
    plan = inst.plan_dependencies(2, probe)
    assert plan.needs_sudo is True
    diff = inst.sudo_grant_diff([], plan)
    assert not diff.converged and set(diff.uncovered) == {"runsc", "proxy"}
    # Tier 2 still requires the explicit grant — unchanged from today
    assert inst.sudo_grant_diff(["runsc", "proxy"], plan).converged


def test_build_install_plan_seam_and_tier_are_tier_conditional():
    sig = inst.sign_spec(SPEC, key_id=KEY)
    probe = {"git": True, "python": True, "runsc": True, "proxy": True, "uv": True}
    gvisor = "the runtime backend provisioning (gVisor runsc + egress proxy)"
    # Tier 2 (default) emits the gVisor seam + carries the tier
    p2 = inst.build_install_plan(SPEC, sig, pinned_keys=PINNED, probe=probe)
    assert gvisor in p2["deferred_live_seams"]
    assert p2["profile"]["isolation_tier"] == 2
    assert p2["dependencies"]["isolation_tier"] == 2
    # Tier 0/1 omit it (zero-root; no runtime backend provisioning)
    for t in (0, 1):
        p = inst.build_install_plan(SPEC, sig, pinned_keys=PINNED, probe=probe, tier=t)
        assert gvisor not in p["deferred_live_seams"]
        assert p["profile"]["isolation_tier"] == t
        assert p["dependencies"]["needs_sudo"] is False


def test_build_profile_carries_isolation_tier():
    assert inst.build_profile().isolation_tier == 2
    assert inst.build_profile(isolation_tier=1).isolation_tier == 1
    assert inst.build_profile(isolation_tier=0).runtime_policy == {
        "spend_cap_enforcement": "enforce"
    }
    with pytest.raises(inst.InstallRefused):
        inst.build_profile(isolation_tier=9)


# ---------------------------------------------------------------------------
# ce-ops#71 CORE — the BACKEND-KEYED re-frame (Edit B) + the resolver (req 5).
# Deps follow the SELECTED backend; the unprivileged os-native default needs no
# sudo; an unknown backend fails closed; the schema default stays gvisor-proxy
# (the back-compat gate, req 4).
# ---------------------------------------------------------------------------
def test_backend_deps_shape_and_no_sudo_default():
    assert inst.BACKEND_DEPS["os-native"] == ("git", "python", "uv")
    assert inst.BACKEND_DEPS["gvisor-proxy"] == ("git", "python", "uv", "runsc", "proxy")
    assert inst.BACKEND_DEPS["openshell"] == ("git", "python", "uv")
    # only the gvisor pairing is privileged across every backend
    for backend, deps in inst.BACKEND_DEPS.items():
        privileged = set(deps) & inst._SUDO_TOOLS
        assert privileged == ({"runsc", "proxy"} if backend == "gvisor-proxy" else set())
    # the schema-level default stays gvisor-proxy (req-4 back-compat gate)
    assert inst.DEFAULT_ISOLATION_BACKEND == "gvisor-proxy"


def test_resolve_isolation_backend_precedence():
    # solo-pilot governance-only → the unprivileged os-native (Edit C)
    assert inst.resolve_isolation_backend(profile="solo-pilot") == "os-native"
    # team / absent profile → the conservative back-compat default (OQ-4 escalated)
    assert inst.resolve_isolation_backend(profile="team") == "gvisor-proxy"
    assert inst.resolve_isolation_backend() == "gvisor-proxy"
    assert inst.resolve_isolation_backend(profile=None) == "gvisor-proxy"
    # an explicit selector wins over the profile default
    assert inst.resolve_isolation_backend(profile="team", explicit="os-native") == "os-native"
    # unknown explicit backend → fail-closed
    with pytest.raises(inst.InstallRefused):
        inst.resolve_isolation_backend(explicit="podman-rootless")


def test_plan_dependencies_by_backend_key():
    probe_present = {"git": True, "python": True, "uv": True, "runsc": False, "proxy": False}
    # os-native plans NO privileged installs (zero-root) even with runsc/proxy absent
    p_osn = inst.plan_dependencies("os-native", probe_present)
    assert p_osn.needs_sudo is False
    assert "runsc" not in {s.name for s in p_osn.steps}
    assert "proxy" not in {s.name for s in p_osn.steps}
    # gvisor-proxy plans the privileged pairing → needs sudo
    p_gv = inst.plan_dependencies("gvisor-proxy", probe_present)
    assert p_gv.needs_sudo is True
    assert set(p_gv.to_install) == {"runsc", "proxy"}
    # unknown backend key → fail-closed
    with pytest.raises(inst.InstallRefused):
        inst.plan_dependencies("bogus-backend")


def test_tier_for_backend_maps_and_fails_closed():
    # ce-ops#71 MINOR-C: the backend → numeric-tier attestation seam.
    assert inst.tier_for_backend("os-native") == 1
    assert inst.tier_for_backend("openshell") == 0
    assert inst.tier_for_backend("gvisor-proxy") == 2
    # unknown backend → fail-closed (never a silent fall-through to the heavy default)
    with pytest.raises(inst.InstallRefused):
        inst.tier_for_backend("podman-rootless")


def test_build_install_plan_tier_matches_resolved_backend():
    # ce-ops#71 MINOR-C: threading the resolved backend's tier makes the emitted
    # profile.isolation_tier match the backend apply uses — os-native carries Tier 1
    # and emits NO gVisor runtime seam; gvisor-proxy carries Tier 2 and does.
    sig = inst.sign_spec(SPEC, key_id=KEY)
    gvisor = "the runtime backend provisioning (gVisor runsc + egress proxy)"
    osn = inst.build_install_plan(
        SPEC, sig, pinned_keys=PINNED,
        probe={"git": True, "python": True, "uv": True},
        tier=inst.tier_for_backend("os-native"),
    )
    assert osn["profile"]["isolation_tier"] == 1
    assert gvisor not in osn["deferred_live_seams"]
    gv = inst.build_install_plan(
        SPEC, sig, pinned_keys=PINNED,
        probe={"git": True, "python": True, "uv": True, "runsc": True, "proxy": True},
        tier=inst.tier_for_backend("gvisor-proxy"),
    )
    assert gv["profile"]["isolation_tier"] == 2
    assert gvisor in gv["deferred_live_seams"]


def test_os_native_converges_with_empty_sudo_grant():
    # the #71 headline: the governance-only default succeeds with NO sudo grant,
    # through the SAME sudo_grant_diff path the tiers use.
    probe = {"git": True, "python": True, "uv": True, "runsc": False, "proxy": False}
    plan = inst.plan_dependencies("os-native", probe)
    diff = inst.sudo_grant_diff([], plan)
    assert diff.converged and diff.uncovered == ()


# ---------------------------------------------------------------------------
# the --inventory emission (the awareness artifact)
# ---------------------------------------------------------------------------
def test_inventory_emission_statuses():
    rows = {r["key"]: r for r in inst.inventory_emission(
        ANSWERS_SCHEMA,
        detected={"provider.harness": "claude-code"},
        answers={"answers_version": 1, "github": {"repo": "owner/name"}},
    )}
    assert rows["provider.harness"]["status"] == "detected:claude-code"
    assert rows["github.repo"]["status"] == "answered:owner/name"
    assert rows["cost.profile"]["status"] == "default:default"
    assert rows["github.bootstrap_token"]["status"] == "secret (ref required)"
    assert rows["github.mode"]["status"].startswith("needed (would ask at step 4")
    assert rows["github.app.pem"]["status"] == "not-applicable"
    assert rows["github.bootstrap_token"]["sensitivity"] == "secret"
    assert "D" in rows["github.repo"]["modes"]


def test_inventory_derives_from_schema_annotations_only():
    keys = {item.key for item in inst.schema_inventory(ANSWERS_SCHEMA)}
    # the meta key carries no x-ce-step → never an operator input
    assert "answers_version" not in keys
    # every journey step from host to pilot is represented
    steps = {item.step for item in inst.schema_inventory(ANSWERS_SCHEMA)}
    assert {1, 2, 3, 4, 5} <= steps


def test_greenfield_rows_derived_from_schema():
    items = inst.schema_inventory(ANSWERS_SCHEMA)
    greenfield = {item.key: item for item in items if item.key.startswith("project.")}
    assert set(greenfield) == {"project.name", "project.scaffold.kind"}
    assert all(item.step == 5 for item in greenfield.values())
    assert greenfield["project.name"].when == ("github.mode", "new")
    assert greenfield["project.name"].optional is True
    assert greenfield["project.scaffold.kind"].default == "minimal"
    assert greenfield["project.scaffold.kind"].modes == ("F", "I")


def test_greenfield_first_project_plan_extends_not_forks():
    answers = _answers(**{
        "github.mode": "new",
        "github.new_repo": {"visibility": "private", "default_branch": "main"},
        "project.name": "fresh-app",
    })
    merged = inst.merge_answers(ANSWERS_SCHEMA, answers=answers)
    missing = inst.missing_answers(ANSWERS_SCHEMA, merged)
    plan = inst.build_greenfield_first_project_plan(ANSWERS_SCHEMA, merged, missing)
    assert plan["mode"] == "greenfield"
    assert plan["project_root"] == "~/ce-workspaces/fresh-app"
    assert plan["e2_plan_ref"] == "onboard.github_leg"
    assert plan["e2_apply_required"] is True
    assert plan["first_ship_not_yet_counted"] is True
    assert "e2_convergence" not in plan
    assert plan["counters"]["inventory_inputs"] == len(inst.schema_inventory(ANSWERS_SCHEMA))
    assert plan["counters"]["missing_answers"] == len(missing)


def test_greenfield_plan_folds_e2_result_read_through():
    answers = _answers(**{
        "github.mode": "new",
        "github.new_repo": {"visibility": "private", "default_branch": "main"},
        "project.name": "fresh-app",
    })
    merged = inst.merge_answers(ANSWERS_SCHEMA, answers=answers)
    result = {
        "legs_total": 12,
        "verified_count": 12,
        "applied": 4,
        "already_satisfied": 8,
        "failed": 0,
        "refused": 0,
        "greenfield_repos_created": 1,
        "legs": [
            {"id": "workspace_checkout", "status": "applied", "verification": {"ok": True}},
            {"id": "github_repo_create", "status": "applied", "verification": {"ok": True}},
            {"id": "github_app_install", "status": "already_satisfied", "verification": {"ok": True}},
            {"id": "github_workflow_install", "status": "applied", "verification": {"ok": True}},
            {"id": "github_branch_protection", "status": "applied", "verification": {"ok": True}},
        ],
    }
    plan = inst.build_greenfield_first_project_plan(
        ANSWERS_SCHEMA,
        merged,
        (),
        e2_apply_result=result,
        e2_apply_result_ref=".ce/state/onboard/ledger.ndjson",
    )
    assert plan["e2_apply_required"] is False
    assert plan["e2_convergence"]["counts"]["verified_count"] == 12
    assert plan["e2_convergence"]["legs"]["github_branch_protection"]["verified"] is True


# ===========================================================================
# ce-ops#53 E3 — brownfield adoption inventory + planning
# ===========================================================================

def _brownfield_probe(**overrides):
    probe = {
        "enabled": True,
        "project_root": ".",
        "history": {
            "mode": "git_history_present",
            "head_sha": "a" * 40,
            "default_branch": "main",
            "commit_count": 12,
            "last_commit_time": "2026-06-12T10:00:00+00:00",
            "dirty": False,
            "tags_present": True,
            "merge_commits": 1,
            "top_changed_dirs": ["validators", "docs"],
        },
        "github": {"origin_remote": "owner/repo"},
        "ci": {
            "workflows": [
                {
                    "path": ".github/workflows/ci.yml",
                    "name": "CI",
                    "jobs": ["test"],
                    "check_names": ["CI / test"],
                }
            ],
            "current_required_checks": ["lint"],
        },
        "tests": {"commands": [{"command": "python -m pytest", "source": "pyproject.toml"}]},
        "conventions": {
            "branch_patterns": [{"value": "feature/*", "confidence": 0.8, "source": "git-branches"}],
            "commit_styles": [{"value": "conventional-commits", "confidence": 0.9, "source": "git-log"}],
        },
        "secrets": {"preflight": "required", "status": "not_run", "scanner_available": None, "findings": []},
    }
    for dotted, value in overrides.items():
        node = probe
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return probe


def test_brownfield_rows_derived_from_schema():
    items = inst.schema_inventory(ANSWERS_SCHEMA)
    brownfield = {item.key: item for item in items if item.key.startswith("brownfield.")}
    assert len(items) == 40
    assert set(brownfield) == {
        "brownfield.enabled",
        "brownfield.project_root",
        "brownfield.inventory_depth",
        "brownfield.ci.adopt_existing_workflows",
        "brownfield.ci.required_checks_strategy",
        "brownfield.tests.required_commands",
        "brownfield.history.mode",
        "brownfield.conventions.branch_pattern",
        "brownfield.conventions.commit_style",
        "brownfield.secrets.preflight",
        "brownfield.secrets.waivers",
    }
    assert all(item.step == 5 for item in brownfield.values())
    assert brownfield["brownfield.secrets.waivers"].sensitivity == "ratification"
    assert brownfield["brownfield.project_root"].modes == ("D", "F", "I")


def test_github_existing_detects_brownfield_facts():
    detected = inst.brownfield_detected_facts(_brownfield_probe())
    assert detected["github.mode"] == "existing"
    assert detected["github.repo"] == "owner/repo"
    assert detected["brownfield.enabled"] is True
    merged = inst.merge_answers(ANSWERS_SCHEMA, detected=detected)
    assert merged.value("github.mode") == "existing"
    assert merged.value("brownfield.history.mode") == "git_history_present"


def test_detected_vs_file_conflict_surfaces_for_repo_and_project_root():
    answers = _answers(**{
        "github.repo": "other/repo",
        "brownfield.project_root": "subdir",
    })
    detected = inst.brownfield_detected_facts(_brownfield_probe())
    merged = inst.merge_answers(ANSWERS_SCHEMA, answers=answers, detected=detected)
    conflicts = {c.key for c in merged.conflicts}
    assert {"github.repo", "brownfield.project_root"} <= conflicts
    missing = inst.missing_answers(ANSWERS_SCHEMA, merged)
    assert {m.key for m in missing if m.reason == "conflict"} >= {"github.repo", "brownfield.project_root"}


def test_github_actions_are_preserved_and_ce_check_is_additive():
    plan = inst.build_brownfield_adoption_plan(
        {"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=_brownfield_probe()
    )
    assert {"lint", "CI / test"} <= set(plan["ci"]["checks_to_preserve"])
    assert plan["ci"]["checks_to_add"] == ["Validate governance artifacts"]
    assert all("drop" not in step.get("id", "") for step in plan["apply_steps"])


def test_test_runner_detection_uses_declared_commands_only():
    with_command = inst.build_brownfield_adoption_plan(
        {"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=_brownfield_probe()
    )
    assert with_command["tests"]["required_commands"] == ["python -m pytest"]
    absent = inst.build_brownfield_adoption_plan(
        {"answers_version": 1},
        schema=ANSWERS_SCHEMA,
        probe=_brownfield_probe(tests={"commands": []}),
    )
    assert absent["tests"]["required_commands"] == []


def test_conventions_detection_is_advisory_and_overridable():
    plan = inst.build_brownfield_adoption_plan(
        _answers(**{
            "brownfield.conventions.branch_pattern": "release/*",
            "brownfield.conventions.commit_style": "short-imperative-subject",
        }),
        schema=ANSWERS_SCHEMA,
        probe=_brownfield_probe(),
    )
    assert plan["conventions"] == {
        "branch_pattern": "release/*",
        "commit_style": "short-imperative-subject",
    }
    assert plan["counters"]["convention_candidates_detected"] == 2


def test_history_present_adoptable_has_value_free_hash():
    probe = _brownfield_probe(secrets={"preflight": "clean", "status": "clean", "scanner_available": True, "findings": []})
    plan = inst.build_brownfield_adoption_plan({"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=probe)
    assert plan["classification"] == "adoptable"
    assert plan["history"]["mode"] == "git_history_present"
    assert len(plan["inventory_sha256"]) == 64
    assert plan["blocked"] is False


def test_history_absent_blocks_without_apply_writes():
    plan = inst.build_brownfield_adoption_plan(
        {"answers_version": 1},
        schema=ANSWERS_SCHEMA,
        probe=_brownfield_probe(history={"mode": "absent", "head_sha": None, "commit_count": 0, "dirty": False}),
    )
    assert plan["blocked"] is True
    assert plan["classification"] == "needs_baseline_capture"
    assert plan["apply_steps"] == []


def test_dirty_tree_blocks_apply():
    plan = inst.build_brownfield_adoption_plan(
        {"answers_version": 1},
        schema=ANSWERS_SCHEMA,
        probe=_brownfield_probe(**{"history.dirty": True}),
    )
    assert plan["blocked"] is True
    assert plan["classification"] == "blocked_dirty_tree"
    assert plan["apply_steps"] == []


def test_secret_preflight_required_plans_scanner_before_artifact_writes():
    plan = inst.build_brownfield_adoption_plan(
        {"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=_brownfield_probe()
    )
    assert plan["classification"] == "adoptable_after_scrub"
    ids = [step["id"] for step in plan["apply_steps"]]
    assert ids == list(inst.BROWNFIELD_APPLY_STEP_IDS)
    assert ids.index("brownfield_secret_preflight") < ids.index("brownfield_build_scaffold")
    scrub_step = next(step for step in plan["apply_steps"] if step["id"] == "brownfield_secret_preflight")
    assert ".github/workflows/ce-validate.yml" in scrub_step["scan_paths"]
    build_step = next(step for step in plan["apply_steps"] if step["id"] == "brownfield_build_scaffold")
    assert "secrets_preflight_clean_or_waived" in build_step["requires"]
    pr_step = next(step for step in plan["apply_steps"] if step["id"] == "brownfield_open_join_pr")
    assert pr_step["plan_ref"] == plan["inventory_sha256"]


def test_secret_waiver_requires_ratification_binding():
    bad = _answers(**{"brownfield.secrets.waivers": [{"finding_id": "finding-1"}]})
    problems = inst.validate_answers(bad, schema=ANSWERS_SCHEMA)
    assert any("ratification" in p for p in problems)
    good = _answers(**{"brownfield.secrets.waivers": [{
        "finding_id": "finding-1",
        "ratification": {
            "ratified_prompt_sha": HEX,
            "approver_ref": "b" * 64,
            "educate_acknowledged": True,
        },
    }]})
    assert inst.validate_answers(good, schema=ANSWERS_SCHEMA) == ()


def test_scope_seed_maps_inventory_and_skill_artifacts_are_value_free(tmp_path):
    plan = inst.build_brownfield_adoption_plan(
        {"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=_brownfield_probe()
    )
    seed = plan["artifact_plan"]["scope_seed"]
    assert "python -m pytest" in " ".join(seed["acceptance_criteria"])
    assert "CI / test" in " ".join(seed["acceptance_criteria"])
    assert seed["skill_refs"] == list(inst.BROWNFIELD_SKILL_ARTIFACT_PATHS)
    content = "\n".join(item["content"] for item in plan["artifact_plan"]["skill_artifacts"])
    assert str(tmp_path) not in content
    for forbidden in ("ghp_", "sk-", "scanner snippet", "chmod735"):
        assert forbidden not in content


def test_brownfield_plan_is_idempotent_and_paths_unique():
    probe = _brownfield_probe()
    first = inst.build_brownfield_adoption_plan({"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=probe)
    second = inst.build_brownfield_adoption_plan({"answers_version": 1}, schema=ANSWERS_SCHEMA, probe=probe)
    assert first["inventory_sha256"] == second["inventory_sha256"]
    paths = [item["path"] for item in first["artifact_plan"]["skill_artifacts"]]
    assert len(paths) == len(set(paths))


def test_docs_loop_updated_for_brownfield_without_e3_apply_executor():
    docs = "\n".join(
        (_REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "docs/contracts/installer.md",
            "docs/contracts/brownfield-adoption.md",
            "docs/llms-install.md",
            "docs/guide/pilot-runbook.md",
        )
    )
    assert "--inventory" in docs and "--plan" in docs and "--apply" in docs
    assert "brownfield_adoption" in docs
    assert "e2_brownfield_seam_unavailable" in docs
    assert "--apply-brownfield" not in docs



# ===========================================================================
# v3.5-E.3 E3-G2 — the GitHub leg, decomposed (pure planners, injected probes)
# ===========================================================================

# ---------------------------------------------------------------------------
# repo plan — existing vs new, idempotent
# ---------------------------------------------------------------------------
def test_plan_repo_existing_uses_probed_repo():
    plan = inst.plan_repo(mode="existing", repo="owner/name", repo_exists=True)
    assert plan["action"] == "use_existing" and plan["converged"] and not plan["problems"]


def test_plan_repo_existing_refuses_probed_missing_repo():
    plan = inst.plan_repo(mode="existing", repo="owner/name", repo_exists=False)
    assert plan["action"] == "refuse" and plan["problems"]


def test_plan_repo_new_plans_create_then_converges_on_rerun():
    plan = inst.plan_repo(mode="new", repo="owner/fresh",
                          new_repo={"visibility": "private", "default_branch": "main"})
    assert plan["action"] == "create"
    assert plan["steps"][0]["step"] == "create_repo"
    assert plan["steps"][0]["visibility"] == "private"
    # second run: the repo now exists → create converges to use (idempotent)
    rerun = inst.plan_repo(mode="new", repo="owner/fresh", repo_exists=True)
    assert rerun["action"] == "use_existing" and rerun["converged"]


def test_plan_repo_unresolved_repo_is_a_problem():
    plan = inst.plan_repo(mode="existing", repo=None)
    assert plan["action"] == "refuse"
    assert any("github.repo" in p for p in plan["problems"])


# ---------------------------------------------------------------------------
# bootstrap-token scope verification (a check, not an input)
# ---------------------------------------------------------------------------
def test_bootstrap_scope_table_verifies_minimal_scopes():
    table = inst.bootstrap_scope_table(inst.REQUIRED_BOOTSTRAP_SCOPES)
    assert table["ok"] and table["probed"] and table["missing"] == []
    assert {row["scope"] for row in table["rows"]} == set(inst.REQUIRED_BOOTSTRAP_SCOPES)


def test_bootstrap_scope_table_names_missing_scopes():
    table = inst.bootstrap_scope_table(["contents:write"])
    assert not table["ok"]
    assert "administration:write" in table["missing"]


def test_bootstrap_scope_table_unprobed_is_fail_closed():
    table = inst.bootstrap_scope_table(None)
    assert not table["ok"] and not table["probed"]
    assert all(row["granted"] is None for row in table["rows"])


def test_bootstrap_scope_table_org_create_only_when_needed():
    assert inst.ORG_CREATE_SCOPE not in [
        r["scope"] for r in inst.bootstrap_scope_table([])["rows"]
    ]
    assert inst.ORG_CREATE_SCOPE in [
        r["scope"] for r in inst.bootstrap_scope_table([], org_create_needed=True)["rows"]
    ]


# ce-ops#94 — right-sizing the bootstrap-PAT requirement to the operation
def test_bootstrap_required_scopes_greenfield_is_full_write_set():
    assert inst.bootstrap_required_scopes(mode="new") == inst.REQUIRED_BOOTSTRAP_SCOPES
    with_org = inst.bootstrap_required_scopes(mode="new", org_create_needed=True)
    assert inst.ORG_CREATE_SCOPE in with_org
    assert set(inst.REQUIRED_BOOTSTRAP_SCOPES).issubset(set(with_org))


def test_bootstrap_required_scopes_plain_join_is_identity_only():
    # A plain-join (any non-"new" mode) writes NOTHING with the bootstrap PAT -> identity-only.
    assert inst.bootstrap_required_scopes(mode="existing") == ()
    assert inst.bootstrap_required_scopes(mode="join", org_create_needed=True) == ()


def test_bootstrap_scope_table_identity_only_required_is_trivially_ok():
    # required=() (plain-join) -> no rows, nothing missing, ok True even when unprobed.
    table = inst.bootstrap_scope_table(None, required=())
    assert table["ok"] and table["rows"] == [] and table["missing"] == []


def test_bootstrap_scope_table_required_override_subset_ok():
    table = inst.bootstrap_scope_table(["contents:write"], required=("contents:write",))
    assert table["ok"] and table["missing"] == []
    # the default (full) requirement is unaffected by the override path
    assert not inst.bootstrap_scope_table(["contents:write"])["ok"]


# ---------------------------------------------------------------------------
# the App plan — shared vs own; click-or-detect (re-run convergence)
# ---------------------------------------------------------------------------
def test_app_plan_shared_first_run_requires_the_click():
    plan = inst.plan_github_app(kind="shared")
    assert plan["click_required"] is True and not plan["converged"]
    click = plan["steps"][0]
    assert click["step"] == "app_install_click" and click["human"] is True
    assert "/installations/new" in click["install_url"]


def test_app_plan_detected_installation_skips_the_click():
    plan = inst.plan_github_app(kind="shared", installation_id=12345678)
    assert plan["click_required"] is False and plan["converged"]
    assert plan["steps"] == []


def test_app_plan_own_requires_ids_and_pem_ref():
    plan = inst.plan_github_app(kind="own")
    assert len(plan["problems"]) == 3
    plan = inst.plan_github_app(
        kind="own", app_id="123", client_id="Iv1.abc",
        pem_ref="file:///dev/shm/ce-app.pem", installation_id=99,
    )
    assert plan["problems"] == [] and plan["converged"]


def test_app_plan_own_refuses_raw_pem():
    plan = inst.plan_github_app(kind="own", app_id="123", client_id="Iv1.abc",
                                pem_ref="-----BEGIN RSA PRIVATE KEY-----")
    assert any("SecretRef" in p for p in plan["problems"])


def test_app_bot_identity_is_the_author_identity():
    assert inst.app_bot_identity() == f"{inst.SHARED_APP_SLUG}[bot]"


# ---------------------------------------------------------------------------
# branch protection — desired-state diff, reference posture as data
# ---------------------------------------------------------------------------
def _floor():
    return inst.reference_protections(ANSWERS_SCHEMA)


def test_protection_diff_unprotected_branch_drifts_everything():
    plan = inst.plan_branch_protection(None, "reference", floor=_floor())
    assert not plan["converged"]
    assert {d["key"] for d in plan["drift"]} == set(_floor().keys())


def test_protection_diff_converges_when_current_matches_floor():
    plan = inst.plan_branch_protection(dict(_floor()), "reference", floor=_floor())
    assert plan["converged"] and plan["drift"] == []


def test_protection_diff_plans_only_the_drift():
    current = dict(_floor())
    current["enforce_admins"] = False
    plan = inst.plan_branch_protection(current, "reference", floor=_floor())
    assert [d["key"] for d in plan["drift"]] == ["enforce_admins"]
    assert plan["drift"][0]["desired"] is True


def test_protection_required_checks_apply_as_a_union():
    current = dict(_floor())
    current["required_checks"] = ["someone-elses-check"]
    plan = inst.plan_branch_protection(current, "reference", floor=_floor())
    [entry] = [d for d in plan["drift"] if d["key"] == "required_checks"]
    assert "someone-elses-check" in entry["desired"]  # never silently dropped
    assert set(_floor()["required_checks"]) <= set(entry["desired"])


def test_effective_protections_overlay_strengthen_and_ratified_weaken():
    floor = _floor()
    assert inst.effective_protections("reference", floor=floor) == floor
    stronger = inst.effective_protections({"required_reviews": 2}, floor=floor)
    assert stronger["required_reviews"] == 2 and stronger["strict"] is True
    weakened = inst.effective_protections(
        {"required_reviews": 0, "ratification": {"x": "ignored"}}, floor=floor
    )
    assert weakened["required_reviews"] == 0
    assert "ratification" not in weakened  # the binding is an attestation, not a setting


# ---------------------------------------------------------------------------
# Actions workflow plan
# ---------------------------------------------------------------------------
def test_actions_plan_installs_workflow_and_enables_actions():
    plan = inst.plan_actions_workflow(
        actions_enabled=False, workflow_present=False,
        required_check="Validate governance artifacts",
    )
    steps = {s["step"] for s in plan["steps"]}
    assert steps == {"enable_actions", "install_validate_workflow"}


def test_actions_plan_converges_when_present_and_enabled():
    plan = inst.plan_actions_workflow(
        actions_enabled=True, workflow_present=True,
        required_check="Validate governance artifacts",
    )
    assert plan["converged"] and plan["steps"] == []


# ---------------------------------------------------------------------------
# the reviewer-identity floor (no self-approval)
# ---------------------------------------------------------------------------
def test_reviewer_floor_detected_login_is_the_solo_reviewer():
    floor = inst.reviewer_identity_floor(token_login="chmod735",
                                         bot_identity="creator-engine[bot]")
    assert floor["ok"] and floor["reviewer"] == "chmod735"


def test_reviewer_floor_refuses_missing_and_bot_self_review():
    assert not inst.reviewer_identity_floor(bot_identity="creator-engine[bot]")["ok"]
    floor = inst.reviewer_identity_floor(reviewer="creator-engine[bot]",
                                         bot_identity="creator-engine[bot]")
    assert not floor["ok"] and any("no-self-approval" in p for p in floor["problems"])


# ---------------------------------------------------------------------------
# the composed GitHub leg (dry-run; mutations stay the deferred forge seam)
# ---------------------------------------------------------------------------
def _github_probe(**overrides):
    probe = {
        "origin_remote": "chmod735/creator-engine-canonical",
        "token_login": "chmod735",
        "token_scopes": list(inst.REQUIRED_BOOTSTRAP_SCOPES),
        "repo_exists": True,
        "app_installation_id": 12345678,
        "current_protections": dict(inst.reference_protections(ANSWERS_SCHEMA)),
        "actions_enabled": True,
        "workflow_present": True,
    }
    probe.update(overrides)
    return probe


def test_github_leg_converges_on_the_fully_provisioned_repo():
    plan = inst.build_github_leg_plan(GOOD_ANSWERS, schema=ANSWERS_SCHEMA, probe=_github_probe())
    assert plan["converged"]
    assert plan["human_approves"] == []          # installation detected → no click
    assert plan["branch_protection"]["drift"] == []
    assert plan["reviewer"]["ok"]


def test_github_leg_first_run_plans_the_click_and_the_drift():
    probe = _github_probe(app_installation_id=None, current_protections=None,
                          workflow_present=False)
    answers = _answers(**{"github.app": {"kind": "shared"}})
    plan = inst.build_github_leg_plan(answers, schema=ANSWERS_SCHEMA, probe=probe)
    assert not plan["converged"]
    assert plan["human_approves"] == ["the GitHub-App authorization click"]
    assert plan["branch_protection"]["drift"]
    assert any(s["step"] == "install_validate_workflow" for s in plan["actions"]["steps"])


def test_github_leg_refuses_invalid_answers_first():
    with pytest.raises(inst.InstallRefused):
        inst.build_github_leg_plan(_answers(typo_key=1), schema=ANSWERS_SCHEMA, probe=_github_probe())


def test_github_leg_surfaces_detected_repo_conflict():
    probe = _github_probe(origin_remote="someone-else/other-repo")
    plan = inst.build_github_leg_plan(GOOD_ANSWERS, schema=ANSWERS_SCHEMA, probe=probe)
    assert plan["conflicts"] and plan["conflicts"][0]["key"] == "github.repo"


def test_github_leg_unprobed_scopes_fail_closed():
    plan = inst.build_github_leg_plan(
        GOOD_ANSWERS, schema=ANSWERS_SCHEMA, probe=_github_probe(token_scopes=None)
    )
    assert not plan["bootstrap_token_scopes"]["ok"] and not plan["converged"]


def test_github_detected_facts_projection():
    detected = inst.github_detected_facts({
        "origin_remote": "o/r", "token_login": "human", "app_installation_id": 5,
    })
    assert detected == {
        "github.mode": "existing", "github.repo": "o/r",
        "github.reviewer": "human", "github.app.installation_id": 5,
    }
    assert inst.github_detected_facts(None) == {}
