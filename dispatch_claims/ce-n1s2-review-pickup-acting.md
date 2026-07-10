# WORK CLAIM — ce-n1s2-review-pickup-acting
claimed: 2026-07-10T15:2xZ
controller: ce-dev-2 (Claude face)
seat: dev-4 (ce-dgx-codex) — active unit; ce-f1s2 stays gate-queued behind it
ticket: STRANGELOOP-2 N-1 slice 2 (spawn-on-event chains acting; review-pickup chain first)
branch: ce-n1s2-review-pickup-acting
role: implementer
work_class: M
scope: promote review-pickup from advisory (s1 #917) to ACTING for PR-opened → spawn reviewer →
  post verdict as PR COMMENT (issues endpoint only; structurally unable to approve/merge).
  Flag-gated default OFF (CE_REVIEW_ACTING_ENABLED); NDJSON dedup ledger per pickup.py idiom;
  failure containment (spawn_failed incident, never crash-loop); IaC = commented armed variant
  in existing service file. EXCLUDED: harvest-prep + approved→merge chains, any approval
  authority, token minting changes.
territory: forge/review_acting.py (NEW), test_review_acting.py (NEW), v3_cli.py (flags wiring),
  deploy/systemd/ce-review-pickup-daemon.service (comments), CHANGELOG.md, changelog+carrier.
  Collision scan 2026-07-10T15:2x: no in-flight branch touches v3_cli.py or the service file;
  ce239 touches test_v3_cli.py only (different file; brief forbids touching it). Verified
  not-landed: zero acting-path hits on main.
evidence_expected: READY-FOR-HARVEST ce-n1s2-review-pickup-acting <40-hex-sha> after the 11
  required test cases + confidentiality check green + default-OFF confirmation.
