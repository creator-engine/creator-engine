# BRIEF — dev-3 — Support agent Phase C: Discord channel adapter (ce-ops#360)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-supportagent-discord-adapter` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report HEAD SHA. Carrier slug MUST equal branch slug `ce-supportagent-discord-adapter`.

## Context (EMBEDDED — you cannot read the ticket; this IS the scope)
CE's support agent has a channel-AGNOSTIC governed core in main: `support_runtime.answer_question()` (retrieval → cite-or-refuse → zero-leak → returns a `SupportAnswer`). The durable architecture = thin per-channel ADAPTERS over that stable core. Operator wants Discord first (Slack/web later as more adapters). **Read `support_runtime.py` + `SupportAnswer` FIRST and match the existing interface — do NOT modify it.**

## Goal — a thin, testable Discord adapter (NO live connection, NO hard discord.py dep in CE core)
Build the channel-translation layer: inbound Discord message → `answer_question()` → outbound Discord reply. The live Discord gateway connection + bot token + deploy are CONTROLLER/deploy concerns — you build the adapter LOGIC + a clean seam, fully tested against a MOCK client.

## Deliverables — NEW FILES ONLY (do NOT edit support_runtime.py / support_profile / support_eval.py / any existing module — other lanes in flight)
1. **Adapter module** (new file, e.g. `validators/creator_engine_validator/support_channel_discord.py` or `tools/support-agent/discord_adapter.py` — pick a sensible path): a channel adapter that
   - Defines a small CLIENT seam (Protocol/ABC) for "receive a message" + "send a reply" so the live Discord client is INJECTED — the adapter core does NOT hard-import `discord.py` (keep CE core dependency-free; any real discord client is an optional/injected impl, imported lazily behind the seam).
   - On an inbound message: extract the question, call `answer_question()`, and render the governed `SupportAnswer` into a Discord-appropriate reply (include citations when answered; render the refusal cleanly when refused — never invent content). Respect Discord's message length limits (chunk/truncate sensibly).
   - Fail-closed/graceful: any error → a safe generic reply (e.g. "I couldn't answer that right now"), never a crash, never leaking internals/stack traces.
2. **Tests (CI-safe, NO network)** (new file): drive the adapter with a MOCK client + a stubbed/real `answer_question` (mock the model seam as the existing tests do). Prove: inbound message → answer_question called → answered reply rendered with citations; a refusal renders the refusal text (no fabricated answer); an error path yields the safe reply (no crash, no internal leak); long answers are chunked/truncated. Do NOT make any live network/Discord call in tests.
3. Optional: a tiny README/docstring documenting how a live discord.py client would bind to the seam (for the controller's later deploy) — but NO live wiring here.

## Do NOT
- Do NOT edit `support_runtime.py`, `support_profile`, `support_eval.py`, or any existing support/runtime module (in-flight lanes own them). New files only.
- Do NOT add a hard/top-level `discord.py` (or any provider) dependency to CE core; keep it injected/optional behind the seam.
- Do NOT make live Discord/network connections; do NOT add a network call to any CI-run test.
- Do NOT weaken cite-or-refuse / zero-leak; the adapter only TRANSLATES the governed answer, never bypasses it.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Carriers: manifest via `carrier_gen.write_carriers(base=<merge-base>)` API (rm build/egg-info first); VERIFY the `- **Declared work class:** <x>` line is present (the API omits it — add if missing; likely `story`) + `.ce/changelog/<slug>.md`. Slug == branch. Product-lens. STOP at green; report SHA. Do NOT push.
