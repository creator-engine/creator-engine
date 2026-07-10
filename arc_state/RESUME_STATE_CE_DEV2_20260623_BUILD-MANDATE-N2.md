# RESUME STATE — CE-DEV-2 · 2026-06-23 · 🏗️ DRIVE BUILD MANDATE N2 (M2 visibility gateway + governed onboarding)

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** the N1 night-arc resume (N1 = fleet conversion, COMPLETE). **READ THIS + MEMORY.md FIRST** — esp. [[ce-visibility-channel-emission-model]], [[ce-agent-pointed-install-model]], [[ce-cockpit-frontend-agnostic-core]]. origin/main ≈ `10dc9226`+.

## 🟢 THE GO (Operator 2026-06-23)
**Build Mandate N2 SIGNED OFF as written** → `.ce/state/research/BUILD_MANDATE_N2_M2_ONBOARD.md`. Drive Wave 1 autonomously, worker-driven, fleet on clean installs, controller holds merge gate; halt at escalation lines.
**🔑 Operator directive: the CONTROLLER (cedev2 — strongest reasoning + on the DGX) DRIVES THE HARDEST TASKS via its OWN workers** (A1 attachable-session substrate first); route lighter work (A2 additive, B mechanical PRs, W6 hygiene) to the fleet seats.

