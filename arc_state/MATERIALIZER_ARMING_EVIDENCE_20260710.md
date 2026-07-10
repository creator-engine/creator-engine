# Materializer Arming Decision — Operator Evidence Summary (R-1)
Prepared 2026-07-10 by a governed read-only research worker; verified sources cited by
absolute path throughout. Controller disposition at the end.

## 1. What the materializer does when armed
When armed, the materializer polls origin/main first-parent history for pending brain append
intent files under `.ce/brain/append-intents/<branch-slug>.yaml`, acquires a singleton lease,
reads the live ledger tail from `.ce/brain/assertions.yaml`, and builds deterministic typed
records with a mediation block binding each record to its source merge commit, intent SHA-256,
and branch slug. It then pushes a single direct commit to main that atomically appends the
records and removes the consumed intent, with a compare-and-swap parent check. Every failure
mode enters an explicit HELD state with a 30-minute closeout window before hard failure; no
intent is silently dropped.
Source: /home/ce-dev-2/creator-engine/validators/creator_engine_validator/brain_intent_materializer.py
Design: /home/ce-dev-2/creator-engine/docs/design/ce-491-optiona-merge-intent.md

## 2. Dry-run evidence
- 9 test files (test_brain_intent_materializer_*.py), 52 test functions (~62 cases with
  parametrization). Dry-run tests prove: `run_dry()` writes dry-run artifacts with
  `status: would_materialize`; JSONL event log is append-only and hash-verifiable; malformed
  intents → HELD with quarantine artifacts; `ARMING_ENABLED is False` asserted at import.
- Record builder is byte-for-byte deterministic across all 4 intent kinds; scan ordering and
  consumed-intent exclusion proven; the 30-minute HELD boundary is exact; write-path guards
  block /tmp traversal and `..` escapes.
- ⚠️ No PRODUCTION dry-run artifacts exist in .ce/state — evidence is unit-suite only; the
  materializer has never been invoked against the live repo.

## 3. Arming mechanism (three changes required on arm day)
1. `ARMING_ENABLED = False` (module constant, line 23) flipped via governed PR.
2. **`construct_materialization_commit()` is a STUB** — validates write bounds then raises;
   no commit/push logic is implemented. Arming today would change nothing.
3. GitHub App private key (app 4_244_593 / installation 145_152_358) has NO provisioning
   runbook and NO env-file template on this host.

## 4. Singleton + IaC precondition — NOT MET
The ratified rule: singleton daemons need a proven IaC redeploy path BEFORE arming. The queue
daemon satisfies it (unit + launch wrapper + redeploy script with health probe). The
materializer does NOT: /home/ce-dev-2/creator-engine/deploy/singleton-redeploy/redeploy-singleton.sh
lines 281-288 hard-refuse: "option-a-materializer is not yet deployed; no systemd unit exists
to redeploy". No unit file, no env template, no health probe in deploy/.

## 5. Risk statement
Worst credible failure when armed: a pushed commit with an incorrect prev_hash permanently
breaks the ledger hash chain, invalidating all subsequent tail proofs and blocking every
future brain append until manual Operator recovery. Not self-healing.
Existing guards: armed-write target hard-limited to the two ledger paths; tail proof before
any build (failure → HELD); idempotency by materialization_key; path-traversal guards; local
singleton lease (explicitly NOT a multi-instance correctness guard — design Open Question 4).

## 6. Recommendation: **DO-NOT-ARM-YET**
Primary gate: IaC redeploy precondition unmet. Secondary: commit path unimplemented; App-key
provisioning runbook absent; design Open Questions 1/2/4 (arming authority, credential form,
lease topology) remain BLOCKING-FOR-IMPLEMENTATION.

## Controller disposition (ce-dev-2 face, 2026-07-10)
R-1 as ratified asked for the arming decision to return to AWAITING-OPERATOR. The evidence
shows the decision is NOT RIPE: arming is not implementable today. The Operator-actionable
item is therefore a BUILD ratification, not an arming decision:
**Proposed pre-arming slice set (ratify to queue as arc units):**
  (a) implement construct_materialization_commit (CAS push path) — M;
  (b) materializer systemd unit + env template + redeploy-singleton support + health probe — S;
  (c) App-key provisioning runbook (OpenBao-backed per the custody lane) — S;
  (d) resolve design Open Questions 1/2/4 in a short ADR — S.
Arming returns to AWAITING-OPERATOR only after (a)-(d) land with a production dry-run pass
recorded in .ce/state.
