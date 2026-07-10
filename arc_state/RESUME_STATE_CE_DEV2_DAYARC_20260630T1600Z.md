# RESUME STATE — CE-DEV-2 Orchestrator — DAY-SHIFT ARC — 2026-06-30 ~16:00Z

> NEWEST. Supersedes 1450Z. Open this + MEMORY.md FIRST. Arc RATIFIED (G1–G7). Lanes L1–L10 (see DAYARC_MANDATE_CE_DEV2_20260630.md).

## ✅ SHIPPED / MERGED THIS BLOCK (the 3-PR closeout from 1450Z, all unblocked + landed)
- **#687** (deploy/dgx dev-4 surface fix) — was merge-BLOCKED by a real test failure: `test_surface_build_wiring` still pinned codex image `0.141.0-aarch64` while manifest/build-script moved to `0.142.4`. Fixed (bumped test → 0.142.4, carrier regen 7 paths), Haiku delta-review APPROVE, re-approved ce-dev-2, **MERGED**.
- **#688** (ce-ops#375 P0 scope-impact, dev-1) — independent reviewer APPROVE (warning-only, no mutation, back-compat, deterministic sha, good tests), ce-dev-2 approved, **MERGED**. main now `642a2fd9`.
- **#689** (ce-ops#374 L9 docs overview, dev-3 harvested) — **MERGED** (main d4c0d1bd7). Public-docs product-lens reviewer PASS.
- **#690** (ce-ops#379 work-class choices back-compat, dev-3 harvested+rebased) — independent APPROVE + ce-dev-2 approved → **merging**. Closes the version-skew that broke #689.
- **dev-4 HEALED** — codex re-auth via device-auth (Operator browser step) → live free seat, now on L3.

## 🎫 TICKETS FILED THIS BLOCK
- **ce-ops#379** — G5 version-skew (stale-base branches reject normalized work-class). FIXED by #690.
- **ce-ops#380** — DGX launcher `CE_DGX_IMAGE` lacks the surfaces_manifest CI guard the VPS one has → silent stale-image drift. Being built by dev-3 now.

## 🔑 CORRECTIONS to 1450Z resume (it was wrong on two seats)
- **dev-3 was NOT stalled** — #374 was DONE (committed in container worktree `/var/tmp/wt-ce-374-prepitch-docs-slice`), just **unpushed (no GH auth in container)**. Harvested via git-bundle out of container → PR #689. Lesson: idle-on-main ≠ stalled; check the worktree + harvest. [[ce-harvest-contained-seat-stale-origin]] [[ce-seat-done-not-committed]]
- **#689 stale-base CI failure** — branch cut pre-#686 (at 80ef8dd); FORGE G5 workflow (post-#686 main) normalizes body `story`→`S`, but the stale branch's validator only knows legacy `tiny/story/feature/epic` → rejected `S`. Fixed by **rebasing #689 onto current main**. Systemic gap filed = **ce-ops#379** (version-skew; 3 fix options). This is exactly why arc L5 says "seat origin-refresh BEFORE dispatch (else stale-base PRs)."

