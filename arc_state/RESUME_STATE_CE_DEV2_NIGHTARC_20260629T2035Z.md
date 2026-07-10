# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-SHIFT ARC — 2026-06-29 ~20:35Z

> NEWEST. Supersedes 1910Z. Open this + MEMORY.md FIRST. Night-arc = balanced completion + arming + scaling, FULL AUTONOMOUS (G1–G5); surface RESERVED/hard-blockers; checkpoint for morning. Author≠approver always.

## 🔴 AWAITING-OPERATOR — CRITICAL (surfaced via push 20:35Z)
**PUBLIC INSTALLER IS BROKEN — blocks ALL onboarding incl Nitzan.** PR #654 (installer uv trust) changed `docs/llms-install.md`, invalidating its ce-root-v1 SSHSIG; the signature block was left as placeholder `value: <RESIGN-REQUIRED-ce-root-v1>`. This is on main AND the LIVE published spec → the one-liner fail-closes for everyone: `INSTALL_REFUSED signature_refused: signature value is not valid base64`. (Confirmed by dev-1 fresh-container e2e; earlier F5/RED-G-4 checks used the local venv so they MISSED it.)
- **FIX = re-sign `docs/llms-install.md` with ce-root-v1** (`~/.ce-keys/ce-root-v1{,.pass,.pub}` — the ONE non-delegable act) + re-publish. Procedure [[ce-release-spec-signing-procedure]]: canonical bytes = whole file with `value:`/`content_sha256:` reset to placeholder; sign SSHSIG; insert. Re-signing the public trust root is consequential + historically ratification-gated → **AWAITING OPERATOR AUTHORIZATION.** On their go: stage canonical bytes → sign → PR → merge → re-publish → re-run e2e.
- CI-guard ticket filed (block merge if llms-install.md has placeholder/invalid signature) so this can't recur.

## 🟢🎉 SUPPORT PILOT IS LIVE + RELEASE-GATE-VALIDATED (headline milestone)
`ce ask` answers for real against the live OpenRouter backend. Merged this arc: Phase B (#656), zero-leak eval (#657), OpenRouter adapter (#659). Controller wiring + validation evidence in memory [[ce-support-pilot-live-validated]]. Zero-leak eval vs live backend: **RELEASE GATE PASSED — 8/8, 0 leaks (4 answered-with-citation, 4 leak-probes refused).** Wiring: `CE_SUPPORT_AGENT_MODEL_CMD=python3 <repo>/tools/support-agent/openrouter_model_cmd.py`, `CE_OPENROUTER_API_KEY`←`OPENROUTER_API_KEY` in `~/.ce-keys/openrouter.env`, `CE_OPENROUTER_MODEL=google/gemini-2.5-flash-lite`. REMAINING: persist this wiring into the pilot deploy config so `ce ask` works out-of-box for users; ce-ops#362 hardening (runtime leak filter laxer than eval).

## 🟣 BOARD / GATE
- **#660** docs onboarding-order fix (dev-1, docs-class) → reviewer `a54077f8` running → approve as ce-dev-2 → Surface-A/daemon merges. (Does NOT fix the install blocker.)
- Merged this session: #651,#652,#654,#655,#656,#657,#658,#659. (Note #654 caused the install-spec break above.)

## 🔵 SEATS
- **dev-1** (VPS, self-push) → just finished Nitzan e2e (found the install blocker + #660). Now FREE; its onboarding lane is PAUSED pending the re-sign. Re-feed when re-sign lands (re-run full e2e) or give a disjoint lane.
- **dev-3** (ce-vps-codex) → Phase C Discord adapter DONE → harvesting (worker `a86302e8` → PR `ce-supportagent-discord-adapter`). Then free.
- **dev-4** (ce-dgx-codex) → ce-ops#362 leak-parity: work done but committed on an ephemeral `worktree-agent-*` branch off STALE local main (no-egress) — asked it via herdr to emit a clean bundle `/var/tmp/harvest-out/leak362.bundle` + report branch/HEAD. Harvest must rebase onto current origin/main (may conflict w/ #657's support_eval). NON-URGENT (pilot already passes zero-leak live).

## 🩺 INFRA
- Brain `vllm-qwen3-embed` :8989 keeps getting GRACEFULLY STOPPED (~17:47, ~19:38; RAM 112/121Gi) — auto-restart monitor `bjix4hjth` (restart on inactive/failed, 2 consecutive; ignores activating). Investigate the recurring-stop cause.
- Daemon 43010 ALIVE. Watchers: board b9aipnn3b+bh8s12igt, seat bs2rmjt2y+bxa44s2dn, brain bjix4hjth. Crons :00/:05/:30/:47.
- HARVEST GOTCHAS [[ce-harvest-carrier-slug-must-match-branch]]: carrier stem==branch_slug(pushed head); `carrier_gen.write_carriers` omits work-class line (re-add). Contained seats have STALE local origin/main (no-egress) — harvest must rebase onto current origin/main.

## 🎟️ TICKETS this session: ce-ops#357–363 (+ the CI-guard one filing now).

## ON RESUME
1. Read this + MEMORY. 2. **CHECK: did Operator authorize the install re-sign?** If yes → execute re-sign procedure → restore installer → re-run Nitzan e2e. 3. `gh pr list` reconcile (#660 merged? Discord PR? #362?). 4. Verify daemon + brain :8989 (re-died?) + watchers. 5. Review+gate PRs (approve as ce-dev-2). 6. Keep seats fed; NEVER inline. 7. Persist support-pilot wiring for users once install is unblocked. Surface RESERVED/blockers; else drive.
