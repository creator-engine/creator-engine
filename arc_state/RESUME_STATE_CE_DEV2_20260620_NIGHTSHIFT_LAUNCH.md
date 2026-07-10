# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (PM) · NIGHT-SHIFT LAUNCH

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Newest-by-mtime; **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260620_DAYSHIFT_HIGHGEAR.md`. Read this + `MEMORY.md` first. **main HEAD = `707e4406`** (post #287/#286/#289/#288/#285).

**PEER-SEAT → HOST → REACH (verify a handle resolves locally before inferring state):**
- **dev-1** = VPS, `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-1 tmux ... -t ce-dev1-orchestrator`. Reviewer-of-record venue (posts as **ce-dev-1**, a CODEOWNER; `cedev1vps-cmd` persona is NOT gh-provisioned — use ce-dev-1).
- **dev-3** = VPS, `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard:1.0`. Has its OWN gh identity (ce-dev-3) — can self-push.
- **dev-4** = CONTAINED DGX, `ssh cedev4@localhost`; codex tmux `dev4stage1`; **NEVER C-c** (codex is the container Cmd). Worktree host-side = `/home/cedev4/ce-workspaces/creator-engine` ↔ container `/workspace/creator-engine`. Courier via overwatch push (dev-4 has no egress).
- Briefs delivered via: write file → `sha256sum` → `scp` to VPS `/tmp/` (dev-1/dev-3) or `cedev4@localhost:/home/cedev4/ce-workspaces/creator-engine/tmp/` (dev-4) → seed pane with `Read <path> (sha256 <h>) and execute`.

## ⏸️ AWAITING-OPERATOR (surface FIRST)
1. **RATIFY the night-shift arc** (expanded 11-wave draft below). On ratify → file as a ce-ops issue + execute unattended.
2. **#290 verdict** — dev-1 reviewing (CI green, head `14447d6`); on APPROVE → merge as overwatch (closes the day's batch). This is already-authorized "push all three."

## 🌙 NIGHT-SHIFT ARC — DRAFT (awaiting ratification)
**Theme:** make self-serve brownfield onboarding actually work (pitch path) + wrap in-flight + build forward. Quota NOT a limiter (Operator: GPT-Pro pool drains slower than Claude-Max; will upgrade to x20 if hit). Full-night throughput.
**Grants (mirror ce-ops#129):** full unattended on ratified flow (build→green→PR→distinct-controller review→overwatch merge), incl manual ce-ops closes. Hard rules: hashes REPRODUCED never transcribed; distinct-reviewer before every merge; escalate-only-on-blockers; **no binding architecture commit without Operator nod (W4 minting topology)**.
**Dispatch:** hardest builds (W4 #157, W9 #119-impl, W2 #159) → dev-4 (DGX); W1/W3/W5/W6/W7/W8/W10 → dev-1/dev-3; dev-2 controller holds merge gate.

| W | Work | Mode |
|---|---|---|
| W1 | **#290** Ring-1 §8c FS mediation — review(dispatched)→merge | auto |
| W2 | **#159** ship gitleaks/trufflehog hash-pinned in wheelhouse/manifest (pins verified, posted on #159) | auto |
| W3 | **#160** protection floor via Rulesets (free-plan private repos) | auto |
| W4 | **#157** shared-app MINTING BACKEND — wire `app.kind: shared` (escalate on central-vs-per-tenant topology) | auto→PR* |
| W5 | **#153** courier ce-egress-broker (BUILT, commit `095f3527` branch `ce-egress-broker`, worktree `/home/cedev2/ce-egress-broker-seat`) + controller wiring; external-user minting path (pairs W4) | auto→PR |
| W6 | **#158** out-of-band trust anchor for ce-root-v1 (DNS TXT / org profile / Sigstore) + org-detect & error-msg UX fixes | auto→PR |
| W7 | **#281** OpenBao secret-zero broker rework (CHANGES_REQUESTED+dirty, branch `ce135-openbao-secret-zero-broker`) | auto |
| W8 | **#45 cockpit Slice-2** (BUILT, commit `0b22c7fb` branch `ce45-journey-cockpit-elevation`, worktree `/home/cedev2/ce-cockpit-seat`) — courier→GOVERNANCE review→wheel rebuild→merge | auto |
| W9 | **#119 impl build** — `tasks_handoff` validator check + `cev3 tasks bind` materialization (contract RATIFIED today, merged #286) | auto→PR |
| W10 | **#155 Web-A** read-only mirror + cockpit-serve→WS gateway (ADR-0008 merged #288) | auto→PR |
| W11 | **#151** rebase-aware/scoped re-review procedure (codify — kills the wheel-rebase churn tax) + **#148** seat-launch-from-unprovisioned-env fix | auto |
| G | **#156 Web-B** binding-act seam (separate governance review) · W4 topology decision | GATED |

## DAY-SHIFT RESULT (2026-06-20) — for the night log's "prior"
- **10 PRs merged today**: #275 OpenBao, #280 renames, #282 computer-use-envelope, #283 ADR-0007, #284 launcher (AM arc #144); **#285 playbooks, #286 tasks-contract, #287 website-v8.1, #288 ADR-0008, #289 auto-close-Action (PM high-gear)**.
- **17 ce-ops issues closed.** Cross-repo **auto-close Action is LIVE** (#289) — prevents pileup; manual close only needed for `fix(...)`-prefix commits (no explicit `Closes`).
- **Shared `creator-engine` GitHub App PUBLISHED + custody'd + verified** ([[ce-shared-app-published]]): PEM `/dev/shm/ce-shared-app.pem` (INTERIM tmpfs — re-place after reboot), config `~/.ce-keys/creator-engine-shared-app.env`, slug matches `SHARED_APP_SLUG` in v3_installer.py:1574.
- **First external brownfield test (arad/aradSmith, chmod735-dor/mythos)** — validated install+org-app+auth+plan, fail-closed safely (no GitHub writes), **stopped cleanly**. Findings → **#157** (shared-app backend, P0), **#158** (out-of-band trust anchor), **#159** (scanner provisioning, P0 — pins gathered+verified+posted), **#160** (Rulesets for free private repos). chmod735-dor is ce-overwatch-owned but CE_OVERWATCH_PAT is NOT scoped to it (404).
- Web-A/Web-B children filed (#155/#156). Tickets this session: #155-160.

## OPEN PRs (main=707e4406)
- **#290** Ring-1 §8c — REVIEW_REQUIRED, CI green, head `14447d6` (rebased+wheel-rebuilt). dev-1 reviewing → merge.
- **#281** OpenBao secret-zero broker — CHANGES_REQUESTED + dirty → W7 rework.

## ⚠️ LEARNINGS THIS SESSION (apply tonight)
- **Wheel-rebase serialization tax:** any 2 PRs that rebuild `validators/wheelhouse/*.whl` conflict; the 2nd must rebase + REBUILD after the 1st merges (route to the authoring dev, don't hand-merge the binary). Hit on #285/#290.
- **dismiss-stale does NOT fire on rebase force-push here** — an APPROVED PR keeps approval through a controller rebase (confirmed #286, #285). But strict-up-to-date means each merge makes the next PR BEHIND → rebase needed.
- **`decision_record` validator: `status: accepted` REQUIRES a `ratification` block** (`ratified_by` concrete handle ≠ decision_makers, `ratified_at`, `ratification_prompt_sha`, `quorum: n1_solo`). An agent CANNOT flip status to accepted without it (caught me on #288). Pattern = ADR-0001.
- **CI trigger gap:** force-push sometimes doesn't trigger validate.yml; if `check-runs==0` on the new SHA, `gh pr close && gh pr reopen` re-triggers.
- Reviews caught 6+ real bugs across the batch (incl. against the controller). The loop works — keep distinct-reviewer-before-merge inviolable.

## OPS
- **Watchers are session-bound — DEAD after /clear. RE-ARM on resume:** `bash ~/ce-fleet-watcher.sh` (run_in_background). It sources `~/.ce-keys/overwatch.env` for the gh token (`CE_OVERWATCH_PAT`).
- gh ops on this host: `source ~/.ce-keys/overwatch.env; export GH_TOKEN=$CE_OVERWATCH_PAT` (= ce-overwatch). Push via inline `https://x-access-token:$CE_OVERWATCH_PAT@github.com/...` — NEVER bake into config (scrub if --set-upstream did).
- Briefs on disk: `~/ce-briefs/` (ce290-review, ce-install.answers.yaml [arad], scanner pins in #159, etc.).
- dev quotas (codex shared GPT pool): ~11% weekly — Operator says fine, will x20 if hit.
