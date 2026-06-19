# PR path manifest — ce-ops#93 · CE v3.5 program plan (docs)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref v35-roadmap-plan
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

The change (docs-only): adds `docs/v3.5-roadmap.md` (the forward program plan that clusters
the open backlog into 7 workstreams → waves → the NVIDIA pitch), and adds a forward-pointer
header to the now-historical `docs/v3-roadmap.md`. No code or behaviour change.

Per-file purpose (closed path-set — 4 paths):
- **`.ce/changelog/v35-roadmap-plan.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/v35-roadmap-plan.md`** *(A)* — this carrier (self-inclusive).
- **`docs/v3-roadmap.md`** *(M)* — forward-pointer header to the v3.5 plan.
- **`docs/v3.5-roadmap.md`** *(A)* — the v3.5 program plan.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4ebfb3c49b1f8583ea42cad96ef8fbf8813434e2723835ec790de322e92ce453

```text
.ce/changelog/v35-roadmap-plan.md
.ce/pr-manifests/v35-roadmap-plan.md
docs/v3-roadmap.md
docs/v3.5-roadmap.md
```
