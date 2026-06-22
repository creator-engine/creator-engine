# PR path manifest - ce185-devops-broker-adr

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce185-devops-broker-adr
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#185 design/schema artifacts for the DevOps privileged-action broker.
The change defines the proposed ADR, prose contract, value-free envelope schema,
and changelog only. It deliberately performs no runtime implementation, live
OpenBao configuration, root action, forge mutation, deploy, or merge.

Base:
`627b42174d8c0dbfd89dbac6c4783b6aeb2365d7` (`origin/main` at branch creation,
post PR #312).

Per-file purpose (closed path-set - 5 paths):

- **`.ce/changelog/ce185-devops-privileged-action-broker.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce185-devops-broker-adr.md`** *(A)* - this PR's closed path-set carrier.
- **`docs/contracts/devops-privileged-action-broker.md`** *(A)* - broker architecture, envelope contract, threat model, OpenBao capability basis, and ce-ops#184 pilot.
- **`docs/decisions/ADR-0011-devops-privileged-action-broker.md`** *(A)* - proposed decision record for the privileged-action broker.
- **`schemas/devops-privileged-action-broker.schema.yaml`** *(A)* - JSON Schema draft 2020-12 envelope schema.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=9987fb9b4acf73e29abfe4db5f96401b101d43ef9084b313c1c04dde699a602f

```text
.ce/changelog/ce185-devops-privileged-action-broker.md
.ce/pr-manifests/ce185-devops-broker-adr.md
docs/contracts/devops-privileged-action-broker.md
docs/decisions/ADR-0011-devops-privileged-action-broker.md
schemas/devops-privileged-action-broker.schema.yaml
```
