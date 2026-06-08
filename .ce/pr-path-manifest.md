# PR path manifest — feat(v3.5-D.0.1): live usage-tap — transcript → spend-ledger (pure, green-now)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **v3.5-D.0.1 — the live usage-tap** (the first slice of the
compute-demand-artifact cluster / the NVIDIA-partnership arc). It lands the live
`usage` tap that `runner/spend_gate.py`'s docstring names as a deferred seam:
it captures per-turn token usage from a harness JSONL transcript and turns each
assistant turn into `runtime_spend_ledger` record bodies **by reusing the existing
pure spend substrate** (`spend_gate.compute_cost` + `meter_record_body`) — cost is
never reimplemented, and an unpriced model is routed to `unpriced_turns`, never a
silent $0 (honoring `spend_gate.UnknownModelRate`).

- **`runner/usage_tap.py`** (NEW) — `@dataclass(frozen=True) UsageTurn`; the pure
  `parse_transcript_usage` (tolerant + idempotent; skips malformed / non-assistant /
  no-usage / `isSidechain` / no-model); the pure `usage_turns_to_ledger(...) ->
  (ledger_bodies, unpriced_turns)`; and the single I/O edge `tap_transcript_file`.
  No `@register` (library module, not a check); imported directly (mirrors
  `spend_gate`, no `__init__` export).
- **`_versions.py`** — adds the `runner.usage_tap` v3 runtime-surface baseline entry
  (keeps `version_boundary` green; no `VAL-VERBND-SHARED-EDGE`).
- **`test_usage_tap.py`** (NEW) — fixtures in the confirmed harness shape; asserts
  extraction, the reused `compute_cost`, the ledger-body fields, and
  unpriced→`unpriced_turns`.
- **`test_version_boundary.py`** — the mandatory paired count-bump for the new
  baseline entry: as the SECOND v3.5 merge (atop #172's `runner.openshell_backend`
  already in main at 27), `V3_RUNTIME` **27 → 28**.

NO schema change, NO new check — the check surface stays **47** and `--list-checks`
is byte-identical. `V3_RUNTIME` becomes **28** (its paired count-test pins 28).

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**);
**G-4.1 naming hygiene** (`v3_naming_hygiene` GREEN — the new v3 surface is clean);
**pure core** (`parse_transcript_usage` + `usage_turns_to_ledger` do no I/O; only
`tap_transcript_file` reads; stdlib `json` only, no new deps). `pytest validators/`
is green (the only non-pass is the pre-existing local-umask
`test_hook_scripts_are_executable_posix_sh`, identical on `main`, green in CI).

This PR is the **SECOND (last) merge** of the concurrent {usage-tap, A.1 openshell}
pair — #172 merged first (advancing main to `280e9273`); the site-only PR #173 then
landed (main → `75b7b571`) and rewrote the shared carrier but left `validators/`
byte-identical, so this branch is rebased onto `75b7b571` with no code change. The
authorized path-set and its SHA256 are unchanged from the first-merge carrier (they
are over the path-set, not the base); only the `base:` line moves.

- **base:** `75b7b571d445bd2e4a78ce2c25f61589535bda55`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=0189ac8a8e14564474c74c082e16d2629dcf317c6e95d70b6263f9b84ab812df

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/runner/usage_tap.py
validators/tests/unit/test_usage_tap.py
validators/tests/unit/test_version_boundary.py
```
