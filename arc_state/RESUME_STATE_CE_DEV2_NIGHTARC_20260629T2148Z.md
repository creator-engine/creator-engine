# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-SHIFT ARC — 2026-06-29 ~21:48Z

> NEWEST. Supersedes 2035Z. Open this + MEMORY.md FIRST. The arc's DEV WORK IS COMPLETE; two OPERATOR decisions remain (below). FULL AUTONOMOUS (G1–G5) still in effect.

## 🔴 AWAITING-OPERATOR (the only open items — surfaced via push earlier)
1. **CRITICAL — authorize `docs/llms-install.md` ce-root-v1 RE-SIGN.** PR #654 changed the spec, invalidating its SSHSIG; it shipped the placeholder `value: <RESIGN-REQUIRED-ce-root-v1>` to main + the LIVE published spec → the public installer fail-closes for EVERYONE (`signature_refused: not valid base64`). **Blocks Nitzan onboarding + pilot deploy.** Fix = re-sign with `~/.ce-keys/ce-root-v1` (the one non-delegable act; consequential public-trust-root → grant-gated, NOT done autonomously). Procedure [[ce-release-spec-signing-procedure]]: canonical bytes = whole file w/ `value:`+`content_sha256:` reset to placeholder → SSHSIG → insert → PR → merge → re-publish → re-run Nitzan e2e. **ON AUTHORIZATION: also FLIP the now-merged advisory install-sig guard (ce-ops#364 / PR #663) to a REQUIRED blocking gate.**
2. **ce-ops#363 approach decision** (Tranche-3 egress-proxy enforcement contract). Full architect design posted as a ce-ops#363 comment: **Option B** (bwrap `--unshare-net` + slirp4netns, kernel-level deny — recommended long-term) vs **Option C** (delegate to OpenShell when available — zero-new-code interim, lets Tranche-3 proceed now). ADR recommended. Decide approach → then dev-4 builds. (Tranche-3 stays safely fail-closed until then.)

## 🟢🎉 DELIVERED THIS ARC (headline: SUPPORT PILOT LIVE + RELEASE-GATE-VALIDATED)
`ce ask` answers real CE questions for real against live OpenRouter (gemini-2.5-flash-lite): real Q→cited answer, out-of-scope→refused, **zero-leak eval vs live backend RELEASE GATE PASSED 8/8, 0 leaks.** Wiring + validation in [[ce-support-pilot-live-validated]]. Merged: #656 Phase B, #657 zero-leak eval, #659 OpenRouter adapter, #661 Discord adapter (Phase C), #662 leak-parity (runtime==eval), #664 eval-corpus-expand (29 cases). Plus: #653 Tranche-2 (os-native scaffold, fail-closed), #658 broker-decouple (#357 pt1), #651/#652/#654/#655/#660 onboarding+installer fixes, #663 advisory install-sig guard (#364).
- **REMAINING to ship pilot to users:** persist the wiring (`CE_SUPPORT_AGENT_MODEL_CMD=python3 <repo>/tools/support-agent/openrouter_model_cmd.py`, `CE_OPENROUTER_API_KEY`←`OPENROUTER_API_KEY` in `~/.ce-keys/openrouter.env`, `CE_OPENROUTER_MODEL=google/gemini-2.5-flash-lite`) into the pilot deploy config; at VPS deploy move key→OpenBao.

## 🟣 BOARD: #663 + #664 APPROVED, settling → will be EMPTY. All dev PRs reviewed+gated (author≠approver, ce-dev-2 approves).

## 🔵 SEATS: dev-1 / dev-3 / dev-4 ALL IDLE at the Operator-gated boundary — NO clean ungated lane (do not make-work). Re-feed when: re-sign lands (dev-1 → re-run Nitzan e2e + flip guard to blocking; PINNED_KEYS single-source follow-up), OR #363 decided (dev-4 → build Option B or C), OR pilot-deploy greenlit (dev-3 → persist wiring; Slack/Phase E).

## 🩺 INFRA
- Brain `vllm-qwen3-embed` :8989 keeps getting GRACEFULLY STOPPED (~hourly; RAM ~112/121Gi) — auto-restart monitor `bjix4hjth` self-heals (restart on inactive/failed×2, ignores activating). INVESTIGATE recurring-stop cause (memory pressure? periodic job?).
- Daemon 43010 ALIVE (1d05h). Watchers: board b9aipnn3b+bh8s12igt, seat bs2rmjt2y+bxa44s2dn, brain bjix4hjth. Crons :00/:05/:30/:47. ~210 stale git worktrees accumulated (bulk-prune someday).
- HARVEST GOTCHAS [[ce-harvest-carrier-slug-must-match-branch]]: carrier stem==branch_slug(pushed head); `carrier_gen.write_carriers` omits work-class line; contained seats have STALE local origin/main (rebase onto current main + resolve; watch SEMANTIC drift not just textual — e.g. #664's test encoded pre-#662 mechanics).

## 🎟️ TICKETS this arc: ce-ops#357 (broker decouple, DONE #658) · #358 (installer, DONE #654) · #359 (onboard doctor, DONE #651) · #360 (support agent — pilot LIVE) · #361 (0.2.0 mirror immutability policy) · #362 (leak-parity, DONE #662) · #363 (egress contract — DESIGN POSTED, Operator decision) · #364 (install-sig guard, advisory DONE #663, flip-to-blocking after re-sign).

## ON RESUME
1. Read this + MEMORY. 2. **Did Operator authorize the re-sign?** If yes → execute re-sign → flip #663 guard to blocking → re-run Nitzan e2e → mark handoff-ready. 3. **Did Operator decide #363?** If yes → dispatch dev-4 to build Option B/C. 4. `gh pr list` (expect empty; #663/#664 merged). 5. Verify daemon + brain :8989 + watchers. 6. If pilot-deploy greenlit → persist support wiring. 7. Re-feed seats ONLY with ungated lanes; else hold (no make-work). Surface RESERVED/blockers; else drive.
