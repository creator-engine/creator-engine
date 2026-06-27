"""Path-to-mutation-class classifier for the CEO-mode auto-merge policy.

``mutation_class_for_paths(changed_paths)`` returns the *highest-risk* mutation
class touched by a PR's changed paths, fail-closed: an unknown or privileged
path maps to the most-privileged class, never AUTO.

This module is pure/offline: no network, no subprocess, no disk writes, no
randomness. It only inspects path strings against a deterministic predicate table.
The predicate table deliberately mirrors the mutation class taxonomy in
``work_sizing.py``/``_RISK_TABLE`` — both must stay consistent.

Design invariants:
- Fail-closed: an empty path list → ``"docs"`` (lowest non-none class, safest
  possible claim for a PR with no changed paths). A path matching no predicate
  → falls through to ``"code"`` (conservative middle ground).
- Privilege escalates monotonically: the classifier always returns the
  *highest-risk* class across all changed paths.
- No mutation: this module only classifies; it never triggers merges or
  capability minting.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Final

# Ordered from LOWEST risk to HIGHEST risk.  The ordering determines which class
# wins when multiple predicates match across a PR's changed paths.
_CLASS_ORDER: Final[tuple[str, ...]] = (
    "none",
    "docs",
    "code",
    "schema",
    "deploy",
    "governance",
    "identity",
    "security",
    "attestation",
    "redaction",
)

# Sentinel for the ``none`` / no-content case (truly empty PR).
_CLASS_NONE_IDX: Final[int] = _CLASS_ORDER.index("none")
_CLASS_DOCS_IDX: Final[int] = _CLASS_ORDER.index("docs")
_CLASS_CODE_IDX: Final[int] = _CLASS_ORDER.index("code")


def _class_index(name: str) -> int:
    try:
        return _CLASS_ORDER.index(name)
    except ValueError:
        # Unknown class → most privileged (fail-closed).
        return len(_CLASS_ORDER) - 1


def _normalize(path: str) -> PurePosixPath:
    return PurePosixPath(path.replace("\\", "/").strip("/") or ".")


def _path_class(path: str) -> str:
    """Return the mutation class for a single changed path.

    Predicates are evaluated in priority order: the FIRST matching predicate
    wins for this path.  The caller takes the maximum across all paths.
    """
    p = _normalize(path)
    parts = tuple(p.parts)
    name = p.name.lower()
    suffix = p.suffix.lower()

    # ── SECURITY / ATTESTATION / REDACTION ─────────────────────────────────
    # Wall, broker, egress-gating, cred-injection, redaction: most privileged.
    # These must be checked before the broader ``forge/`` code predicate.
    _security_file_stems = frozenset({
        "approval_capability",
        "cred_injection_proxy",
        "secret_identity",
        "_redact",
        "redact",
    })
    _security_dir_parts = frozenset({
        "egress-broker",
        "egress_broker",
        "openbao",
        "openbao-config",
    })

    # cred_injection_proxy, approval_capability, _redact, secret_identity
    stem = p.stem.lower()
    if stem in _security_file_stems:
        # attestation for approval_capability (the wall itself)
        if stem == "approval_capability":
            return "attestation"
        # redaction classifier
        if stem in {"_redact", "redact"}:
            return "redaction"
        # secret_identity → identity
        if stem == "secret_identity":
            return "identity"
        return "security"

    # egress broker (tools/egress-broker/**) → security
    if any(part in _security_dir_parts for part in parts):
        return "security"

    # ── IDENTITY ────────────────────────────────────────────────────────────
    _identity_stems = frozenset({
        "identity_registry",
        "reviewer_registry",
        "identity-registry",
        "reviewer-registry",
    })
    _identity_file_names = frozenset({
        "identity-registry.schema.yaml",
        "reviewer-registry.schema.yaml",
    })
    if stem in _identity_stems or name in _identity_file_names:
        return "identity"
    # schemas/identity-registry.schema.yaml and similar
    if parts and parts[0] == "schemas" and "identity" in name:
        return "identity"
    # account config / app-key artefacts
    if parts and parts[0] in {"accounts", "account-config", "identity"}:
        return "identity"

    # ── GOVERNANCE ──────────────────────────────────────────────────────────
    _governance_dirs = frozenset({
        "playbooks",
        "governance",
    })
    _governance_contract_dirs = frozenset({
        "contracts",
    })
    if parts and parts[0] in _governance_dirs:
        return "governance"
    # .ce/contracts/**, docs/contracts/**
    if len(parts) >= 2 and parts[1] in _governance_contract_dirs:
        return "governance"
    if parts and parts[0] in _governance_contract_dirs:
        return "governance"
    # GOVERNANCE.md root file
    if len(parts) == 1 and name in {"governance.md", "security.md", "code_of_conduct.md"}:
        return "governance"

    # ── DEPLOY ──────────────────────────────────────────────────────────────
    # .github/workflows/**, Dockerfiles, deploy/**, systemd units, install scripts
    _deploy_dirs = frozenset({"deploy", ".github"})
    _deploy_file_names = frozenset({
        "dockerfile",
        "containerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    })
    if parts and parts[0] in _deploy_dirs:
        return "deploy"
    if name in _deploy_file_names or name.startswith("dockerfile."):
        return "deploy"
    # systemd service files, install scripts
    if suffix in {".service", ".timer", ".socket"} or name in {"install.sh", "install-ce.sh"}:
        return "deploy"

    # ── SCHEMA ──────────────────────────────────────────────────────────────
    # schemas/**, surfaces/manifest.yaml, *.schema.yaml, mutation-class-taxonomy
    _schema_dirs = frozenset({"schemas"})
    if parts and parts[0] in _schema_dirs:
        return "schema"
    if name == "manifest.yaml" and len(parts) >= 2 and parts[-2] == "surfaces":
        return "schema"
    if name.endswith(".schema.yaml") or name.endswith(".schema.json"):
        return "schema"
    # surfaces/manifest.yaml specifically
    if len(parts) >= 2 and parts[0] == "surfaces" and name == "manifest.yaml":
        return "schema"

    # ── DOCS ────────────────────────────────────────────────────────────────
    # docs/**, *.md (excluding privileged markdown already caught above),
    # .ce/changelog/**, .ce/pr-manifests/**
    _docs_dirs = frozenset({"docs"})
    _docs_ce_subdirs = frozenset({"changelog", "pr-manifests"})
    if parts and parts[0] in _docs_dirs:
        # docs/contracts/** is already caught above as governance
        if len(parts) >= 2 and parts[1] in _governance_contract_dirs:
            return "governance"
        return "docs"
    if suffix == ".md":
        return "docs"
    # .ce/changelog/**, .ce/pr-manifests/**
    if len(parts) >= 2 and parts[0] == ".ce" and parts[1] in _docs_ce_subdirs:
        return "docs"
    # CHANGELOG.md, README.md, CONTRIBUTING.md, etc. at root (already caught by .md suffix)

    # ── CODE ────────────────────────────────────────────────────────────────
    # Everything else: validators/**, tools/**, app source — conservative middle.
    return "code"


def mutation_class_for_paths(changed_paths: list[str]) -> str:
    """Return the highest-risk mutation class across ``changed_paths``.

    Fail-closed contract:
    - Empty list → ``"docs"`` (lowest non-none; no paths means PR is likely
      docs-only or trivially safe, but we still need a class).
    - Path matching no predicate → ``"code"`` (conservative).
    - Unknown class returned by a predicate → ``"redaction"`` (highest; internal
      safeguard against predicate bugs).

    Never returns ``"none"`` for a non-empty path list because even a PR that
    only touches files we haven't classified deserves ``"code"`` at minimum.
    """
    if not changed_paths:
        return "docs"

    highest_idx = _CLASS_DOCS_IDX  # start at docs, escalate upward
    for path in changed_paths:
        cls = _path_class(str(path))
        idx = _class_index(cls)
        if idx > highest_idx:
            highest_idx = idx
        # Short-circuit: already at maximum privileged class
        if highest_idx == len(_CLASS_ORDER) - 1:
            break

    return _CLASS_ORDER[highest_idx]


# Convenience set: classes that map to AUTO ratification gates per _RISK_TABLE.
AUTO_CLASSES: Final[frozenset[str]] = frozenset({"none", "docs"})

# Classes that always require operator_merge (never auto-mergeable).
GESTURE_CLASSES: Final[frozenset[str]] = frozenset(
    {"code", "schema", "deploy", "governance", "identity", "security", "attestation", "redaction"}
)

# Privileged classes that carry ring1_push_block / non_delegable.
PRIVILEGED_CLASSES: Final[frozenset[str]] = frozenset(
    {"governance", "identity", "security", "attestation", "redaction"}
)
