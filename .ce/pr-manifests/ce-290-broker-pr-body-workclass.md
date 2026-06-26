# PR path manifest - ce-290-broker-pr-body-workclass - ce-ops#290 broker PR body declared work class

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-290-broker-pr-body-workclass

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#290 requires the egress broker PR body renderer to inject the declared
work class from `.ce/changelog/<branch-slug>.md` YAML front matter so
broker-created PRs satisfy the G5 declared-work-class gate.

The changes:
- Read `work_class` from the branch changelog front matter when rendering the
  broker PR body.
- Include `- **Declared work class:** <work_class>` in the generated body when
  the changelog field is present.
- Add focused unit coverage for present and unusable changelog metadata.
- Add this changelog and path manifest carrier.

Per-file purpose:
- **`.ce/changelog/ce-290-broker-pr-body-workclass.md`** *(A)* - changelog fragment with `work_class: tiny`.
- **`.ce/pr-manifests/ce-290-broker-pr-body-workclass.md`** *(A)* - this carrier.
- **`tools/egress-broker/egress_broker/orchestrator.py`** *(M)* - render declared work class from changelog front matter into broker PR bodies.
- **`validators/tests/unit/test_egress_orchestrator.py`** *(M)* - focused PR-body unit coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b8f0c317f33386a8b6ac2dac5e37bfc97e9efe8cfdee8da9eb757d517700ec1e

```text
.ce/changelog/ce-290-broker-pr-body-workclass.md
.ce/pr-manifests/ce-290-broker-pr-body-workclass.md
tools/egress-broker/egress_broker/orchestrator.py
validators/tests/unit/test_egress_orchestrator.py
```