## 🩺 FLEET (ALL THREE WORKING as of ~16:28Z)
- **dev-1** (non-contained, self-syncs): **WORKING → L1 clean-room install e2e** (verify-path, D2). Brief `~/ce-briefs/ce-L1-cleanroom-install-e2e-dev1-20260630.md` (on dev-1). Expect: evidence report + green/broken verdict + maybe `ce-L1-install-e2e-fixes` doc PR (self-pushes — non-contained).
- **dev-3** (contained, fetch-egress YES / push needs HARVEST): **WORKING → ce-ops#380** (symmetric surfaces_manifest CI guard for DGX launcher `CE_DGX_IMAGE`). Branch `ce-380-dgx-launcher-image-guard`. Brief `/var/tmp/ce-380-brief.md`. PRIOR task #379 done→harvested→**PR #690 (merging)**. HARVEST #380 when done (git-bundle out, like #374→#689→#690).
- **dev-4** (contained DGX): ✅ **HEALED + WORKING → L3 forge Triage Ready Queue P0**. Branch `ce-L3-triage-ready-queue-p0`. Brief `/var/tmp/ce-L3-brief.md`. Re-authed via `codex login --device-auth` (Operator did browser step) → fresh ACCT B token, 100% quota, image 0.142.4-aarch64, ssh-keygen+PyNaCl ✓. HARVEST when done. **Launch rule: ALWAYS pass `CE_DGX_IMAGE=...0.142.4-aarch64` explicitly** (stale-branch launcher defaults to broken 0.141.0 — [[ce-dev4-rebuild-and-launch-canon]], ce-ops#380).
- L3 design (architect, this block) = `ce_ops_triage_queue.py` + `ce triage queue` CLI + cron workflow; reuses forge_triage classifiers; advisory-only, fail-open, apply=False default, date-range candidate filter. **Pre-live Operator setup: ce-ops#67 needs a pinned comment with `<!-- ce-triage-queue-issue:v1 -->`** before the workflow goes live.

## ⏭️ NEXT ACTIONS (on resume) — dispatch-ready
1. **Dispatch dev-1 → L1 onboarding e2e** (HIGHEST, today-time-boxed): clean-room install e2e GREEN vs live `creator-engine.dev/llms-install.md`; onboarding handoff doc; contributor path verify. L1.a/L1.b build (#366 ratified) is dev-1 post-scout. Cross-machine brief: write file → transfer via stdin→tee into dev-1 checkout → pointer+sha (NOT inline).
2. **Dispatch dev-3 → L3 forge-triage (#67)** off fresh main (now refreshed). Contained → embed brief content (no private-ticket refs); arm watcher; harvest to push.
3. **dev-4 codex re-auth** — needs ACCT B interactive (Operator). Then it's a free seat (route hardest work; e.g. L2 autonomy-arming build or L4 brain).
4. ce-ops#378 (work-mgmt SSOT doc) — review/merge (ce-ops repo). ce-ops#377 per-arch digest fix dispatch. ce-ops#379 version-skew fix dispatch. #376 sweep.
5. Fleet-IaC P1 (framing approved `.ce/briefs/fleet-iac-p1-framing.md`).

## 🚨 L1 ONBOARDING BLOCKER + R5 AUTHORIZED (live, ~17:30Z)
- dev-1 clean-room e2e verdict = **BROKEN** for a strict new-user verbatim run of live `creator-engine.dev/llms-install.md`: (1) §0 sig-verify needs `ssh-keygen` but docs don't list `openssh-client` as a prereq (clean Ubuntu 24.04 lacks it; after manual install the full path PASSED — install 0.3.1+91d20efc, verify-install PASS); (2) §0.5 stale prose still says 0.2.0 (downloads/0.2.0/SHA256SUMS, creator-engine-validator==0.2.0) vs live 0.3.1.
- **dev-1 PREPARING the fix** (branch `ce-L1-install-doc-fix`): edit docs/llms-install.md §0 (add openssh-client prereq) + §0.5 (0.2.0→0.3.1), emit canonical bytes for signing. NO push-to-green (install-spec guard RED until signed).
- **✅ OPERATOR AUTHORIZED R5 (2026-06-30) to re-sign the updated docs/llms-install.md** for this openssh-client+0.3.1 fix. Key present `~/.ce-keys/ce-root-v1`(+.pass/.pub). NEXT: when dev-1 emits the prepared edit+bytes → review diff → sign with ce-root-v1 → embed → `ce verify-install` green → ship (independent review + ce-dev-2 approve). Recommend follow-up: bootstrap preflight ssh-keygen check (actionable error) so users don't need to read prereqs.

## 🔴 OPERATOR-GATED (surface, can't self-do)
- **dev-4 re-auth** (shared ACCT B browser/device flow).
- **R4 contributor access grant** — need Nitzan's GitHub handle + scope (outside-collaborator vs org-member; repos; push-branch vs fork-only) to exercise. Path verify is autonomous; access grant = Operator act.
- **R5 spec-signing** — per-instance offline ce-root-v1 (any release).

## DAEMONS / MONITORS
queue-daemon PID 43010 alive (log /home/cedev2/ce-wall-daemon.log — settle→mint→enqueue→auto-merge; approval-triggered CI re-runs cause settle churn but converge). Board monitors b9aipnn3b/bh8s12igt alive.

## WORKTREES
Removed wt-ce687-fix, wt-ce688-review (merged). wt-ce689-review + wt-ce374-harvest remain until #689 merges (then prune). ~210 stale .ce/wt-* worktrees still need the L5(d) prune (G7).

## NEW THIS BLOCK
ce-ops#379 (version-skew). Memory: [[ce-contained-seat-completed-but-unpushed-not-stalled]].
