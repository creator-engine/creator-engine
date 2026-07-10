# Support Agent — Harness Benchmark + Architecture: Synthesis (2026-06-29)

Research worker output (architect_research, grounded in current 2026 sources). Full report in the agent transcript; this is the decision-grade synthesis.

## Headline
- The GOVERNED CORE is already shipped (4 Python files: support_corpus.py + support_corpus_allowlist.yaml + support_system_prompt.md + support_profile.py). Remaining = harness wrapper + surface adapters + corpus deploy. The moat is built.
- Operator harness hypothesis = CONFIRMED with one sharpening: coding-agent for CLI + in-project tool ✓; minimal harness for hosted bot ✓ — BUT the minimal harness is the **Claude Agent SDK (Python) directly**, NOT NanoClaw. NanoClaw is real (MIT, TS/Node, ~3.9k LOC, ~30k stars) and is the right ARCHITECTURE REFERENCE (container-per-session + SQLite session state + Discord channel pattern), but TypeScript would force a language bridge that breaks the single-sourced Python refusal spine. Decisively: **NanoClaw is itself built ON the Claude Agent SDK** — using the SDK directly picks the minimal layer NanoClaw wraps.

## Recommendation per surface
- (a) `ce ask` CLI → Claude Code subprocess (the existing dev-seat harness via cc_hook_adapter/ce-pretooluse hook). Dogfooding; support_profile fires as PreToolUse.
- (b) Hosted Discord bot (CE VPS) → Claude Agent SDK (Python) + discord.py (~150-line adapter). `pre_tool_use=support_profile.evaluate` is the whole integration seam (~40-60 LOC wrapper). NOT NanoClaw, NOT Managed Agents.
- (c) In-user-project tool → user's own Claude Code + a CE-shipped read-only skill bundle (setting_sources). Runs CE's governed seat when called.

## Trust-tier isolation
Two SEPARATE systemd processes (support-internal.service / support-external.service), each loading a different corpus allowlist YAML; "you can't leak what you never loaded." Internal-infra corpus bytes never enter the external process address space. Internal auth = Discord guild "CE-Internal" role gate (~10 LOC), private server.

## Ruled out
- Claude Managed Agents (Anthropic cloud): server-side data persistence (NOT ZDR-eligible) = hard disqualifier for the internal tier; +$0.08/session-hr; PreToolUse becomes a network hop. Right for FUTURE long-running Phase-2 action agents, wrong for Phase-1 read-only.
- Raw Messages API / CE-native harness: dominated by the SDK (would reinvent the tool loop).

## NVIDIA angle (strategic, not Phase 1)
NemoClaw (NVIDIA, Apache-2.0, GTC Mar-2026) = structural (out-of-process) enforcement — same thesis as CE's hook_check/support_profile. The DGX Qwen3-Embedding stack could be a local-model backend for an NVIDIA-differentiated config (route simple lookups to Nemotron-local, complex to Anthropic). Phase-3.

## Phase-2 action seam (clean)
allowed_tools list + a new action_profile.py + system-prompt scope upgrade. No architecture rewrite. Corpus stack + adapters untouched.

## Smallest pilot (proposed)
1. `ce ask` subcommand wired (CE's FIRST Anthropic API call — budget-capped from day 1).
2. Internal Discord bot on VPS (product-lens corpus, role-gated) for Nitzan/Arad.
3. Eval session (capture refusals/I-don't-knows; zero-leak adversarial probe; file doc-gap tickets).
4. External bot only AFTER zero-leak eval passes.

## OPEN DECISIONS for Operator (before build handoff)
GATING for the pilot:
1. Internal-infra corpus scope — which internal docs the internal bot may answer from (a new internal allowlist YAML). Build can't proceed on the internal tier without it. (Pilot can START on product-lens corpus for both, deferring the internal-infra corpus.)
2. Discord topology — one server role-gated vs two separate servers (stricter isolation).
3. Budget caps — per-call max_budget_usd + monthly ceiling (esp. external).
DEFERRABLE: auth model for `ce ask --corpus internal`; corpus-freshness automation (CI gate vs manual-for-pilot); Phase-2 action scope.
