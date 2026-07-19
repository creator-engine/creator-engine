"""Unit tests for deploy/automerge/materialize-automerge-policy.py.

Tests invoke the materializer script via subprocess against tmp_path repo
roots so that file-system side-effects are isolated and the script's
fail-closed contract can be verified without touching live state.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "deploy" / "automerge" / "materialize-automerge-policy.py"
_DECLARATION = _REPO_ROOT / "deploy" / "automerge" / "policy-declaration.yaml"

# Expected enabling_decision_ref from the canonical declaration
EXPECTED_ENABLING_REF = (
    "ADR-0016 ratification 2026-07-19 "
    "(ratification_prompt_sha d99b5dea8268df79e9c95e8a550b20fabae73a1c7ffe68299b43a1eeff5bb0f8)"
)

# The relative path where policy.json is written inside the repo root
_POLICY_RELATIVE = Path(".ce") / "state" / "automerge" / "policy.json"


def _run(
    *extra_args: str,
    repo_root: Path | None = None,
    declaration: Path | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(_SCRIPT),
        "--repo-root",
        str(repo_root or _REPO_ROOT),
    ]
    if declaration is not None:
        cmd += ["--declaration", str(declaration)]
    cmd += list(extra_args)
    import os
    env = os.environ.copy()
    validators_path = str(_REPO_ROOT / "validators")
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{validators_path}:{pythonpath}" if pythonpath else validators_path
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
    )


def _make_declaration(tmp_path: Path, overrides: dict | None = None) -> Path:
    import yaml  # type: ignore[import-untyped]
    decl: dict = {
        "run_mode": "ceo",
        "kill_switch": False,
        "classes": {
            "none": {"auto_merge": False},
            "docs": {"auto_merge": True},
            "code": {"auto_merge": False},
            "schema": {"auto_merge": False},
            "deploy": {"auto_merge": False},
            "governance": {"auto_merge": False},
            "identity": {"auto_merge": False},
            "security": {"auto_merge": False},
            "attestation": {"auto_merge": False},
            "redaction": {"auto_merge": False},
        },
        "tiers": {
            "carrier_changelog_mechanical": {"auto_merge": False},
            "docs_envelope": {"auto_merge": True},
            "brain_ledger_supersede": {"auto_merge": False},
        },
        "enabling_decision_ref": EXPECTED_ENABLING_REF,
    }
    if overrides:
        decl.update(overrides)
    path = tmp_path / "policy-declaration.yaml"
    path.write_text(yaml.dump(decl), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Round-trip: declaration -> expected JSON payload
# ---------------------------------------------------------------------------


def test_declaration_to_payload_round_trip(tmp_path: Path):
    """The canonical declaration materializes to the expected JSON payload."""
    result = _run("--dry-run", repo_root=tmp_path, declaration=_DECLARATION)
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["run_mode"] == "ceo"
    assert payload["kill_switch"] is False
    assert payload["classes"]["docs"]["auto_merge"] is True
    assert payload["tiers"]["docs_envelope"]["auto_merge"] is True
    assert payload["enabling_decision_ref"] == EXPECTED_ENABLING_REF

    # All other classes must be false
    for class_name in ("none", "code", "schema", "deploy", "governance",
                       "identity", "security", "attestation", "redaction"):
        assert payload["classes"][class_name]["auto_merge"] is False, (
            f"expected class {class_name!r} to be false"
        )

    # All other tiers must be false
    for tier_name in ("carrier_changelog_mechanical", "brain_ledger_supersede"):
        assert payload["tiers"][tier_name]["auto_merge"] is False, (
            f"expected tier {tier_name!r} to be false"
        )


# ---------------------------------------------------------------------------
# Dry-run: nothing written
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path: Path):
    """--dry-run must not write any file."""
    result = _run("--dry-run", repo_root=tmp_path, declaration=_DECLARATION)
    assert result.returncode == 0, result.stderr

    policy_path = tmp_path / _POLICY_RELATIVE
    assert not policy_path.exists(), "dry-run must not create policy.json"


# ---------------------------------------------------------------------------
# Actual write: file appears and is valid
# ---------------------------------------------------------------------------


def test_write_creates_policy_json(tmp_path: Path):
    """Non-dry-run materializes the file at the correct path."""
    result = _run(repo_root=tmp_path, declaration=_DECLARATION)
    assert result.returncode == 0, result.stderr

    policy_path = tmp_path / _POLICY_RELATIVE
    assert policy_path.exists(), "policy.json was not created"
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    assert payload["run_mode"] == "ceo"
    assert payload["classes"]["docs"]["auto_merge"] is True
    assert payload["tiers"]["docs_envelope"]["auto_merge"] is True
    assert payload["enabling_decision_ref"] == EXPECTED_ENABLING_REF


# ---------------------------------------------------------------------------
# Idempotency: re-run produces identical file
# ---------------------------------------------------------------------------


def test_idempotent_rerun(tmp_path: Path):
    """Running the materializer twice yields identical policy.json content."""
    _run(repo_root=tmp_path, declaration=_DECLARATION)
    policy_path = tmp_path / _POLICY_RELATIVE
    first_content = policy_path.read_text(encoding="utf-8")

    _run(repo_root=tmp_path, declaration=_DECLARATION)
    second_content = policy_path.read_text(encoding="utf-8")

    assert first_content == second_content, (
        "materialize-automerge-policy.py is not idempotent"
    )


# ---------------------------------------------------------------------------
# Malformed declaration: unknown top-level key
# ---------------------------------------------------------------------------


def test_unknown_top_level_key_exits_2(tmp_path: Path):
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["unknown_future_key"] = "oops"
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}"
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_unknown_top_level_key_no_write(tmp_path: Path):
    """Even in non-dry-run mode, unknown key must block the write."""
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["surprise"] = True
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run(repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2
    assert not (tmp_path / _POLICY_RELATIVE).exists()


# ---------------------------------------------------------------------------
# Malformed declaration: bad run_mode
# ---------------------------------------------------------------------------


def test_bad_run_mode_exits_2(tmp_path: Path):
    decl_path = _make_declaration(tmp_path, {"run_mode": "invalid_mode"})
    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_run_mode_dev_is_valid(tmp_path: Path):
    """'dev' is a valid run_mode (inert/dormant state)."""
    decl_path = _make_declaration(tmp_path, {"run_mode": "dev"})
    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 0, result.stderr


def test_run_mode_ceo_is_valid(tmp_path: Path):
    decl_path = _make_declaration(tmp_path, {"run_mode": "ceo"})
    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 0, result.stderr


def test_run_mode_strangeLoop_is_valid(tmp_path: Path):
    decl_path = _make_declaration(tmp_path, {"run_mode": "strangeLoop"})
    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Malformed declaration: empty enabling_decision_ref
# ---------------------------------------------------------------------------


def test_empty_enabling_ref_exits_2(tmp_path: Path):
    decl_path = _make_declaration(tmp_path, {"enabling_decision_ref": ""})
    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_whitespace_only_enabling_ref_exits_2(tmp_path: Path):
    decl_path = _make_declaration(tmp_path, {"enabling_decision_ref": "   "})
    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2


def test_missing_enabling_ref_exits_2(tmp_path: Path):
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    del raw["enabling_decision_ref"]
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# Malformed declaration: non-bool auto_merge flag
# ---------------------------------------------------------------------------


def test_non_bool_class_flag_exits_2(tmp_path: Path):
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["classes"]["docs"]["auto_merge"] = "yes"  # non-bool
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_non_bool_tier_flag_exits_2(tmp_path: Path):
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["tiers"]["docs_envelope"]["auto_merge"] = 1  # int, not bool
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2


def test_non_bool_kill_switch_exits_2(tmp_path: Path):
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["kill_switch"] = "off"
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# ADR-0016 predicate verification
# ---------------------------------------------------------------------------


def _materialized_state(tmp_path: Path) -> dict:
    """Materialize and return the loaded payload."""
    result = _run(repo_root=tmp_path, declaration=_DECLARATION)
    assert result.returncode == 0, result.stderr
    policy_path = tmp_path / _POLICY_RELATIVE
    return json.loads(policy_path.read_text(encoding="utf-8"))


def test_p11_run_mode_in_arming_set(tmp_path: Path):
    """P11: run_mode must be in AUTOMERGE_ARMING_RUN_MODES."""
    from creator_engine_validator.forge.automerge_policy import AUTOMERGE_ARMING_RUN_MODES
    payload = _materialized_state(tmp_path)
    assert payload["run_mode"] in AUTOMERGE_ARMING_RUN_MODES, (
        f"P11 violated: run_mode {payload['run_mode']!r} not in {AUTOMERGE_ARMING_RUN_MODES}"
    )


def test_p12_docs_class_and_docs_envelope_tier_true(tmp_path: Path):
    """P12: class_flag('docs') AND tier_flag('docs_envelope') must both be True."""
    payload = _materialized_state(tmp_path)
    assert payload["classes"]["docs"]["auto_merge"] is True, (
        "P12 violated: docs class flag is not True"
    )
    assert payload["tiers"]["docs_envelope"]["auto_merge"] is True, (
        "P12 violated: docs_envelope tier flag is not True"
    )


def test_p13_enabling_decision_ref_non_empty(tmp_path: Path):
    """P13: enabling_decision_ref must be a non-empty string."""
    payload = _materialized_state(tmp_path)
    ref = payload.get("enabling_decision_ref")
    assert isinstance(ref, str) and ref.strip(), (
        "P13 violated: enabling_decision_ref is absent or empty"
    )


def test_p13_enabling_decision_ref_cites_adr_0016(tmp_path: Path):
    """P13: enabling_decision_ref must cite ADR-0016 ratification."""
    payload = _materialized_state(tmp_path)
    ref = payload.get("enabling_decision_ref", "")
    assert "ADR-0016" in ref, (
        f"P13: enabling_decision_ref does not cite ADR-0016: {ref!r}"
    )
    assert "d99b5dea8268df79e9c95e8a550b20fabae73a1c7ffe68299b43a1eeff5bb0f8" in ref, (
        f"P13: enabling_decision_ref does not include the ratification_prompt_sha: {ref!r}"
    )


# ---------------------------------------------------------------------------
# Malformed declaration: unknown mutation-class and unknown tier name
# ---------------------------------------------------------------------------


def test_unknown_mutation_class_exits_2(tmp_path: Path):
    """Unknown mutation class name in classes section must exit 2, nothing written."""
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["classes"]["malicious_class"] = {"auto_merge": False}
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}\nstderr: {result.stderr}"
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_unknown_mutation_class_no_write(tmp_path: Path):
    """Even in non-dry-run mode, unknown mutation class must block the write."""
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["classes"]["malicious_class"] = {"auto_merge": False}
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run(repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_unknown_tier_name_exits_2(tmp_path: Path):
    """Unknown tier name in tiers section must exit 2, nothing written."""
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["tiers"]["nonexistent_tier"] = {"auto_merge": False}
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run("--dry-run", repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2, f"expected exit 2, got {result.returncode}\nstderr: {result.stderr}"
    assert not (tmp_path / _POLICY_RELATIVE).exists()


def test_unknown_tier_name_no_write(tmp_path: Path):
    """Even in non-dry-run mode, unknown tier name must block the write."""
    import yaml
    decl_path = _make_declaration(tmp_path)
    raw = yaml.safe_load(decl_path.read_text(encoding="utf-8"))
    raw["tiers"]["nonexistent_tier"] = {"auto_merge": False}
    decl_path.write_text(yaml.dump(raw), encoding="utf-8")

    result = _run(repo_root=tmp_path, declaration=decl_path)
    assert result.returncode == 2
    assert not (tmp_path / _POLICY_RELATIVE).exists()
