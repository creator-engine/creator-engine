---
slug: ce-488-memory-layer-slice1
date: 2026-07-07
work_class: story
branch: ce-488-memory-layer-slice1
brief_sha256: 2b5fdb74778afad79addff057878a29573f582371b15ea84db000f7c097b5e79
---

# PR #888 Remediation Evidence

## Findings

- F1: Replaced hydration `newest_resume_state.mtime` with deterministic `content_sha256`; takeover receives the renamed field through the existing hydration passthrough.
- F2: Added required decision `authority` and lesson `source` provenance fields to ledger records and append-intent validation; regenerated schema reference.
- F3: Added a byte-identical `hydrate_contract` test that serializes two calls over the same populated state root with a seeded resume file.
- F4: Privatized memory append helpers as `_append_decision` and `_append_lesson`; the mediated append worker is the only production consumer retained.
- F5: Added corrupt-ledger takeover coverage for a syntactically valid but hash-chain-invalid brain ledger; `ce takeover --dry-run --json` exits 2 with a JSON error packet.
- F7: Added an inline comment documenting hydration's empty-records lenience.
- F8: Unified the brain hydration contract `schema_version` to string `"1"` to match ledger records.
- F10: Not taken; no new docs path was needed for the required remediation.

## Verification

- Focused remediation tests: `PYTEST_ADDOPTS="-n 2" pytest validators/tests/unit/test_brain_runtime.py validators/tests/unit/test_brain_append_worker.py validators/tests/unit/test_ce_takeover_cli.py` -> 37 passed.
- Schema reference: `python scripts/gen_schema_reference.py --write`.
- Full local preflight: pending before final harvest commit.
