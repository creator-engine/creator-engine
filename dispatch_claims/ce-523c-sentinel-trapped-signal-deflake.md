# WORK CLAIM — ce-523c-sentinel-trapped-signal-deflake
claimed: 2026-07-10T13:2xZ
controller: ce-dev-2 (Claude face)
seat: dev-3 (ce-vps-codex)
ticket: ce-ops#523 (follow-up c: trapped-signal case)
branch: ce-523c-sentinel-trapped-signal-deflake
role: implementer
work_class: XS
scope: deflake test_wrapper_trapped_signal_writes_exit[1-129] (fails intermittently on
  unmodified main baselines — beyond dd71c9cf33's exit-record-wait fix). Root-cause the
  residual race, surgical fix (test seam preferred; product seat_sentinel.py only if the
  race is product-side), 30x consecutive green proof.
territory: validators/tests/unit/test_seat_sentinel.py,
  validators/creator_engine_validator/seat_sentinel.py (conditional, minimal),
  changelog+carrier (NEW).
  Collision scan 2026-07-10T13:2x: NO COLLISIONS — no open PR or held-queue branch touches
  either file (#950 lineage merged; ce-523b touches test_jit_credential_broker.py only).
evidence_expected: READY-FOR-HARVEST ce-523c-sentinel-trapped-signal-deflake <40-hex-sha>
  after 30x loop + focused file run + confidentiality check green.
