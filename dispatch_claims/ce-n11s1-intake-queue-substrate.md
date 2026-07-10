# WORK CLAIM — ce-n11s1-intake-queue-substrate
claimed: 2026-07-10T16:4xZ
controller: ce-dev-2 (Claude face)
seat: dev-4 (ce-dgx-codex)
ticket: STRANGELOOP-2 N-11 slice 1 (conveyor intake queue — claim lifecycle on the existing substrate)
branch: ce-n11s1-intake-queue-substrate
role: implementer
work_class: M
scope: extend the EXISTING conveyor_intake_queue.py (prior slice found on main by the drafter's
  verify-not-landed pass) with pointer+sha doctrine fields (brief_sha, territory_paths), full
  claim lifecycle (claim/release/complete with ownership checks, TTL + stale reclaim), and an
  append-only NDJSON claim ledger. Atomicity via POSIX os.replace. Value-free entries; claiming
  grants no authority. EXCLUDED: arc-feed daemon, seat auto-pull loop, dispatch retirement.
territory: conveyor_intake_queue.py, test_conveyor_intake_queue.py,
  docs/design/conveyor-intake-queue.md, changelog+carrier.
  Collision scan 2026-07-10T16:4x: no in-flight branch touches conveyor_intake_queue.py or its
  test/design files (checked all current wave branches + n1s2 + f1s2).
evidence_expected: READY-FOR-HARVEST ce-n11s1-intake-queue-substrate <40-hex-sha> after the ten
  new test cases + existing tests + confidentiality check green.
