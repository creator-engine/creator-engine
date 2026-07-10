# PROGRAM STATE — CE-DEV-2 · 2026-06-23 · 🏗️ TWO PARALLEL FORCE-MULTIPLIER PROGRAMS

**WRITTEN BY/WHERE:** CE-DEV-2 controller (`cedev2` on DGX `spark-b824`), Opus 4.8 effort-high. Companion to RESUME_STATE_CE_DEV2_20260623_INTEGRATOR-AND-REREVIEW.md. **Operator GO 2026-06-23:** build #163 (with #148 first) AND the Integrator MVP IN PARALLEL — "think in concurrency terms." Interim: REMIND seats to delegate to workers (foreman model) until #163 lands and makes it autonomous.

## ✅ WAVE 1+2 LANDED (main @ 0d4ed0e2+)
#369·#364·#365·#366·#367·#368 (Wave 1) · #371 (launcher-refuse) · #372 (bot-fix durable: ruleset default flipped) · #370 (notify report-fold) · **#337 (forge.re_review — DIFF-AWARE RE-REVIEW LANE, TOP priority, MERGED 08:24)**. #373 (onboard orchestrator) rebased+APPROVED (dev-3 approval SURVIVED rebase via the ruleset patch), head 54ab4894, **pending CI → enqueue when green** (gh pr merge 373 --auto set).

## 🏗️ LANE ALLOCATION (disjoint file-sets → both programs merge in parallel)
- **LANE 1 — Integrator MVP (ce-ops#216)** → **dev-1** (foreman; spawned 2 workers for Units 1+2). Phase-1 deterministic-only: U1 eviction-detection (watch queue for APPROVED+green→DIRTY/BEHIND/CONFLICTING) · U2 deterministic resolver library (TODAY's _versions.py frozenset-union / test_version_boundary count / changelog+manifest take-both resolutions = the spec) · U3 executor+race-guard (read-only resolver, executor holds write, §7/minter posture) · U4 escalation seam (non-mechanical → controller). Files: `forge/` + new `integrator` module.
- **LANE 2a — #163 prerequisite ce-ops#148 (provisioning)** → **dev-3** (branch `ce148-seat-provisioning`; ⚠️ 85% context — watch for compaction/inline-drift). Deliver: provision-by-construction (offline wheelhouse install into venv) + `ce bootstrap`/`ce doctor --fix` + NAMED `ce doctor` FAIL for app-not-importable. Files: bootstrap/installer + doctor.
- **LANE 2b — #163 core** → **dev-4** (foreman; DGX/strongest). RATIFIED defaults: hard-deny force-delegation modeled on §7 push-block; trigger=action-type×irreversibility (NOT line-count); isolation=worktree+cred-scrub; foreman-of-foreman depth-bounded. Units: REQ-2 harness-agnostic worker-spawn primitive (FOUNDATION — Codex/Hermes lack native fan-out) → REQ-1 born-a-foreman launcher inject → REQ-3 §7-style hard-deny refusal (regression: direct impl refused, worker-routed allowed). Files: launcher + refusal-spine (`hook_check.py`) + new `seat_class`. Designs against #148's `ce launch` contract IN PARALLEL (don't block on 2a).

## 🤖 TRACK BY BRANCH/PR (agentIds die on /clear)
dev-1 Integrator → PRs forthcoming (2 workers running). dev-3 → `ce148-seat-provisioning`. dev-4 → #163-core branch(es) forthcoming. Each lead is a FOREMAN: decompose + fan out; controller (me) holds merge gate + routes reviews (non-author, intersect manifests — Integrator `forge/` vs #163 `launcher/seat_class` are DISJOINT → parallel-mergeable).

## 📋 GATE DISCIPLINE
reviewDecision==APPROVED on CURRENT head + green + CLEAN before enqueue (`gh pr merge <n> --auto`, no --squash). Ruleset patched → approvals survive rebases (verified live on #373). Bot-fix durable (#372 merged). Route each PR to a non-author seat; serialize any PRs sharing `_versions.py`/`test_version_boundary.py`.

## 🆕 DURABLE DECISIONS THIS SESSION
[[ce-orchestration-replaces-model-upgrade-pitch]] (MOAT: wk-21Jun orchestration surpassed the Fable-upgrade peak wk 68c/67705+, SAME model — cite GH Insights not local git) · [[ce-agent-paced-estimation]] 4th reinforcement (single leg = minutes-to-hours, NEVER days) · [[ce-codex-foreman-directive-durable]] updated (#163 = designed+ratified, gap is BUILD; #148 mechanical prereq).
