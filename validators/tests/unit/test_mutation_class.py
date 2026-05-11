from copy import deepcopy
from pathlib import Path

from creator_engine_validator.checks.mutation_class import (
    BASELINE_NAMES,
    PRIVILEGED_NAMES,
    _build_index,
    validate_overlay_file,
    validate_tasks_sidecar_against_taxonomy,
    validate_taxonomy_file,
)
from creator_engine_validator.loader import load_yaml


def _baseline_data():
    return load_yaml("docs/contracts/mutation-class-taxonomy.yml")


def test_baseline_taxonomy_file_is_well_formed():
    data = _baseline_data()
    errors = validate_taxonomy_file(Path("docs/contracts/mutation-class-taxonomy.yml"), data)
    assert errors == []


def test_baseline_index_contains_all_nine_baseline_names():
    data = _baseline_data()
    index = _build_index([e for e in data if isinstance(e, dict)], [])
    for name in BASELINE_NAMES:
        assert name in index
        assert index[name].get("is_baseline") is True


def test_missing_baseline_class_cites_fr006():
    data = [e for e in _baseline_data() if e.get("name") != "docs"]
    errors = validate_taxonomy_file(Path("fixture.yml"), data)
    assert any(error.code == "FR-006" and "'docs'" in error.message for error in errors)
    assert all(error.contract == "docs/contracts/mutation-class-taxonomy.md" for error in errors)


def test_duplicate_baseline_class_cites_fr006():
    data = list(_baseline_data())
    docs_entry = next(e for e in data if e.get("name") == "docs")
    data.append(deepcopy(docs_entry))
    errors = validate_taxonomy_file(Path("fixture.yml"), data)
    assert any(
        error.code == "FR-006" and "more than once" in error.message and "'docs'" in error.message
        for error in errors
    )


def test_action_outside_reserved_vocabulary_cites_fr006():
    data = deepcopy(_baseline_data())
    docs_entry = next(e for e in data if e.get("name") == "docs")
    docs_entry["action_vocabulary"].append("invent_new_action")
    errors = validate_taxonomy_file(Path("fixture.yml"), data)
    assert any(
        error.code == "FR-006"
        and "/action_vocabulary" in error.path
        and "'invent_new_action'" in error.message
        for error in errors
    )


def test_agent_permitted_action_outside_action_vocabulary_cites_fr006():
    data = deepcopy(_baseline_data())
    docs_entry = next(e for e in data if e.get("name") == "docs")
    docs_entry["action_vocabulary"] = [a for a in docs_entry["action_vocabulary"] if a != "edit"]
    docs_entry["agent_permitted_actions"] = ["edit"]
    errors = validate_taxonomy_file(Path("fixture.yml"), data)
    assert any(
        error.code == "FR-006"
        and "/agent_permitted_actions" in error.path
        and "not declared in action_vocabulary" in error.message
        for error in errors
    )


def test_reading_a_violation_in_agent_permitted_actions_cites_fr008():
    data = deepcopy(_baseline_data())
    docs_entry = next(e for e in data if e.get("name") == "docs")
    docs_entry["action_vocabulary"].append("merge")
    docs_entry["agent_permitted_actions"].append("merge")
    errors = validate_taxonomy_file(Path("fixture.yml"), data)
    assert any(
        error.code == "FR-008"
        and "reserved-restricted action" in error.message
        and "'merge'" in error.message
        for error in errors
    )


def test_privileged_class_missing_human_ratification_cites_fr008():
    data = deepcopy(_baseline_data())
    deploy_entry = next(e for e in data if e.get("name") == "deploy")
    deploy_entry["human_ratification_required"] = False
    errors = validate_taxonomy_file(Path("fixture.yml"), data)
    assert any(
        error.code == "FR-008"
        and "human_ratification_required" in error.path
        and "'deploy'" in error.message
        for error in errors
    )
    assert "deploy" in PRIVILEGED_NAMES


def test_overlay_reusing_baseline_name_cites_fr006():
    overlay = [
        {
            "name": "docs",
            "is_baseline": False,
            "description": "Tenant override (forbidden).",
            "action_vocabulary": ["propose"],
            "agent_permitted_actions": ["propose"],
            "human_ratification_required": False,
        }
    ]
    errors = validate_overlay_file(Path("tenants/example/mutation-classes.yml"), overlay)
    assert any(
        error.code == "FR-006"
        and "/0/name" in error.path
        and "reuses baseline class name" in error.message
        for error in errors
    )


