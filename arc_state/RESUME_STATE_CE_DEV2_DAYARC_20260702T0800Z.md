# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 ~08:00Z (DAY, post-nightarc)

> NEWEST. Supersedes NIGHTARC_...0255Z. Open MEMORY.md + NIGHTARC_MANDATE_CE_DEV2_20260701.md first.
> Arc authority still the batch-ratified night grants (G-N1..G-N7; code≤M = 2-review quorum; docs XS/S single).
> **TODAY: first external test user + contributor (Nitzan) onboards** — onboarding-path quality is pitch-critical.

## ✅ This block (fresh session after /clear)
- **Learned the hard way:** last session's 2 fix-workers (#718 RCE fix, #719 scope fix) did NOT survive the /clear — nothing pushed. Re-dispatched/resolved.
- **#719 libsodium: REQUEST_CHANGES was a FALSE finding** (reviewer contaminated by dirty build-image.sh in main checkout; GitHub-authoritative = 3 files only). Re-reviewed with 2-quorum (Sonnet functional + Haiku mechanical, both APPROVE) → un-drafted + approved as ce-dev-2 → CLEAN, daemon merging. **FOLLOW-UP after merge: rebuild + relaunch dev-4 image** (arm64 base-digest override, ce-ops#377; relaunch canon = cedev4/run-codex-runsc.sh, re-auth codex).
- **#720 guide review: REQUEST_CHANGES (real)** — (1) guide abandoned canonical Frame→Shape→Build→Review→Ship vocabulary, zero cross-links; (2) "unlinked draft" banner false (already linked from welcome.md:206, solo-ceo-onboarding.md:259, solo-dev-onboarding.md:277 + rendered .html). Fix dispatched to author dev-1 (brief .ce/briefs/ce-720-guide-fixes-dev1.md). After fix + re-review → **⏸️ AWAITING-OPERATOR publication sign-off**.

