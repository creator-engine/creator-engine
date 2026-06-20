from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema.validators import validator_for


SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "tasks.schema.yaml"
HEX64 = "a" * 64


def _validator():
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema)


def _minimal_handoff(scope: dict):
    return {
        "kind": "tasks-handoff",
        "schema_version": "1",
        "source": {
            "spec_ref": "specs/x/spec.md",
            "plan_ref": "specs/x/plan.md",
            "tasks_ref": "specs/x/tasks.md",
        },
        "ratification": {
            "ratifier_ref": HEX64,
            "ratified_task_set_sha256": HEX64,
            "ratified_at": "2026-06-20T00:00:00Z",
            "authority_basis": "operator",
        },
        "sha_binding": {
            "algorithm": "sha256",
            "canonicalization": "ce-tasks-handoff-v1",
            "task_set_sha256": HEX64,
            "source_artifacts": {
                "spec_sha256": HEX64,
                "plan_sha256": HEX64,
                "tasks_sha256": HEX64,
            },
        },
        "tasks": [
            {
                "id": "T001",
                "goal": "Do the task.",
                "done_when": ["Done."],
                "mutation_class": "docs",
                "permitted_actions": ["edit"],
                "scope": deepcopy(scope),
                "verification": {
                    "required_commands": ["true"],
                    "evidence_refs": ["evidence/log.txt"],
                },
                "sha_binding": {
                    "algorithm": "sha256",
                    "canonicalization": "ce-tasks-handoff-v1",
                    "task_spec_sha256": HEX64,
                },
                "do_not_replan": True,
                "harness": {
                    "role": "implementer",
                    "allowed_harnesses": ["codex"],
                    "requires_containment": True,
                    "stop_conditions": ["task_sha_drift"],
                },
            }
        ],
    }


def _errors_for_scope(scope: dict):
    return list(_validator().iter_errors(_minimal_handoff(scope)))


def test_scope_empty_requires_explicit_no_file_change():
    assert _errors_for_scope({"allowed_paths": []})


def test_scope_no_file_change_allows_empty_allowed_paths():
    assert _errors_for_scope({"allowed_paths": [], "no_file_change": True}) == []


def test_scope_exact_allowed_path_passes():
    assert _errors_for_scope({"allowed_paths": ["docs/x.md"]}) == []


def test_scope_breadth_rejects_recursive_and_root_globs():
    assert _errors_for_scope({"allowed_paths": ["**"]})
    assert _errors_for_scope({"allowed_paths": ["*.py"]})


def test_scope_breadth_allows_named_directory_glob():
    assert _errors_for_scope({"allowed_paths": ["src/foo/*.py"]}) == []


def test_scope_prohibited_paths_are_exact_only():
    assert _errors_for_scope({"allowed_paths": ["docs/x.md"], "prohibited_paths": ["src/*.py"]})