def test_overlay_extension_with_unique_name_passes():
    overlay = [
        {
            "name": "tenant-research",
            "is_baseline": False,
            "description": "Tenant-only class for research artefacts.",
            "action_vocabulary": ["propose", "edit", "commit", "open_pr", "attest", "advise_only"],
            "agent_permitted_actions": ["propose", "edit", "attest"],
            "human_ratification_required": False,
        }
    ]
    errors = validate_overlay_file(Path("tenants/example/mutation-classes.yml"), overlay)
    assert errors == []


def test_overlay_entry_claiming_is_baseline_true_cites_fr006():
    overlay = [
        {
            "name": "tenant-research",
            "is_baseline": True,
            "description": "Forbidden: extension claims baseline status.",
            "action_vocabulary": ["propose", "edit", "commit", "open_pr", "attest", "advise_only"],
            "agent_permitted_actions": ["propose", "edit", "attest"],
            "human_ratification_required": False,
        }
    ]
    errors = validate_overlay_file(Path("tenants/example/mutation-classes.yml"), overlay)
    assert any(
        error.code == "FR-006"
        and "/0/is_baseline" in error.path
        and "is_baseline: false" in error.message
        for error in errors
    )
    assert all(error.contract == "docs/contracts/mutation-class-taxonomy.md" for error in errors)


def test_overlay_entry_missing_is_baseline_field_cites_fr006():
    overlay = [
        {
            "name": "tenant-research",
            "description": "Forbidden: extension omits is_baseline.",
            "action_vocabulary": ["propose", "edit", "commit", "open_pr", "attest", "advise_only"],
            "agent_permitted_actions": ["propose", "edit", "attest"],
            "human_ratification_required": False,
        }
    ]
    errors = validate_overlay_file(Path("tenants/example/mutation-classes.yml"), overlay)
    assert any(
        error.code == "FR-006" and "/0/is_baseline" in error.path for error in errors
    )


def test_overlay_duplicate_extension_class_names_cites_fr006():
    overlay = [
        {
            "name": "tenant-research",
            "is_baseline": False,
            "description": "First entry.",
            "action_vocabulary": ["propose", "edit", "attest"],
            "agent_permitted_actions": ["propose", "edit", "attest"],
            "human_ratification_required": False,
        },
        {
            "name": "tenant-research",
            "is_baseline": False,
            "description": "Duplicate name within overlay.",
            "action_vocabulary": ["propose", "advise_only"],
            "agent_permitted_actions": ["propose", "advise_only"],
            "human_ratification_required": False,
        },
    ]
    errors = validate_overlay_file(Path("tenants/example/mutation-classes.yml"), overlay)
    assert any(
        error.code == "FR-006"
        and "/1/name" in error.path
        and "duplicate tenant extension class name" in error.message
        for error in errors
    )


def test_tasks_sidecar_mismatch_cites_fr027a_and_contract():
    data = _baseline_data()
    index = _build_index([e for e in data if isinstance(e, dict)], [])
    sidecar = {
        "spec_ref": "spec.creator-engine.yml",
        "tasks": [
            {
                "id": "BAD-001",
                "title": "docs declaring deploy",
                "mutation_class": "docs",
                "permitted_actions": ["deploy"],
                "verification_evidence_ref": "ref",
                "author_actor_id": "agent",
            }
        ],
    }
    errors = validate_tasks_sidecar_against_taxonomy(
        Path("examples/malformed/tasks.creator-engine.class-action-mismatch.yml"), sidecar, index
    )
    assert any(
        error.code == "FR-027a"
        and "/tasks/0/permitted_actions" in error.path
        and "'deploy'" in error.message
        for error in errors
    )
    assert all(error.contract == "docs/contracts/mutation-class-taxonomy.md" for error in errors)


def test_tasks_sidecar_unknown_class_cites_fr006():
    data = _baseline_data()
    index = _build_index([e for e in data if isinstance(e, dict)], [])
    sidecar = {
        "spec_ref": "spec.creator-engine.yml",
        "tasks": [
            {
                "id": "BAD-002",
                "title": "unknown class",
                "mutation_class": "not-a-real-class",
                "permitted_actions": ["edit"],
                "verification_evidence_ref": "ref",
                "author_actor_id": "agent",
            }
        ],
    }
    errors = validate_tasks_sidecar_against_taxonomy(Path("fixture.yml"), sidecar, index)
    assert any(
        error.code == "FR-006"
        and "/tasks/0/mutation_class" in error.path
        and "'not-a-real-class'" in error.message
        for error in errors
    )


def test_well_formed_tasks_sidecar_passes():
    data = _baseline_data()
    index = _build_index([e for e in data if isinstance(e, dict)], [])
    sidecar = load_yaml("examples/well-formed/tasks.creator-engine.yml")
    errors = validate_tasks_sidecar_against_taxonomy(
        Path("examples/well-formed/tasks.creator-engine.yml"), sidecar, index
    )
    assert errors == []