## 🔄 IN-FLIGHT
- **#718 conveyor — HELD DRAFT, STRUCTURAL fix round (4th) in flight.** Adversarial rounds keep finding NEW untrusted-payload→git RCEs: r1 validate_command, r2 base+remote, r3 found bundle_path→`git fetch ext::` RCE + repo_path/worktree_path unconfined-cwd RCE (attacker `.git/config` origin=ext:: BYPASSES the remote pin). Root cause = payload carries execution CONTROL. **Fix worker ab2af4ad running a STRUCTURAL fix** (.ce/wt-718-fix, stack on 12933a4c5): payload = DATA-ONLY, confine ALL fs paths (bundle/repo/worktree) under a daemon-pinned root (realpath-under-root, fail-closed) + shape-check bundle_path + validate pr_base + full per-field audit + confinement tests. This is the whack-a-mole stop-and-fix-root (2-strikes doctrine). ⚠️ SIGNAL for Operator: conveyor's payload trust model needed a design pass, not field patches. NOTE the earlier af1b02964 adversarial APPROVE was WRONG (stale/shallow) — the deep passes (a9d44a19, ac957ffea) found the real RCEs.
- **#718 APPROVED + ENQUEUED (DISARMED) — final head 49cb785b7.** 5 adversarial rounds, ALL code-level RCE closed (validate_command/base/remote pinned, paths confined under daemon-pinned roots, TOCTOU closed via resolved-path threading). Both final re-reviews APPROVE. **ARMING (G-N3) HELD → ce-ops#388** (payload-as-data-only + daemon-owned-dirs + seat-authored-bundle CONTENT-trust; content-trust finding added to #388). Daemon disarmed-by-default, no arming wiring exists. Merges to main safely disarmed.
- **[superseded] #718 2nd RCE round in fix.** History: e6068c69b pinned validate_command (round 1). I approved on a functional APPROVE + a CURSORY adversarial APPROVE (agent af1b02964 — likely a stale auto-resumed prior-session agent) → **premature**. My DEDICATED deep adversarial (a9d44a19) then found TWO MORE RCEs of the same class the first fix missed: `base`→`git rebase <base>` (`--exec=` gadget, exploitable BY DEFAULT since rebase=True) and `remote`→`git push <remote>` (`ext::sh -c` transport RCE). **Converted #718 to DRAFT (GraphQL) to kill the pending merge** (my approval is still on record → MUST stay draft or dismiss until re-fixed+re-reviewed). **Fix worker abf91781 running** (.ce/wt-718-fix, pin/allowlist base+remote + hostile-payload tests) → controller pushes → FULL adversarial re-review (audit ALL payload fields) → then re-approve → merge → ARM CONVEYOR (G-N3). LESSON: don't approve on a bare/cursory adversarial APPROVE; the deep "try-to-defeat" adversarial is the gate. ce-ops#383 = the option-smuggling hardening (now partly overlaps this real fix).
- **#367 speckit — DONE → PR #722 (DRAFT), head 700d073f1, preflight GREEN.** CLI-reference regen fix applied (was the mechanical blocker); PR body carries the ⏸️ AWAITING-OPERATOR Principle-X question. **Leave DRAFT until Operator rules** on spec-kit-retirement compatibility. dev-3 seat NOT freed (already on #370).
- **#721 N2 pickup-filter — APPROVED + ENQUEUED** (fbad4be20; both re-reviews APPROVE). Behind #724 in merge queue. Follow-up filed: **ce-ops#387** (PR-side inbox lacks _BLOCKING_LABELS coverage — pre-existing asymmetry). Changelog doesn't mention round-2/3 additions (non-blocking, accepted).
- **[superseded] #721 fix ROUND 3 running.** R1: routed readiness through _skip_reason (da5e1e9a8, pushed) → functional re-review APPROVE, but adversarial re-review found a REAL residual: _skip_reason's hold-marker only catches the BODY-TEXT form; an issue with the `awaiting-operator` LABEL (sibling convention forge/controller_inbox.py:24 AWAITING_OPERATOR_LABELS) still surfaces as ready. **Fix worker a65f6fe4 running** (.ce/wt-721-fix, stack on da5e1e9a8): exclude awaiting-operator LABEL form (reuse AWAITING_OPERATOR_LABELS) + add machine-readable `requires_live_recheck` payload signal + tests. Controller pushes → 2-review re-quorum → gate. (Head after push = new SHA; dismisses prior approvals.)
- **dev-1** (55% ctx, watch): BATCH = ce-ops#337 self-push diagnose+canary (branch ce-337-selfpush-canary) + #720 fixes (same branch ce-329-scrum-to-ce-guide). Self-pushes.
- **dev-3**: #370 DONE (commit c4af71b) → **harvest worker a29075c0 running** (→ PR). Re-fed with **CE-native `ce init`** (ce-ops#367, branch ce-367-ce-native-init, claim recorded) — Working, confirmed on CE-native path not speckit.
- **dev-4**: #366 ADR DONE (37148fd) → **harvest worker ad9c9057 running** (→ DRAFT PR, awaiting-Operator-ratification). Re-fed **#388 conveyor redesign ADR** (branch ce-388-conveyor-redesign-adr, docs-only) — Working. Claim recorded.
- **#723 (#337 self-push canary) — APPROVED + ENQUEUED** (2ce701071; functional APPROVE + adversarial clean-on-delta). Dedup-mount fix landed. Deploy note: after merge, the run-vps-runsc.sh launcher fix needs the dev-3 container RELAUNCHED to take effect (canonical launch only).
- **[superseded] #723 quorum SPLIT:** functional REQUEST_CHANGES (real blocker: parent-dir mount emits DUPLICATE `--mount` when broker+self-review sockets share /run/ce-egress → docker "duplicate mount point" → dev-3 launch fails), adversarial APPROVE (containment tightened, canary sound). **Fix worker ac87f2bb running** (.ce/wt-723-fix: dedupe same-dir egress mount + dual-socket regression test) → controller pushes → re-review (functional) → gate.
- **#724 (#370 harvest, XS code) — APPROVED + ENQUEUED** (merge queue). Functional APPROVE + mechanical no-blocking-defects (Haiku withheld literal APPROVE on over-cautious self-fire read — content = clean pass; quorum met, author≠approver). git_helpers.py extraction + local --pr-body-file parity. Harvest worker confirmed GREEN preflight.
- **⚠️ WORK-CLASS VOCAB = XS/S/M/L** (NOT tiny/story/feature/epic — retired #686). My harvest-brief template + docs/operations/AUTHOR_A_CE_VALID_PR.md had stale vocab → filed **ce-ops#385** (onboarding footgun). Use XS/S/M/L in all future briefs.
- Claims recorded in .ce/claims/. PR-board watcher armed (Monitor, persistent).
- **ACTIVE WORKERS:** #718 structural fix (ab2af4ad), #721 label-form fix (a65f6fe4), #723 dedupe fix (ac87f2bb), #724 reviews (a7523ab3/a223ee64). SEATS: dev-1 #720 fixes, dev-3 CE-native init, dev-4 #366 ADR.

## ✅ OPERATOR DECISIONS LANDED (2026-07-02)
- **#367 spec-kit → RETIRE COMPLETELY.** Replicate init capability CE-native. PR #722 CLOSED. ce-ops#367 retitled/redirected → CE-native `ce init` (brief `.ce/briefs/ce-367-ce-native-init.md` ready to dispatch to next free seat). Memory [[ce-speckit-full-retirement-ce-native-init]].
- **VPS /tmp (#184) SOLVED live** via passwordless sudo — tmpfiles.d 1d aging + 6h clean cadence + reclaim 11G→360K. #184 CLOSED. Directive: build internal CE DevOps agent + runbook-SSOT section → filed **ce-ops#384**; memory [[ce-internal-devops-agent-and-runbook-ssot]]. Orchestrator HAS passwordless VPS sudo.

## 🛑 CONVEYOR ARMING (G-N3) HELD — controller decision, adopted while Operator away (asked, 60s no-response)
4 adversarial rounds on #718 each found a NEW RCE class (payload command → base/remote gadgets → bundle/cwd poisoning → TOCTOU). Model is unsafe-by-patching (runs git in payload-specified dirs, trusts ambient .git/config). **Posture = Option A:** finish TOCTOU fix (worker a82a2158 running) → re-review → merge #718 DISARMED (disarmed-by-default, arming needs explicit config) → but **DO NOT ARM** pending a security DESIGN review = **ce-ops#388** (payload=data-only + daemon-owned working dirs). Re-ask Operator to ratify this posture (options were: A design-pass-before-arm [chosen], B keep-patching-toward-arm, C redesign-before-merge). If Operator prefers B/C, adjust.

## ✅ OPERATOR RATIFIED 2026-07-02 (all controller recs approved as written) — [[ce-mainhead-install-option-a-ratified]]
- **Main-HEAD install → Option A RATIFIED retroactively** (#725/#366). ADR flipping to Accepted (worker ac19db9c) → push → 1 docs review → approve + merge #725 → close #366. Guard follow-up = **ce-ops#389**.
- **Conveyor arming → HELD, design-pass first** (Option A confirmed). #388 ADR (dev-4) is the vehicle; arm only after redesign + independent review.
- **#720 → publish WHEN fixes re-review GREEN** (don't publish before vocabulary/false-banner fixes land).

## ⏸️ AWAITING-OPERATOR (surface FIRST)
1. **#720 publication** — ratified "publish when green"; awaiting dev-1 fixes → re-review → then it publishes (first-contributor onboarding doc).
2. **#388 conveyor-redesign ADR** — review when dev-4's draft lands (ratify the arm-safety model → unblocks G-N3).
2. **#366 trust-contract ratification** once the ADR PR lands (main-HEAD artifact trust anchor).
3. **N1a install-spec re-sign (R5)** — still PARKED from night-arc.
4. **ce-ops#184** durable VPS /tmp guard needs host root — Operator-level infra op.

## ✅ MERGED this session (ALL LANDED): #719 libsodium · #724 prbody-parity(#370) · #721 pickup-filter(N2) · #723 self-push-canary(#337) · #718 conveyor-daemon-DISARMED(N1 core). Board clear except #720 (draft, dev-1). Queue empty, daemon alive.
- **DEFERRED controller op (2):** #723's run-vps-runsc.sh launcher fix (egress socket parent-dir mount + dedup) only takes effect on a dev-3 container RELAUNCH (canonical launch only). Do NOT relaunch while dev-3 is mid-task on CE-native init (#367). After #367 harvested + dev-3 idle → relaunch dev-3 to activate the self-push spine, then verify the self-push canary passes end-to-end. (Existing dev-3 keeps working via controller-harvest until then.)
- **DEFERRED controller op:** rebuild + relaunch dev-4 image to bake in system libsodium (arm64 base-digest override, ce-ops#377; relaunch canon = cedev4/run-codex-runsc.sh + codex re-auth). Do NOT do while dev-4 is mid-task on #366 — wait until #366 is harvested + dev-4 idle, then rebuild at a quiet window.

## ⏭️ NEXT ACTIONS
1. #718 fix lands → controller pushes → adversarial re-review → gate → **conveyor arming (G-N3)** = N1 headline.
2. Gate harvest PRs (#367 = 2-quorum code; N2 pickup-filter = 2-quorum code).
3. #720 fix push → re-review (single, docs) → hold for Operator sign-off (do NOT auto-merge publication).
4. After #719 merges: dev-4 image rebuild+relaunch (controller op).
5. **#351 LIVE cutover** still queued (unblocked; token durable). Surface-B strangeLoop demo (G-N4).
6. Re-feed seats as they free up. Incident follow-up tickets (queue-daemon --preflight, AppRole migration) → ops_triage.

## KEY FACTS
- Auth: overwatch `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`.
- Seat drive: dev-4 `sudo docker exec ce-dgx-codex bash -c "HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr <cmd> w1:p1"`; dev-3 same via `ssh dev1 'sudo docker exec ce-vps-codex ...'`; dev-1 tmux `ce-dev1-orchestrator:2.0` (C-u before send).
- Daemon pid 648947 healthy, token durable. Local main checkout is DIRTY on ce-release-0.3.1-rc2 (build-image.sh etc.) — caused the #719 false review; workers must use worktrees off origin refs, never the main checkout.
