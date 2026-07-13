# Creator Engine 0.3.6

## Highlights

- Complete the **daemon heartbeat ladder** (S1→S2→S3→S4): every background daemon now emits bounded, non-secret liveness records and stale/failed daemons raise structured alarms.
- Ship the **`ce checkpoint` verb** and controller continuity checkpoint protocol for durable, redaction-safe session handoff.
- Add the **M2 governed review-acting spawn provider** (default-OFF, Operator-armed) and wire the **M4 ratifier-queue** to the CLI (SL-DAY-2 P1 / NIGHT-6 W1).
- Block double-assignment at the **work-claims layer (M6)**.
- Fix the **install-answers schema mirror drift** that caused `INSTALL_REFUSED artifact_hash_mismatch` on every fresh install (ce-ops#992).
- Add a **Dockerfile image-build smoke tier** to PR validation (ce-ops#543).

## Internal improvements

Plus reliability and internal tooling improvements across forge spawn, brain reconcile, preflight, onboarding, and schema generation.
