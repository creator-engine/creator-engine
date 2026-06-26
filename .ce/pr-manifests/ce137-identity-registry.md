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
ce-ops#137 GitHub identity and infrastructure registry. Public artifact =
schema + redacted example only (creator-engine is a public repo). The
authoritative registry with real values is maintained internally (see
follow-on internal registry ticket). Raw token values, PEM values,
validator business logic, tools, deploy code, brain subsystem files, agent
configuration, and `AGENTS.md` are out of scope.

Per-file purpose (closed path-set - 6 paths):
- **`.ce/brain/assertions.yaml`** *(M)* - brain ledger re-sealed to match current validate.yml sha256 (bug-fix; chain hashes re-derived).
- **`.ce/changelog/ce137-identity-registry.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce137-identity-registry.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - existing Validate workflow gains
  an identity-registry schema validation step (validates example file).
- **`docs/governance/identity-registry.example.yaml`** *(A)* - schema-conformance
  sample with generic placeholders only; no real fleet identities.
- **`schemas/identity-registry.schema.yaml`** *(A)* - registry validation schema.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=8f899bf57a0105e29dd33abaa76f534a85df0bcbc6041bdfc24a508b24f25341

```text
.ce/brain/assertions.yaml
.ce/changelog/ce137-identity-registry.md
.ce/pr-manifests/ce137-identity-registry.md
.github/workflows/validate.yml
docs/governance/identity-registry.example.yaml
schemas/identity-registry.schema.yaml
```
