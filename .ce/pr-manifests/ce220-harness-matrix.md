# PR path manifest - ce220-harness-matrix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce220-harness-matrix

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified scope:
Implement ce-ops#220: the PROBED harness-support capability matrix — a
code-synced single source of truth for which agent harnesses CE governs and to
what extent. Pairs with the containment-probe incident (ce-ops#221): governance
state must be DERIVED/probed, never hand-asserted. Adds the `ce harness-matrix`
CLI surface that emits a HARNESS x CAPABILITY matrix (Markdown + JSON) derived
from the live adapter specs and committed config, with a provenance note per
cell and an explicit flag for any asserted-but-unverifiable capability. No forge
write, push, or merge from the authoring lane.

The changes:
- Add `harness_matrix.py`: the probe runtime that derives each cell from the
  live specs (`claude_launch_spec`, `codex_launch_spec`, `lane_runtime`,
  `hook_pack_confirm`) and the committed config (`.claude/settings.json`,
  `.codex/requirements.toml`), plus Markdown/JSON renderers.
- Wire `ce harness-matrix` into the `ce` CLI (`ce_cli.py`) with `--repo-root`
  and `--json`.
- Add unit coverage asserting the derived-not-hardcoded invariants (claude
  Ring-1 = present only with a backing PreToolUse pack; codex Ring-1 =
  managed-non-bypassable only with the committed `allow_managed_hooks_only` pin;
  never present without a backing file; containment is deferred/unverified while
  the herdr live launch is the fail-closed U2 stub).
- Add a changelog fragment and this path-manifest carrier.

Per-file purpose (the closed path-set - 5 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce220-harness-matrix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce220-harness-matrix.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wire the
  `ce harness-matrix` subcommand + handler.
- **`validators/creator_engine_validator/harness_matrix.py`** *(A)* - the
  probed matrix runtime + renderers.
- **`validators/tests/unit/test_harness_matrix.py`** *(A)* - derived-not-hardcoded
  unit coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=8c5611859d69b6bc1f17f5052bde182cd3a4b08c1e4535581d94e0745c89c594

```text
.ce/changelog/ce220-harness-matrix.md
.ce/pr-manifests/ce220-harness-matrix.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/harness_matrix.py
validators/tests/unit/test_harness_matrix.py
```
