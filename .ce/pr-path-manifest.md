# PR path manifest — feat(gate-b): scope governed posture to the live ledger (injection-first)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **Gate B — scope the governed posture-reachability decision to the live
ledger (injection-first), preserving the posture-gated push hard-deny.**

- `.claude/hooks/ce-hook-common.sh`, `.claude/hooks/ce-pretooluse.sh`: the hook
  pack's posture wiring.
- `docs/operations/CLAUDE_CODE_HOOK_PACK.md`: the hook-pack doc kept in sync.
- `validators/creator_engine_validator/cli.py`,
  `validators/creator_engine_validator/hook_check.py`,
  `validators/creator_engine_validator/lane_runtime.py`: the posture-reachability
  decision and its injection-first ledger source.
- `validators/tests/integration/test_hook_check_cli.py`,
  `validators/tests/unit/test_ce_lane_cli.py`,
  `validators/tests/unit/test_hook_check.py`: coverage for the scoped posture.

**Version-boundary impact = ZERO.** No new `runner.*` module, no schema change,
no check registration, no `runner/__init__.py` export; `V3_RUNTIME` stays **28**
and `--list-checks` stays byte-identical.

- **base:** `97dbc28e8c72717759d572ec4b022e854331048a` (current `main`). NOTE:
  this PR overlaps `cli.py`/`hook_check.py` with Gate C (#182); Gate C merges
  first, then this branch rebases. After the rebase, re-pin this `base:` to the
  post-#182 `main` SHA and regenerate the path-set if it shifts.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=47cc43755a6476865a23f341ca009c6e6a923b82f81a32bb18b80cb0070479e5

```text
.ce/pr-path-manifest.md
.claude/hooks/ce-hook-common.sh
.claude/hooks/ce-pretooluse.sh
docs/operations/CLAUDE_CODE_HOOK_PACK.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/lane_runtime.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_hook_check.py
```
