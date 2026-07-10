# DISPATCH — dev-4 BATCH — 2026-07-10 — materializer pre-arming slices (d)+(a)+(b) — Operator-ratified
Role: implementer foreman. THREE units, SEQUENCED: Unit D FIRST (its decisions bind A), then
A and B may run concurrently (disjoint files). One signal per unit:
`READY-FOR-HARVEST <branch> <full-40-hex-sha>` / `BLOCKED <branch> <one-line-reason>`
Base: freshly fetched origin/main OR LATER (merge queue is active — use whatever you fetch;
re-block only on rewind). Worktrees /var/tmp/wt-<branch>. Focused tests only; commit per unit.
PRE-SIGNAL CHECKLIST every unit: focused module tests green + the confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`
Product lens everywhere: ZERO internal ticket refs in prose.

## Shared context (embedded)
The Option A merge-intent materializer shipped disarmed: 9 unit-test files prove the dry-run
loop; `construct_materialization_commit()` is a guarded stub; no deploy unit exists; the
redeploy script hard-refuses it. Operator ratified four pre-arming slices 2026-07-10 (evidence
page: .ce/state/research/MATERIALIZER_ARMING_EVIDENCE_20260710.md — READ IT plus the design
doc docs/design/ce-491-optiona-merge-intent.md before Unit D). ARMING_ENABLED stays False in
every unit — nothing in this batch arms anything.

## UNIT D — branch `ce-materializer-adr-arming` — class S — DO FIRST
Short ADR `docs/decisions/0006-materializer-arming-credential-lease.md` (follow the numbering/
format of existing docs/decisions/*) resolving the design doc's three open questions:
Q1 arming authority (recommend: governed PR flipping the constant + Operator co-sign artifact
per the ratified release-signing model — decide and justify); Q2 credential form for the App
private key (recommend: OpenBao-backed short-TTL issuance, never on worker disk — decide);
Q4 lease topology (local file lease vs external linearizable lock — the design flags the local
lease as insufficient under multi-instance; decide for the CURRENT single-host topology with
an explicit revisit trigger). Each: decision, rationale, rejected alternative, revisit trigger.
Files: the ADR + changelog + carrier (slug=branch). `- **Declared work class:** S`

## UNIT A — branch `ce-materializer-cas-push` — class M — after D commits
Implement the commit-build + compare-and-swap push path in
`validators/creator_engine_validator/brain_intent_materializer.py`:
- Build the materialization commit deterministically from the built records (append to
  assertions.yaml + remove consumed intent, one commit, message format per design doc).
- CAS semantics: push only if remote main parent == the scanned parent; on CAS failure,
  re-enter the scan loop (no retry-push of a stale build).
- The PUSH itself stays behind `assert_arming_enabled()`; commit CONSTRUCTION must be
  testable disarmed (construct-and-inspect without push). Honor Unit D's Q4 decision on
  lease semantics; keep HELD/closeout behavior byte-stable.
- Tests: construction determinism (same inputs → same tree/commit), CAS-failure re-scan path
  (mocked remote), disarmed-push refusal preserved, existing 52 tests untouched-green.
Files: the module + its test files (extend; new test module allowed) + changelog + carrier
(slug=branch). `- **Declared work class:** M`

## UNIT B — branch `ce-materializer-deploy-unit` — class S — may run parallel to A
Give the materializer the queue-daemon's IaC shape:
- `deploy/materializer/ce-materializer.service` + env-file template (mirror the queue-daemon
  unit conventions incl. LogsDirectory= per the gate-hardening pattern) — deploys the DRY-RUN
  loop (disarmed) as a supervised service.
- Health probe script or --health flag consistent with how launch-queue-daemon.sh does it.
- Replace the hard-refusal stub in `deploy/singleton-redeploy/redeploy-singleton.sh`
  (lines ~281-288) with real redeploy support for --daemon option-a-materializer.
- Tests: unit-file render/lint check consistent with existing deploy tests
  (test_gate_daemons_systemd.py idiom), redeploy-script dry-run path for the new daemon.
Files: deploy/materializer/** (NEW), deploy/singleton-redeploy/redeploy-singleton.sh, the
relevant deploy test module + changelog + carrier (slug=branch). `- **Declared work class:** S`

## Stop lines (all units)
ARMING_ENABLED flip (NEVER in this batch), .ce/brain/assertions.yaml, ce_cli.py, v3_cli.py,
launch_runtime.py, checks/**, pr_preflight.py, release_acceptance.py, ticket_reconcile.py,
seat-watch + queue-daemon deploy assets (except the one redeploy-script section named in B),
.github/**, install.sh, docs/llms-install.md, any file in another unit's carrier.
