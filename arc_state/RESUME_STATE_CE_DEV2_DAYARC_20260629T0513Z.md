# RESUME STATE — CE-DEV-2 Orchestrator — DAY-SHIFT ARC — 2026-06-29 ~05:13Z — checkpoint for fresh-context continuation

> NEWEST. Operator asked to checkpoint + continue the ARMING + SUPPORT-AGENT discussion with fresh context. Open this + MEMORY.md FIRST. Supersedes the night-arc FINAL checkpoint.
> ⭐ ROLE: OVERARCHING ORCHESTRATOR — drive via seats/workers, NEVER inline. Author≠approver. AUTONOMOUS=dispatch/harvest/review/gate/merge; RESERVED→HALT (arming flips, release-sign, deploy, fleet-rollout, history-scrub).

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. queue-daemon (pid 43010) auto-merges approved+green. Agent routing pinned (reviewer/implementer/architect=sonnet, verification=haiku, Opus=controller).

## 🔴 TOP ACTIVE THREAD #1 — ARMING (Operator said "arm it" = BOTH surfaces; bring the precise flip to ratify)
Both arming WIRINGS now MERGED to main; nothing is live yet (inert by design). The flip is R-RESERVED = Operator's act.
- **Surface A — AUTO-MERGE** (#641-no wait that's B; auto-merge wiring = **#642 ARM-A merged**): the live caller (automerge-actuate.yml + automerge_actuate_cli.py) + required_checks=["Validate governance artifacts"] are in main. EXACT ARMING FLIP = edit `.ce/state/automerge/policy.json`: set `run_mode: "ceo"` (from "dev") + `classes.docs.auto_merge: true` + a non-empty `enabling_decision_ref` (a ratification record); kill_switch stays false. Effect: only docs/none-class PRs (docs/**, *.md, .ce/changelog/**, .ce/pr-manifests/**) that are review-approved+green+work-class-declared auto-merge. Rollback: run_mode→"dev".
- **Surface B — AUTONOMOUS APPROVE** (broker --run-mode = **#641 ARM-B merged**, ce-ops#346): EXACT ARMING FLIP = set systemd env `CE_EGRESS_RUN_MODE=strangeLoop` (from "dev") on `deploy/systemd/ce-egress-self-review.service` (EnvironmentFile) + RESTART the broker daemon. Effect: contained reviewers w/ a valid reviewer-authority-envelope under strangeLoop run-mode may submit APPROVE. author≠approver host-side wall + envelope validation STILL enforced (a seat can NEVER auto-approve its OWN PR). Rollback: env→dev + restart.
- ⚠️ **PRE-ARMING HARDENING IN FLIGHT (dev-4, branch ce-harden-actuator-arming-guard):** review found 2 actuator smells — (1) dormancy guard `if run_mode=="dev"` is non-strict (any non-dev string arms) → hardening to strict allowlist `_ARMING_RUN_MODES={"ceo"}`; (2) actuator trusts the decision-ARTIFACT run_mode not live policy.json → hardening to re-verify live policy.json at actuation (makes disarm immediate). HARVEST→review→gate this BEFORE presenting the arming flip, so the control is fail-safe when armed.
- **ON RESUME:** once the hardening merges, COMPOSE + present the consolidated one-tap arming ratification (both surfaces, exact lines above + rollback + the in-flight-artifact caveat). Get Operator's explicit confirm-on-the-specifics before executing (reserved).

## 🔵 TOP ACTIVE THREAD #2 — SUPPORT AGENT (Frame/Shape done; research landed; awaiting Operator direction to scope build)
Synthesis saved: `.ce/state/research/SUPPORT_AGENT_HARNESS_RESEARCH_SYNTHESIS_20260629.md` (full report in agent transcript a4e78950).
- RATIFIED FRAME: one governed CORE (4 shipped Python files: support_corpus.py/allowlist.yaml/system_prompt.md/profile.py), MANY surfaces, TRUST-TIERED (internal-infra corpus vs product-lens; separate processes), read-only Phase-1 / action Phase-2.
- RESEARCH RECOMMENDATION (validated Operator hypothesis w/ 1 sharpening): (a) `ce ask` CLI → Claude Code subprocess; (b) hosted Discord bot (VPS) → **Claude Agent SDK (Python) directly + discord.py** (NOT NanoClaw — TS breaks the Python spine; NanoClaw is the design REFERENCE, and is itself built ON the SDK); (c) in-user-project tool → user's Claude Code + CE-shipped read-only skill bundle. Managed Agents RULED OUT (server-side data = internal-tier disqualifier). NemoClaw = NVIDIA-pitch reference (structural enforcement = our thesis).
- **⏸️ AWAITING OPERATOR — 3 gating decisions to scope the build handoff:** (1) internal-infra corpus scope (pilot can START on product-lens corpus, defer this); (2) Discord topology (one server role-gated vs two separate servers); (3) budget caps (per-call + monthly; or I set a conservative default). Plus deferrable: ce-ask-internal auth, corpus-freshness automation, Phase-2 action scope.
- MY REC: greenlight the smallest pilot now (`ce ask` wired [in flight as #354] → internal Discord bot on VPS product-lens corpus role-gated → eval → external bot after zero-leak eval). Scope the build handoff on Operator's confirm + a budget number.

## 🟢 ALSO AWAITING OPERATOR — OQ-1 mechanism ratification
**#643 (OQ-1) gated** → recommends **Option A**: Linux bwrap+Landlock+seccomp + deny-by-default egress proxy (egress proxy REQUIRED since Landlock can't gate network); macOS Seatbelt/sandbox-exec as parallel lane; gvisor-proxy stays DEFAULT; os-native user-elected fail-closed; CE-native jail deferred. Reviewer independently confirmed technically sound. RATIFY → unblocks #353 (os-native fix impl) + #352 (macOS Seatbelt lane).

## IN-FLIGHT SEATS
- dev-1 (VPS tmux, self-push) → **#354 support-agent Phase-1** (P0.2 bundle projector + model-wiring for `ce ask`; cite-or-refuse/read-only/dev-gated; mock model in tests). NOTE: I had to TRANSFER the design SSOT to dev-1 (~/ce-briefs/CE_SUPPORT_AGENT_PLAN_20260627.md) — it's a DGX-local file not in git; dev-1 (VPS, diff machine) couldn't read it. On self-push → review + gate.
- dev-3 (contained ce-vps-codex) → **corpus-scrub** (ce-corpus-scrub-contributing: scrub contributing-to-ce.md + playbook-format.md off KNOWN_PENDING + re-add to support_corpus_allowlist.yaml → widens ce ask for the contributor). On READY → harvest→review→gate.
- dev-4 (contained ce-dgx-codex DGX-local) → **actuator hardening** (ce-harden-actuator-arming-guard, above). On READY → harvest→review→gate, THEN compose arming flip.

## BOARD / MERGE TALLY
Board: #642 + #643 APPROVED (merging). Day-shift merges so far: #641 (ARM-B broker --run-mode/#346) + #642 (ARM-A auto-merge wiring) + #643 (OQ-1 doc) + (night arc was 20: #621-#640). queue-daemon ALIVE; brain UP; wall token good to ~07-01.

## DAY-SHIFT TICKETS FILED
#352 (native macOS — os-native/Seatbelt start; needs Operator signed wheelhouse later) · #353 (os-native selectability bug — gated on OQ-1 ratify) · #354 (support-agent Phase-1, parent #317). Sibling corpus-scrub in flight (dev-3).

## ⏸️ CONSOLIDATED AWAITING-OPERATOR QUEUE (surface FIRST on resume)
1. ARMING flip (both surfaces) — compose + present after hardening merges.
2. SUPPORT-AGENT — 3 gating decisions + greenlight smallest pilot.
3. OQ-1 = Option A — one-tap ratify → unblocks #353/#352.

## WATCHERS
Board Monitor **bh8s12igt** (PR-set+reviewDecision). Seat-READY Monitor **bxa44s2dn** (dev-3/dev-4 READY-or-idle). Hourly cron **0a34687f** (:47). Re-arm if the session changed them.

## LESSONS THIS ARC (locked)
- **Don't run 2 host-side full validate-pr concurrently** — they contend on the venv/egg-info and BOTH crawl (caused the ARM-A/OQ-1 harvests to take ~6min+ each). Serialize host harvests, or accept slowness.
- **DGX-local files (.ce/state/research/*) are NOT in git + NOT on the VPS** — briefs to dev-1 (VPS) / contained seats must EMBED content or I must TRANSFER the file first. (Stranded dev-1 on #354 once; fixed by scp-ing the SSOT.) [[ce-no-egress-seat-self-contained-briefs]]
- **Carrier false-blocker (×4) + stale-local-main false-blocker:** judge carriers from the PR's ONE added (slug-matched) carrier; trust CI-green over a local `base..HEAD` diff; my main working tree is on stale branch `ce-brain-vllm-embedder` — always `git fetch origin main` first. Verify every "blocking" finding vs CI/origin before acting.
- Harvest absorbs the egg-info footgun + autogen/ratchet coupling (regen in a clean worktree); seats honestly REFUSE out-of-scope gates rather than fake green — good.

## ON RESUME (fresh context)
1. Read this + MEMORY.md. 2. `gh pr list` + reconcile (#642/#643 merged?; dev-1 #354 PR?; dev-3/dev-4 READY?). 3. Verify watchers/daemon. 4. Surface the ⏸️ AWAITING-OPERATOR queue (arming flip / support-agent decisions / OQ-1=Option A). 5. Harvest+review+gate the hardening → then compose the arming flip. Continue the arming + support-agent DISCUSSION with the Operator.
