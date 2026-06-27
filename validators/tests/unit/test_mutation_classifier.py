"""Unit tests for forge.mutation_classifier — path-to-mutation-class classifier.

Covers:
- All baseline mutation classes (docs/code/schema/deploy/governance/identity/
  security/attestation/redaction).
- Fail-closed contract (empty list → docs; unknown path → code).
- Privileged path → GESTURE (never AUTO).
- Monotonic escalation: highest-risk class wins across all changed paths.
- Key individual predicates for each class.
"""
from __future__ import annotations

import pytest

from creator_engine_validator.forge.mutation_classifier import (
    AUTO_CLASSES,
    GESTURE_CLASSES,
    PRIVILEGED_CLASSES,
    mutation_class_for_paths,
)


# ── Fail-closed contract ──────────────────────────────────────────────────────

def test_empty_paths_returns_docs():
    """Empty path list → docs (lowest non-none class, fail-closed safe)."""
    assert mutation_class_for_paths([]) == "docs"


def test_unknown_path_falls_back_to_code():
    """A path matching no predicate → 'code' (conservative)."""
    result = mutation_class_for_paths(["some/random/unknown/file.py"])
    assert result == "code"


# ── docs class ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "docs/getting-started.md",
    "docs/architecture/ADR-0001.md",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "NOTICE",  # no suffix but doesn't have .md; fallthrough to code
    ".ce/changelog/2026-06-27-fix.md",
    ".ce/pr-manifests/pr-123.md",
    "docs/operations/PROTOCOL.md",
])
def test_docs_paths(path):
    result = mutation_class_for_paths([path])
    # NOTICE has no .md suffix so it falls to code; just check .md paths are docs
    if path.endswith(".md"):
        assert result == "docs", f"Expected docs for {path!r}, got {result!r}"


def test_docs_subdir_without_contracts():
    # docs/ paths that are not docs/contracts/ are docs
    assert mutation_class_for_paths(["docs/operations/PROTOCOL.md"]) == "docs"


def test_docs_contracts_path_is_governance():
    # docs/contracts/** is governance, not docs
    result = mutation_class_for_paths(["docs/contracts/mutation-class-taxonomy.md"])
    assert result == "governance"


# ── code class ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "validators/creator_engine_validator/work_sizing.py",
    "validators/creator_engine_validator/checks/some_check.py",
    "validators/tests/unit/test_something.py",
    "tools/some_tool.py",
    "some_random/app_source.py",
])
def test_code_paths(path):
    assert mutation_class_for_paths([path]) == "code"


# ── schema class ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "schemas/work-sizing.schema.yaml",
    "schemas/automerge-policy.schema.yaml",
    "schemas/automerge-decision.schema.yaml",
    "surfaces/manifest.yaml",
    "some/thing.schema.yaml",
    "other/thing.schema.json",
])
def test_schema_paths(path):
    assert mutation_class_for_paths([path]) == "schema"


# ── deploy class ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    ".github/workflows/ci.yml",
    ".github/workflows/ce-automerge.yml",
    ".github/CODEOWNERS",
    "deploy/systemd/ce.service",
    "Dockerfile",
    "dockerfile",
    "Dockerfile.prod",
    "docker-compose.yml",
    "deploy/k8s/deployment.yaml",
    "install.sh",
])
def test_deploy_paths(path):
    assert mutation_class_for_paths([path]) == "deploy"


# ── governance class ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "playbooks/controller/briefs/dispatch.md",
    "playbooks/governance/review.md",
    "governance/policy.md",
    "docs/contracts/mutation-class-taxonomy.md",
    ".ce/contracts/approval-policy.md",
    "contracts/review-evidence.md",
])
def test_governance_paths(path):
    assert mutation_class_for_paths([path]) == "governance"


def test_governance_md_returns_governance():
    assert mutation_class_for_paths(["GOVERNANCE.md"]) == "governance"


# ── identity class ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "validators/creator_engine_validator/secret_identity.py",
    "schemas/identity-registry.schema.yaml",
    "schemas/reviewer-registry.schema.yaml",
])
def test_identity_paths(path):
    assert mutation_class_for_paths([path]) == "identity"