## 🔴 WAVE 1 LIVE STATUS (2026-06-23 ~04:45Z — UPDATE EACH CHECKPOINT)
All 5 Wave-1 PRs OPEN. Controller holds merge gate; route independent (non-author) review; merge on APPROVED+green (R1, G-B).
- **#368** A1 PTY attachable-session substrate (W2′, MINE) — 16 files, +884; work-class fixed→`feature`; CI re-running. Foundational. Review → dev-3 (best ctx) when free.
- **#364** A2 channel-emission webhook sink (MINE) — GREEN ✅; **review ASSIGNED → dev-1**. Redaction guardrail met (2 secret-leak tests). Scope-2 (run-outcome/spend report-fold) DEFERRED = queue as small follow-up.
- **#367** PR-1 `ce verify-install` (dev-1) — GREEN ✅; review → dev-4 (non-author) when free.
- **#366** PR-2 install.sh robustness (dev-3) — CI FAIL (REAL: `test_install_bootstrap.py:268` artifact_hash_mismatch from install.sh edit). dev-3 fixing (fanned sub-worker). Guardrail sent.
- **#365** PR-3 profile-path (dev-4) — CI FAIL (`test_e2e_real_sshsig` sig-verify). dev-4 iterating+repushed. Guardrail sent.
- **🚨 GOVERNANCE GUARDRAIL sent to dev-3+dev-4:** do NOT modify/regenerate SIGNED TRUST ARTIFACTS (docs/llms-install.md, docs/keys/ce-root-v1, production SHA256SUMS, docs/downloads/*) to pass a test — re-signing is controller-gated escalation. Watch their next push for trust-artifact diffs.
- **Footgun learned** [[ce-pr-work-class-line-format]]: work-class line = bare token, no parenthetical. Fixed at gate on #364/#368.
- **Seat ctx watch:** dev-1 81% / dev-4 78% (high, may auto-compact) · dev-3 16% (room → give it the heavy #368 review).

## ✅ N1 DONE (context)
Fleet conversion COMPLETE — dev-4/dev-3/dev-1 all on clean signed 0.2.0, governed, acceptance-proven (#355/#357/#358 merged). Fleet in autonomous governed pickup. W4 #207-W1 (#356 VisibilityBackend registry seam) MERGED. main @ `10dc9226`+.

## 📐 RATIFIED DESIGN BASIS (resolved 2026-06-23 — memories + design docs are authoritative)
- **Visibility** [[ce-visibility-channel-emission-model]]: contract = read-model emission from AUTHORITATIVE governance/lifecycle events (NOT screen-scrape, herdr guardrail). Headless OK incl **CONTROLLERS** (read-model/channel/attach-visible, not dark; C4 refuses *dark* `--print` only). Default INVERTS: headless-baseline + opt-in attach. No auto-degrade. **ATTACH:** CE owns a **PTY-master session per agent** (herdr-shaped, replaces tmux) → read-model emission AND interactive attach (read+write) from ONE session; Dev-Mode = attach-all default + always-available option. Governance preserved (acts hit Ring-1 regardless of who types; attach CE-mediated+audited).
- **Install** [[ce-agent-pointed-install-model]]: agent-driven install first-class + GOVERNED (auto verify-trust + confirm-on-consequence×novelty×irreversibility + emit-audit). 3 modes: agent-pointed (PRIMARY/novel) / guided one-liner / hybrid hand-off. **hybrid = default when agent present** (Operator-approved). Handoff-confirmation INHERITS the user's permission mode (trusting→no prompt; cautious→ONE friendly mom-test confirmation-of-fact); security machine-side (carry-verified-artifacts + safe discovery). print = manual fallback. D4 profile-PATH default-on managed block; D5 classify new modules `v1`.

## 🏗️ MANDATE + DESIGN DOCS (`.ce/state/research/`)
- **BUILD_MANDATE_N2_M2_ONBOARD.md** — signed; grants **G-A** (worker fan-out, #208→dev-4) **G-B** (auto-merge on independent-review+green, R1) **G-C** (governed-install authority).
- **DESIGN_207_VISIBILITY_BACKEND.md** (REVISED — attachable-session substrate). Baseline PR-units: W1 registry (MERGED #356) → **W2′ PTY-session backend + C1/C3** → **W2-sec redaction/leak gate** → W4 teardown (close PTY/socket). Trailing: T1 control-socket+NDJSON · T2 cockpit attach-UI · T3 controller-C4 token + `ce launch` · T4 container-attach. `ce lane attach` rides existing `lane` group (no docs-reconciliation trip). W2′ touches wheel → rebuild + re-pin SHA256SUMS.
- **DESIGN_197_CE_ONBOARD.md** (REVISED — 3-mode governed install). 7 PR-units: PR-1 `ce verify-install` → PR-2 install.sh robustness (TMPDIR fallback + install-lock UX) → PR-3 profile-PATH writer (default-on + `--no-fix-path`) → PR-4 programmatic init/brain-init + doctor probes → PR-5 `ce onboard` orchestrator + `--emit-manifest` → PR-6 launcher resolve-harness/refuse-before-spawn + lifecycle-reconcile (**the #212 fix**) → PR-7 install.sh hybrid hand-off.
- **DESIGN_207B_READMODEL_COVERAGE.md** + **RESEARCH_HERDR_AGENT_MULTIPLEXER.md** (references).

## 🌊 BUILD SEQUENCE
- **WAVE 1 (now, parallel):**
  - **A1 — CONTROLLER drives** (hardest, MY own workers, isolated worktrees on DGX): W2′ PTY-session backend → W2-sec redaction/leak gate → W4 teardown.
  - **A2 — fleet/own** (the 95% surface, additive on `runner/notify_feed.py`): first-class `kind: webhook` sink + fold run-outcomes/spend into notify events for periodic reports/status (contact-on-need → Discord/Slack/NanoClaw).
  - **B — fleet** (7 onboard PR-units, DESIGN_197).
  - Each PR: strict-TDD · path-manifest carrier · changelog fragment · `- **Declared work class:** <…>` body line · `_versions.py` classify new modules `v1` · independent cross-review · merge on APPROVED+green (R1). **NEW live-work surfaces (W2-sec, attach stream, any log/transcript) = redaction gate + secret-leak test MANDATORY (escalation if a unit can't meet it).**
- **WAVE 2 (staged, Operator reachable):** A3 (cockpit attach-UI + controller-C4 + multi-attach write-lock) → A4 (#208 container image + container-attach). GATED on E-att escalations.
- **TRACK C (opportunistic):** #209 merge-queue flake · land #362 (rebase) / #351 (resolve already-merged-via-#300 vs divergent drain-Q FIRST) / #337 · gap tickets #212/#213/#214 · **ce-ops#215 seat-side read-only ce-ops checkout** (design docs now durable in private ce-ops/designs/ + mandates/ via fixed sync-ops.sh; #215 = wire seat read access so briefs point-not-embed) · #349 (⏸️ Operator visual-check).

## ⏸️ ESCALATION LINES
M2-arch beyond #207/#208 incl **E-att-1** PTY-into-sandbox mechanism · **E-att-2** socket reachability across container boundary + secret surface · **E-att-3** multi-attach write-lock arbitration · **E-att-4** replay/scrollback buffer size + persistence default (secret-aware, default OFF). · **redaction-gate + secret-leak test on EVERY new live-work surface** (non-negotiable) · **ungoverned install** · version bump / new external publish · **#349 live-site / web-design visual-checkpoint** (Operator) · Arad/chmod735 (postponed 27 Jun).

## 🖥️ FLEET / REACH / MECHANICS
- dev-4 = `ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux `dev4stage1:0.0`) · dev-3 = `ssh dev3` (tmux `dev3-onboard:0.0` %66) · dev-1 = `ssh dev1` (tmux `ce-dev1-orchestrator` `controller` win). All on clean `ce 0.2.0`, gpt-5.5 **high**, autonomous governed pickup.
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Merge queue: `gh pr merge <n> --auto` (queue sets strategy; "already queued" = enqueued; monitor + re-enqueue on #209 merge_group flake). main protection: 1 independent (non-author) review + green CI. ISSUES = creator-engine/ce-ops; CODE/PRs = creator-engine/creator-engine.
- Sign release (if needed — escalate version bumps): ce-root-v1 key `~/.ce-keys/ce-root-v1`(+.pass), askpass `/tmp/ce_askpass.sh`. CF DNS token `~/.ce-keys/cloudflare.env`.
- HELD/OPEN PRs: #349 (⏸️ Operator visual-check, live-site `docs/index.html`) · #362 (rebase, conflict w/ merged #360) · #351 (drain-Q) · #337 (rebase).
- N1 heartbeat cron (dc4cb55f) DELETED (was N1-specific). Re-arm a build-appropriate monitor if wanted.

## 📋 NEXT-SESSION FIRST ACTIONS (fresh context)
1. **Dispatch WAVE 1** — (a) CONTROLLER-driven A1: spawn my own worker(s) in isolated worktree for W2′ PTY-session backend (hardest) + W2-sec redaction gate; (b) A2 channel-emission → a fleet seat or own worker; (c) B onboard PR-units → fleet seats. Stock the belt; don't single-thread.
2. Route each PR to an independent non-author reviewer; merge on APPROVED+green (R1); hold the gate.
3. Checkpoint + resume-write at each unit boundary; dual-write CE-DEV-1.
4. Wave 2 (A3→A4) ONLY with Operator reachable; surface E-att escalations before any #208 substrate decision.
