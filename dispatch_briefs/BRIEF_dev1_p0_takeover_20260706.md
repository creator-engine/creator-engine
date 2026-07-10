# BRIEF — dev-1 — P0 BATCH: ce takeover + posture banner (ce-ops#477 + #478, ratified program, lands THIS ARC)
2026-07-06 ~15:1xZ by CE-DEV-2. Role: implementer/foreman, self-push. Slot AFTER your #859 wheel-build triage resolves. You have gh — read ce-ops#477 and ce-ops#478 in full; their acceptance bars are the spec (ratified as a block by Operator today; do not relitigate any embedded decision).

Sequencing directive (bounded work-units, ~200/400-line PRs — SLICE, do not ship one monster):
1. Slice A (small, ship first): #478 posture banner — the read-only reporting command. Branch ce-478-posture-banner.
2. Slice B: #477 core — `ce takeover` detect/select/verify/hydrate path with --dry-run --json, REUSING the existing launch specs (codex_launch_spec/claude_launch_spec/launch_runtime) — this is wiring, not new governance. Branch ce-477-takeover-core.
3. Slice C: #477 refusal-that-teaches (raw role=controller launch → READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED + prints the exact command) + watcher re-arm from duty manifest. Branch per slice.
4. Slice D: continuity drill harness (scheduled; benign governed gate cycle proof). Can trail into next arc if C lands first.

Known facts to build against: the 2026-07-06 handover packet (.ce/state/research/HANDOVER_PACKET_CE_DEV2_20260706.md on the controller host — content summarized in #477) is the manual procedure ce takeover automates; a live codex standby controller was launched today via `ce launch --harness codex` and the friction log rides #471.

Territory note: dev-4 has in-flight changes to ce_cli.py + lane_runtime.py (PR #864 round-2) — expect rebases there; do not touch lane reviewer-authority code.

Bar per slice: FULL ce validate-pr GREEN; carrier (stem == branch slug); changelog; declared work class per G5 honestly (banner=tiny/story, takeover core=story); new `ce` verbs trip the docs-coupling test — write the docs. Self-push + PR; report PR#s + heads. STOP lines standard (no sign, no merge, no settings, no sha-pinned files).
