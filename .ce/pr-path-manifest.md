# PR path manifest — feat(v3): G-7.5 pilot runbook + in-product `ce guide` + roadmap flip → v3.1 pilot-ready

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **G-7 slice 7F — the pilot runbook + in-product help + the roadmap flip**
(the SIXTH and FINAL ratified G-7 slice — it reaches **v3.1 pilot-ready**):

- **Pilot runbook** (`docs/guide/pilot-runbook.md`, NEW) — the operator path:
  install (two operator-typeless modes) → provision repo+App → file work as a
  Scope (Frame→Shape→Build→Review→Ship) → ratify → drive → ◆ Completion Report →
  review → merge, in the canon vocabulary, using `ce`. Includes the greenfield-OSS
  quickstart + the cost-safety note. Names the deferred first-pilot live seams.
- **In-product help** — `ce guide` surfaces the seed of
  `docs/guide/understanding-ce.md` (content reused, not re-authored) via a new
  `guide` subcommand on the v3 CLI. Speaks `ce` (the user-facing name).
- **Roadmap flip** (`docs/v3-roadmap.md`) — G-7 row → **DONE** (the 6 slices
  #164/#166/#167/#168/#169/#170); the gate map + the milestone lines flipped to
  **v3.1 pilot-ready ✓ REACHED**. **Carry-forward:** the G-6 row SHA `pending` →
  **`dee9c9b`** (the #162 merge SHA).

NO new module, NO new check, NO schema change — `V3_RUNTIME` stays **26**, the
check surface stays **47**, `test_version_boundary` count-pins unchanged. The
`guide` command is content added to the already-v3 `v3_cli`.

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**);
**G-4.1 naming hygiene** (`v3_naming_hygiene` GREEN 0/0 — docs excluded; no v3-code
residue; `ce guide` text speaks `ce`, no `cev3`); **vocabulary fidelity** (the
runbook + guide use the ratified canon — stage phases / Scope-card / Completion-
Report — no third vocabulary). `check-examples` stays **78/0** (docs + CLI help
text; no example fixtures). The G-7 row SHA stays `pending` (filled post-merge by
the next PR, per the established deferred-SHA pattern — this is the closing slice).

- **base:** `6889b207aa3923a50a866c6447f064cbf8f6f651`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=ee99cbb4dc64c6090ee598d3b7f8e1b4377a7f1530186b198a45366315b6aa1c

```text
.ce/pr-path-manifest.md
docs/guide/pilot-runbook.md
docs/v3-roadmap.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_v3_cli.py
```
