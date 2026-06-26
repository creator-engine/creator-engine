# PR path manifest - ce-ops#91 - controller ops SSOT

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce91-controller-ops-ssot
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself; `branch_slug("ce91-controller-ops-ssot") == "ce91-controller-ops-ssot"`).

Purpose:
- Add `docs/operations/CE_CLI_REFERENCE.md`, generated from available help surfaces and parser-backed help definitions.
- Add `docs/operations/CE_CONTROLLER_PLAYBOOK.md`, the Controller task playbook for reviewer venues, lane lifecycle, PR validation, and carriers.
- Add `docs/operations/CE_ORIENTATION_MAP.md`, the subsystem/state/invariant map for agent-native operation.
- Carry the required changelog fragment.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=737b4011fc95eecc361ee4cb762a67e33de3008f6cdd2fe041512a725d00ce3c

```text
.ce/changelog/ce91-controller-ops-ssot.md
.ce/pr-manifests/ce91-controller-ops-ssot.md
docs/operations/CE_CLI_REFERENCE.md
docs/operations/CE_CONTROLLER_PLAYBOOK.md
docs/operations/CE_ORIENTATION_MAP.md
```
