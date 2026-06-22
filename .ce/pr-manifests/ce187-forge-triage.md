# PR path manifest - ce187-forge-triage

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce187-forge-triage
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`73bff5a` (`origin/main` at branch creation).

Scope:
ce-ops#187 first bounded forge-triage slice: an offline-first planner that
stocks the existing pickup belt with deterministic, sized, claimable issues
using pickup labels and optional assignees. The slice explicitly excludes
auto-launch, datastore, roadmap prose generation, and merge authority.

Per-file purpose:
- **`.ce/changelog/ce187-forge-triage.md`** *(A)* - changelog fragment for ce-ops#187.
- **`.ce/pr-manifests/ce187-forge-triage.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wires `ce pickup triage` dry-run/apply CLI.
- **`validators/creator_engine_validator/forge_triage.py`** *(A)* - planner, readiness gates, collision checks, and label/assignee apply seam.
- **`validators/tests/unit/test_forge_triage.py`** *(A)* - offline tests for deterministic output, gates, collision, sizing, and CLI JSON.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=7a4125ad625d5d91cce568bce4ebc57ccfac17d89bb4752b7ce1d37afa53f3f4

```text
.ce/changelog/ce187-forge-triage.md
.ce/pr-manifests/ce187-forge-triage.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_forge_triage.py
```