# ── security class ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "validators/creator_engine_validator/forge/cred_injection_proxy.py",
    "tools/egress-broker/main.py",
    "tools/egress_broker/config.py",
])
def test_security_paths(path):
    assert mutation_class_for_paths([path]) == "security"


# ── attestation class ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "validators/creator_engine_validator/forge/approval_capability.py",
])
def test_attestation_paths(path):
    assert mutation_class_for_paths([path]) == "attestation"


# ── redaction class ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "validators/creator_engine_validator/forge/_redact.py",
    "validators/creator_engine_validator/forge/redact.py",
])
def test_redaction_paths(path):
    assert mutation_class_for_paths([path]) == "redaction"


# ── Monotonic escalation ─────────────────────────────────────────────────────

def test_mixed_docs_and_code_escalates_to_code():
    """docs + code → code."""
    result = mutation_class_for_paths([
        "README.md",
        "validators/creator_engine_validator/some_module.py",
    ])
    assert result == "code"


def test_mixed_code_and_schema_escalates_to_schema():
    """code + schema → schema."""
    result = mutation_class_for_paths([
        "validators/creator_engine_validator/work_sizing.py",
        "schemas/work-sizing.schema.yaml",
    ])
    assert result == "schema"


def test_mixed_schema_and_deploy_escalates_to_deploy():
    """schema + deploy → deploy."""
    result = mutation_class_for_paths([
        "schemas/something.schema.yaml",
        ".github/workflows/ci.yml",
    ])
    assert result == "deploy"


def test_mixed_docs_and_privileged_escalates_to_privileged():
    """docs + approval_capability → attestation (privileged)."""
    result = mutation_class_for_paths([
        "README.md",
        "validators/creator_engine_validator/forge/approval_capability.py",
    ])
    assert result == "attestation"


def test_mixed_code_and_egress_broker_escalates_to_security():
    """code + egress-broker → security."""
    result = mutation_class_for_paths([
        "validators/creator_engine_validator/work_sizing.py",
        "tools/egress-broker/server.py",
    ])
    assert result == "security"


# ── AUTO_CLASSES / GESTURE_CLASSES sets ──────────────────────────────────────

def test_auto_classes_are_docs_and_none():
    assert "docs" in AUTO_CLASSES
    assert "none" in AUTO_CLASSES


def test_gesture_classes_covers_all_non_auto():
    """Every non-AUTO class is in GESTURE_CLASSES."""
    all_non_auto = {"code", "schema", "deploy", "governance", "identity", "security", "attestation", "redaction"}
    assert all_non_auto == GESTURE_CLASSES


def test_privileged_classes_subset_of_gesture_classes():
    assert PRIVILEGED_CLASSES <= GESTURE_CLASSES


def test_docs_only_pr_is_auto_candidate():
    """A PR with only .md files classifies to docs, which is in AUTO_CLASSES."""
    result = mutation_class_for_paths([
        "README.md",
        "docs/getting-started.md",
        "CHANGELOG.md",
    ])
    assert result in AUTO_CLASSES


def test_privileged_path_pr_is_never_auto():
    """A PR touching any privileged path is NOT in AUTO_CLASSES."""
    privileged_paths = [
        "validators/creator_engine_validator/forge/approval_capability.py",  # attestation
        "validators/creator_engine_validator/forge/cred_injection_proxy.py",  # security
        "validators/creator_engine_validator/forge/_redact.py",               # redaction
        "validators/creator_engine_validator/secret_identity.py",             # identity
        "playbooks/governance/policy.md",                                      # governance
    ]
    for path in privileged_paths:
        result = mutation_class_for_paths([path])
        assert result not in AUTO_CLASSES, (
            f"Privileged path {path!r} classified as {result!r} which is in AUTO_CLASSES — "
            "this is a false-AUTO on a privileged path!"
        )
        assert result in GESTURE_CLASSES, (
            f"Privileged path {path!r} classified as {result!r} but not in GESTURE_CLASSES"
        )


def test_github_workflows_never_auto():
    """.github/** paths must not be AUTO."""
    result = mutation_class_for_paths([".github/workflows/ci.yml"])
    assert result not in AUTO_CLASSES


def test_schema_paths_never_auto():
    """Schema paths must not be AUTO."""
    result = mutation_class_for_paths(["schemas/some-schema.schema.yaml"])
    assert result not in AUTO_CLASSES
