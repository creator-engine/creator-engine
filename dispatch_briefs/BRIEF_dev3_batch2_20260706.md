# BATCH ADDENDUM — dev-3 — queue alongside your in-flight ce-467-version-drift-gate
You are a foreman — run these concurrently with #467 where safe (separate worktrees).
UNIT B1 — GATED RESUME of parked ce-461 (adoption e2e fixture): poll origin/main (every ~10 min between other work); the moment it contains the adoption-template merge_group fix (PR #859, grep the template in validators/creator_engine_validator/onboard_apply.py for merge_group), un-park: branch ce-461-adoption-e2e-fixture off THAT main, execute your original brief /var/tmp/BRIEF_dev3_ce461_e2e_fixture.md in full (its stop lines stand). Commit-only, READY <sha>.
Territory unchanged: tests+fixtures only for B1; no product code; report product gaps as findings.
