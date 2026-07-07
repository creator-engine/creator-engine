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
- Schema reference: `python scripts/gen_schema_reference.py --write`; `python scripts/gen_schema_reference.py --check` -> current.
- Path manifest: `PYTHONPATH=validators python3 -m creator_engine_validator verify-path-manifest --base bd5b1f837f8030fd030c4e72883c4aeb6728c625 --manifest-dir .ce/pr-manifests --head-ref ce-488-memory-layer-slice1 --require-carrier` -> PASS `path_manifest_fidelity`.
- Full local preflight: `PYTHONPATH=validators PYTEST_ADDOPTS="-n 2" python3 -m creator_engine_validator.ce_cli validate-pr --repo-root .` was attempted. It prepared baseline/head worktrees and ran pytest phases, but the host environment failed unrelated baseline and head tests under Python 3.11.2 while the repo contract requires Python >=3.14; tmux, rootless Podman, uv, and installed CE posture were also unavailable. After both pytest phases, the process hung in the aggregate examples gate and was interrupted. ENV-SKIP applied to the full preflight; focused remediation modules plus schema and carrier checks are recorded above.
