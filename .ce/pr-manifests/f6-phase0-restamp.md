# PR path manifest — ce-ops#39 · F6 Phase-0 two-tier change-block re-stamp

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref f6-phase0-restamp
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED F6 merge-concurrency design
(`~/Documents/ce-f6-merge-concurrency-design-DRAFT-20260612.md`, ratified as written
2026-06-12 on the ce-ops#39 thread, sha256
`f3c3f8a51b77b6442f35ed933c8f5681154b456ca0a16beb5daa686200d8f3cd`); ratified Scope
`f6-phase0-restamp` (`ratified_scope_sha c158037b…`, `approver_ref f3c3f8a5…`). The
combined-source wheel rebuild + `SHA256SUMS` re-pin is the declared mechanical co-move on
ce-ops#39 (the F6 source modules are wheel-shipped; the packaging contract byte-checks the
bundled `.py` against source).

Manifest = the design's closed 15-path manifest PLUS the wheel pair
(`validators/wheelhouse/{SHA256SUMS, creator_engine_validator-0.1.0-py3-none-any.whl}`,
the declared mechanical widening for wheel-shipped source moves) = **17 paths**, in per-PR
carrier form. NO override flag anywhere; NO GitHub workflow edits; merge stays head-pinned.
`_versions.py` / `docs/v3-roadmap.md` / `test_version_boundary.py` are deliberately ABSENT:
F6 adds NO new module (V3_RUNTIME frozenset unchanged at 36, registry unchanged at 53) — the
"+1 runtime capability" lands in existing v3 modules and "+2 record types" land in the
already-listed `runtime-evidence.schema.yaml`.

Per-file purpose (the closed path-set — 17 paths):
- **`.ce/pr-manifests/f6-phase0-restamp.md`** *(A)* — this carrier (self-inclusive).
- **`docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`** *(M)* — §g records the
  Phase-0 two-tier re-stamp semantics + the recorded Phase-1 merge-queue trigger.
- **`schemas/dispatch-record.schema.yaml`** *(M)* — optional re-stamp anchor fields on the
  `change` block (`base_sha` + change identity); `schema_version` stays `"1"` (additive).
- **`schemas/runtime-evidence.schema.yaml`** *(M)* — +2 record types
  (`runtime_change_restamp`, `runtime_merge_audit`) + optional `change_set.base_sha`.
- **`validators/creator_engine_validator/checks/path_manifest_fidelity.py`** *(M)* —
  structured carrier parser (`parse_carrier`/`parse_carrier_file`/`CarrierIdentity`) under
  the existing check; no new registered check.
- **`validators/creator_engine_validator/forge/change_status.py`** *(M)* — the combined
  `pr_state` read (`PullRequestState`): live head/base SHAs + branch/base + gate, one read.
- **`validators/creator_engine_validator/forge/merge.py`** *(M)* — F6 head-pin authority
  doc (no override; the `sha` is the latest attested/re-stamped head + match-head guard).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `cev3 merge` surfaces
  `head_status` + re-stamp + the merge-audit alarm; `cev3 collect` propagates `base_sha`.
- **`validators/creator_engine_validator/v3_forge_join.py`** *(M)* — the two-tier re-stamp
  algorithm (`merge_for_run`): identity proof, `runtime_change_restamp`, `pr_merged`,
  `runtime_merge_audit`; open stamps the re-stamp anchor when a git identity seam is wired.
- **`validators/tests/unit/test_ce_runtime_evidence.py`** *(M)* — new record-type schema +
  hash-chain tests.
- **`validators/tests/unit/test_change_status.py`** *(M)* — combined `pr_state` reads +
  malformed-response refusals.
- **`validators/tests/unit/test_merge.py`** *(M)* — head-pin preservation, no override, race.
- **`validators/tests/unit/test_path_manifest_fidelity.py`** *(M)* — carrier normalization
  + path-set hash stability tests.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — plan/apply output + audit-alarm tests.
- **`validators/tests/unit/test_v3_forge_join.py`** *(M)* — restamp/merge/evidence/refusal/
  no-token + audit tests (the design test plan).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — the
  wheel rebuilt from this branch's source (F6 source modules are wheel-shipped).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=870b7b46c2201d8a4971624b2da8db5caec9c2c01a6d0249da474f102ce40b22

```text
.ce/pr-manifests/f6-phase0-restamp.md
docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md
schemas/dispatch-record.schema.yaml
schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/creator_engine_validator/forge/change_status.py
validators/creator_engine_validator/forge/merge.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_forge_join.py
validators/tests/unit/test_ce_runtime_evidence.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_path_manifest_fidelity.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_forge_join.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
