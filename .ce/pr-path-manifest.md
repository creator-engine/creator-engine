# PR path manifest — v3 G-3.7b.1 merge-driving seam + distinct merge-identity seam + `pr_merged` producer (CI-pure)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the PRODUCER half of the gated-merge substrate (G-3.7b.1), mirroring the
3.7.2a(model)→3.7.2b(producer) cadence. Three things, **entirely offline,
RED→GREEN against fakes**: (1) a **forge-free merge-driving seam** —
`orchestrator.merge_change(...)`, a NEW entry distinct from the agent-run
`run_plan` (a merge acts on an ALREADY-OPEN, reviewed PR) — that drives an
injected forge-free `change_merger` (the production closure wraps `forge.merge()`
/ G-3.3) and, on an ACTUAL merge, attests a typed `pr_merged` `runtime_run_outcome`
record onto the SAME hash chain; (2) a **distinct merge-identity seam** —
`run_assembly.make_merge_driver(...)` whose merge credential is the injected
`merge_gh_runner` and is **NEVER the per-run scoped token** (it mints no per-run
token and never reaches for `authenticated_gh_runner`; no self-merge collision —
the per-run token authored the PR); (3) the **`pr_merged` PRODUCER** wiring. The
`pr_merged` MODEL already landed on `main` (G-3.7b.0), so this slice touches the
spine/schema/contract/example **not at all** (byte-unchanged). `pr_merged` is
attested only on an ACTUAL merge (`result.merged`) — a non-mutating plan-mode
`would_merge` preview or a gate-ineligible/refused merge attests NOTHING. The
merge record reuses the value-free `change_set` pointer shape (branch / base /
manifest_paths / head_sha / pr_number); `merge_commit_sha` has no v1-schema slot
and stays on the returned `MergeResult` (no `schema_version` bump). CI-pure: every
path driven by fakes; `subprocess`/`socket`/`Path.write_text` explode; NO live
`gh`/network/real `apply=True`/merge (→ the out-of-envelope **G-3.8**). It adds no
check/backend/CLI/wheel/dependency → `--list-checks` STAYS **43**,
`available_backends()` is unchanged, and `check-examples` STAYS **77/0**. Design
source: the in-repo `docs/architecture/pilot-roadmap.md` §"G-3.7b / G-3.8" +
`docs/architecture/pilot-deployment-transport.md` (the agent author ≠
reviewer/merger identity invariant).

- **base:** `894bc429179122b9493f1028456ab6bd5b503a3f`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=2124d90c0461850246d4990ec3fa39cfa2edb12416bd5f685df5ae5832982022

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/run_assembly.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_run_assembly.py
```
