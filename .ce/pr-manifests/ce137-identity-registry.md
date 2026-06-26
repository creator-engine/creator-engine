---
slug: ce137-identity-registry
date: 2026-06-26
kind: governance-manifest
scope: identity registry SSOT
issue: ce-ops#137
---

# PR path manifest - ce137-identity-registry

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce137-identity-registry --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#137 GitHub identity and infrastructure registry. This adds a non-secret
machine-readable SSOT, its schema, CI validation in the existing Validate
workflow, and the required governance carriers. Raw token values, PEM values,
validator business logic, tools, deploy code, brain subsystem files, agent
configuration, and `AGENTS.md` are out of scope.

Per-file purpose (closed path-set - 6 paths):
- **`.ce/brain/assertions.yaml`** *(M)* - brain ledger re-sealed to match current validate.yml sha256 (bug-fix; chain hashes re-derived).
- **`.ce/changelog/ce137-identity-registry.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce137-identity-registry.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - existing Validate workflow gains
  an identity-registry schema validation step.
- **`docs/governance/identity-registry.yaml`** *(A)* - non-secret identity and
  infrastructure registry.
- **`schemas/identity-registry.schema.yaml`** *(A)* - registry validation schema.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=f220a7462d8ad0b442778972707e6caec0943698e695fb7d58cd053693a00531

```text
.ce/brain/assertions.yaml
.ce/changelog/ce137-identity-registry.md
.ce/pr-manifests/ce137-identity-registry.md
.github/workflows/validate.yml
docs/governance/identity-registry.yaml
schemas/identity-registry.schema.yaml
```
