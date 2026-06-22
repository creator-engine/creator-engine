# PR path manifest - ce104-review-gate-design

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce104-review-gate-design
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
creator-engine/creator-engine#104 architect/design-gate output for Review Gate reviewer-venue
semantics. This is a docs-only plan that reconciles the named Review Gate,
review evidence, reviewer identity, controller boundary, lane launch,
transcript archive, and completion-report sources. Explicitly excluded:
runtime code, schema changes, validators, CI wiring, launcher changes, GitHub
behavior, branch protection, merge behavior, and reviewer-authority minting.

Per-file purpose (closed path-set - 3 paths):

- **`.ce/changelog/ce104-review-gate-design.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce104-review-gate-design.md`** *(A)* - this PR's closed path-set carrier.
- **`docs/operations/REVIEW_GATE_REVIEWER_VENUE_DESIGN.md`** *(A)* - bounded design plan for future Review Gate reviewer-venue enforcement.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=5a1b3252ce6f3618cbdeae59ffa2d46e63a1879d8f6585784f05e2f4ebcf7e7d

```text
.ce/changelog/ce104-review-gate-design.md
.ce/pr-manifests/ce104-review-gate-design.md
docs/operations/REVIEW_GATE_REVIEWER_VENUE_DESIGN.md
```
