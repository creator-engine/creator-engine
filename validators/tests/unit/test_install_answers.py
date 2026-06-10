"""Unit tests for the ``install_answers`` check (v3.5-E.3).

The Ring-1 enforcement of the committable answers file: discovery by
canonical basename; schema validation (fail-closed unknown keys); the
raw-secret refusal; the ratified-HUMAN-only governance-weakening bindings
(cost opt-out + branch-protection floor). The check is SHARED (no v3 import)
and the governance floor it enforces is the SCHEMA's
``x-ce-reference-posture`` data — the same floor the v3 engine derives.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import install_answers as ia
from creator_engine_validator.checks import registered_checks

HEX_A = "a" * 64
HEX_B = "b" * 64

GOOD = """\
answers_version: 1
profile: solo-pilot
host:
  sudo_grant: [runsc, proxy]
cost:
  profile: default
provider:
  harness: claude-code
  anthropic_api_key: env://ANTHROPIC_API_KEY
github:
  mode: existing
  repo: chmod735/creator-engine-canonical
  bootstrap_token: prompt://github-bootstrap-token
  app:
    kind: shared
  protections: reference
  reviewer: chmod735
"""


def _write(tmp_path: Path, content: str, name: str = ia.ANSWERS_BASENAME) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _codes(tmp_path: Path) -> list[str]:
    return [e.code for e in ia.run([tmp_path]).errors]


def test_check_is_registered():
    assert "install_answers" in registered_checks()


def test_well_formed_answers_pass(tmp_path):
    _write(tmp_path, GOOD)
    assert _codes(tmp_path) == []


def test_qualified_basename_is_discovered(tmp_path):
    _write(tmp_path, GOOD, name=f"vps-pilot.{ia.ANSWERS_BASENAME}")
    documents, errors = ia.iter_answers_files([tmp_path])
    assert len(documents) == 1 and errors == []


def test_unrelated_yaml_is_not_discovered(tmp_path):
    _write(tmp_path, "not: an answers file\n", name="config.yaml")
    documents, errors = ia.iter_answers_files([tmp_path])
    assert documents == [] and errors == []


def test_unparseable_answers_file_is_surfaced_not_skipped(tmp_path):
    _write(tmp_path, "answers_version: [unclosed\n")
    assert ia.CODE_INVALID in _codes(tmp_path)
    _write(tmp_path, "- just\n- a\n- list\n")
    assert ia.CODE_INVALID in _codes(tmp_path)


def test_unknown_key_fails_closed(tmp_path):
    _write(tmp_path, GOOD + "workspce_root: typo\n")
    assert ia.CODE_SCHEMA in _codes(tmp_path)


def test_raw_secret_value_is_refused(tmp_path):
    _write(tmp_path, GOOD.replace(
        "bootstrap_token: prompt://github-bootstrap-token",
        "bootstrap_token: ghp_rawtokenvalue123",
    ))
    codes = _codes(tmp_path)
    assert ia.CODE_SCHEMA in codes        # the schema pattern layer
    assert ia.CODE_RAW_SECRET in codes    # the belt-and-braces layer


def test_custom_cost_profile_without_binding_is_refused(tmp_path):
    _write(tmp_path, GOOD.replace("profile: default", "profile: custom"))
    assert ia.CODE_OPTOUT_UNRATIFIED in _codes(tmp_path)


def test_custom_cost_profile_with_acked_binding_passes(tmp_path):
    content = GOOD.replace(
        "cost:\n  profile: default",
        "cost:\n  profile: custom\n  optout:\n"
        f"    ratified_prompt_sha: {HEX_A}\n"
        f"    approver_ref: {HEX_B}\n"
        "    educate_acknowledged: true",
    )
    _write(tmp_path, content)
    assert _codes(tmp_path) == []


def test_weakened_protections_without_binding_are_refused(tmp_path):
    _write(tmp_path, GOOD.replace(
        "protections: reference",
        "protections:\n    required_reviews: 0",
    ))
    assert ia.CODE_WEAKENED_UNRATIFIED in _codes(tmp_path)


def test_weakened_protections_with_acked_binding_pass(tmp_path):
    _write(tmp_path, GOOD.replace(
        "protections: reference",
        "protections:\n"
        "    required_reviews: 0\n"
        "    ratification:\n"
        f"      ratified_prompt_sha: {HEX_A}\n"
        f"      approver_ref: {HEX_B}\n"
        "      educate_acknowledged: true",
    ))
    assert _codes(tmp_path) == []


def test_strengthened_protections_need_no_binding(tmp_path):
    _write(tmp_path, GOOD.replace(
        "protections: reference",
        "protections:\n    required_reviews: 2",
    ))
    assert _codes(tmp_path) == []


def test_floor_matches_the_v3_engine_floor():
    """The check and the v3 engine must enforce the SAME floor — both derive
    it from the schema's x-ce-reference-posture (single source of truth)."""
    from creator_engine_validator import v3_installer as inst

    schema = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / ia.SCHEMA).read_text(encoding="utf-8")
    )
    engine_floor = inst.reference_protections(schema)
    check_floor = (
        schema["properties"]["github"]["properties"]["protections"]["x-ce-reference-posture"]
    )
    assert engine_floor == check_floor
    desired = {"required_reviews": 0, "enforce_admins": False}
    assert list(inst.protection_weakenings(desired, floor=engine_floor)) == list(
        ia._protection_weakenings(desired, check_floor)
    )


def test_check_module_is_shared_no_v3_import():
    # the version_boundary check enforces this repo-wide; this is the focused guard
    source = Path(ia.__file__).read_text(encoding="utf-8")
    for forbidden in ("from .. import v3_installer", "from ..v3_installer import",
                      "import creator_engine_validator.v3_installer"):
        assert forbidden not in source, (
            "the shared check must not import the v3 engine (version_boundary ratchet)"
        )
