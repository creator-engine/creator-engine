from __future__ import annotations

import pytest

from creator_engine_validator.forge.mutation_classifier import (
    AUTO_CLASSES,
    GESTURE_CLASSES,
    MutationPolicy,
    default_mutation_policy,
    mutation_class_for_paths,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("README.md", "docs"),
        ("docs/operator-guide.md", "docs"),
        (".ce/changelog/ce291.md", "docs"),
        (".ce/pr-manifests/ce291.md", "docs"),
        ("validators/creator_engine_validator/forge/automerge_policy.py", "code"),
        ("tools/local-helper.py", "code"),
        ("schemas/automerge-policy.schema.yaml", "schema"),
        ("surfaces/manifest.yaml", "schema"),
        (".github/workflows/ci.yml", "deploy"),
        ("Dockerfile", "deploy"),
        (".ce/contracts/operator-wall.md", "governance"),
        ("docs/contracts/ratification-flow.md", "governance"),
        ("playbooks/review.md", "governance"),
        ("validators/creator_engine_validator/secret_identity.py", "identity"),
        ("schemas/identity-registry.schema.yaml", "identity"),
        ("validators/creator_engine_validator/forge/cred_injection_proxy.py", "security"),
        ("tools/egress-broker/main.py", "security"),
        ("validators/creator_engine_validator/forge/approval_capability.py", "attestation"),
        ("validators/creator_engine_validator/forge/_redact.py", "redaction"),
    ],
)
def test_classifier_path_table(path: str, expected: str) -> None:
    assert mutation_class_for_paths([path]) == expected


def test_highest_risk_wins() -> None:
    assert (
        mutation_class_for_paths(
            [
                "README.md",
                "validators/creator_engine_validator/work_sizing.py",
                "schemas/automerge-policy.schema.yaml",
                "validators/creator_engine_validator/forge/approval_capability.py",
            ]
        )
        == "attestation"
    )


def test_single_path_matching_multiple_classes_uses_highest_risk() -> None:
    assert mutation_class_for_paths(["docs/contracts/approval-policy.md"]) == "governance"


def test_unknown_path_fails_closed_to_policy_class() -> None:
    assert mutation_class_for_paths(["unmapped/runtime.bin"]) == "redaction"


def test_empty_path_set_fails_closed() -> None:
    assert mutation_class_for_paths([]) == "redaction"


def test_policy_data_controls_predicates() -> None:
    policy = MutationPolicy.from_payload(
        {
            "class_order": list(default_mutation_policy().class_order),
            "fail_closed_class": "redaction",
            "path_predicates": {
                "docs": ["notes/**"],
                "redaction": ["secret/**"],
            },
        }
    )
    assert mutation_class_for_paths(["notes/brief.txt"], policy) == "docs"
    assert mutation_class_for_paths(["README.md"], policy) == "redaction"


def test_auto_classes_remain_none_and_docs_only() -> None:
    assert AUTO_CLASSES == frozenset({"none", "docs"})


def test_gesture_classes_cover_every_non_auto_class() -> None:
    assert GESTURE_CLASSES == frozenset(
        {
            "code",
            "schema",
            "deploy",
            "governance",
            "identity",
            "security",
            "attestation",
            "redaction",
        }
    )
