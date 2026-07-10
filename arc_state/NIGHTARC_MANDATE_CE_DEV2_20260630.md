# 🌙 NIGHT-ARC MANDATE — CE-DEV-2 Orchestrator — 2026-06-30 (night)

> Follows the day-shift arc (RATIFIED G1–G7). Resume anchor for the night shift. Standing authority carries over: G1–G7 + R1 (canary go-live, Option A) + R5 (install-spec re-sign, authorized 2026-06-30). Drive via workers, never inline (signing is the controller's non-delegable act).

## Thesis
Land **onboarding go-live (Nitzan)** + a **presentable public docs surface**, **finish the automation** (the headline "seats autonomy + forge autonomy" scale-up that's built-but-not-armed or not-started), and close release-hygiene gaps — all **protecting the 01-Jul NVIDIA pitch path** (nothing may break the live install/demo before the pitch).

## N0 — OPENING AUTOMATION-COMPLETENESS AUDIT (do FIRST)
Dispatch a recon/architect pass that maps EVERY automation lane → built / partial / not-started + the exact finish-step + the file/PR evidence. Drive the night from this VERIFIED inventory, not memory. Cover at least the lanes in N2 below. Output a table the controller works from. (Rationale: both Operator and controller were unsure of exact completion state — ground it.)

## N1 — Onboarding go-live (HIGHEST, pitch-critical, time-boxed)
- **N1a — Install-spec re-sign (PARKED R5 act, resume first):** worktree `.ce/wt-resign-llms` (branch `origin/ce-L1-install-doc-fix`, HEAD `10f824a5`). Canonical bytes sha256 = **`865ba4f46acaeb999064ecf9d719e22c216ffa5f75f96b93c0ee50c76122820e`** (reproducible: `v3_installer.canonical_spec_bytes(doc_bytes)` — VERIFIED matches dev-1). Steps: write canonical → `ssh-keygen -Y sign -f ~/.ce-keys/ce-root-v1 -I ce-root-v1 -n ce-spec-v1 - < canonical > sig` (passphrase via SSH_ASKPASS feeding `~/.ce-keys/ce-root-v1.pass`, 32 bytes) → embed `value=base64(sig)` + `content_sha256=865ba4f4…` via `release_publish._replace_field` (canonical-ization strips value+content_sha256 → embedding does NOT change canonical) → verify (`ce verify-install` + install-spec guard + `ssh-keygen -Y verify` vs `~/.ce-keys/ce-root-v1.pub`) green → ship to main (independent review + ce-dev-2 approve). SHOW Operator the diff before merge.
- **N1b — LIVE redeploy (the actual unblock):** main==live==0.3.1 already (NOT drift — earlier "0.3.0 behind" was a stale-rc2-checkout misread). After re-sign lands on main, redeploy `creator-engine.dev/llms-install.md` to the fixed spec. **Deploy mechanism UNKNOWN** — no Pages/deploy workflow in `.github/workflows`; INVESTIGATE how creator-engine.dev serves `docs/` first.
- **N1c — Re-run clean-room e2e** vs the redeployed live spec → confirm GREEN end-to-end (dev-1; it found the blocker, has context).
- **N1d — Bootstrap ssh-keygen preflight** — `docs/install.sh` already has a Debian/Ubuntu remediation; expose it earlier / add an actionable "install openssh-client" error for §0 manual path.
- **N1e — Contributor path (R4, needs Operator):** Nitzan's GitHub handle + scope (outside-collaborator vs org-member; repos; push-branch vs fork-only) to wire/verify clone→ticket→governed-implement→PR.

## N1.5 — Render public docs (PITCH-CRITICAL)
The website `#docs` has **1 rendered HTML page (what-is-creator-engine.html, #689) + 7 RAW `.md` links** served as `text/markdown` (browser downloads/shows source — poor look for NVIDIA). Root cause = #37 portal vanished (no promotion mechanism; the L10/#376 gap). **Render the 6 human-facing docs to HTML** matching the what-is-CE page (understanding-ce, pilot-runbook, contributing-to-ce, solo-dev-onboarding, solo-ceo-onboarding, SECURITY_MODEL); fix raw relative `.md` cross-links (e.g. `../architecture/stage-vocabulary.md`); apply public-docs product-lens scrub. **KEEP `llms-install.md` as machine `.md`** (the agent-fetched signed spec). This is #37 pulled forward to a pre-pitch slice. Owner: seat + reviewer.

## N2 — AUTOMATION COMPLETION (the elevated headline thread — drive from N0 audit)
- **Auto-merge canary (L2):** GO-LIVE (Option A authorized) — harvest L2 (PR opening) → SAFETY review (disarmed-default, kill-switch, envelope docs+XS/S only, author≠approver, no-self-arm, the new `reviewDecision==APPROVED` guard) → CI green → approve→merge = **docs-class auto-merge LIVE**. Spot-check first real auto-merge + audit. Rollback = `CE_AUTOMERGE_KILL_SWITCH=true`. P1: `ce automerge kill-switch` CLI, single-PR mechanical gate. [[ce-l2-automerge-golive-decision]]
- **Autonomous review/approve (Surface B / AutoReview run_mode):** broker `--run-mode` is CODED but the live broker (dev-3) runs WITHOUT it → autonomous APPROVE not live. Governed deploy/arming of run-mode (R1-class — Operator-gated flip after build+verify).
- **Forge triage (L3):** P0 merged (#692) runs DRY-RUN only. Enable apply-mode: post the **ce-ops#67 sentinel comment** (`<!-- ce-triage-queue-issue:v1 -->`) + flip cron to apply (or workflow_dispatch first run). P1: lane-config YAML, auto-labeling, webhook latency.
- **L7 — Automatic releases (NOT built; biggest gap; today's §0.5/version drift is the proof):** CI-driven release cutting — pinned wheels + signed-spec staging to the ≤1 manual signature (R5) + GitHub release + Pages publish + release-parity guard. Design (architect) → build → sign-gate.
- **L1.b — Auto-track-main / auto-update:** `ce update --track main` (pull+rebuild+re-verify, governance intact) + the auto-update trigger+prompt+recall-floor (#682 P0 merged; #366 ratified). Verify build state in N0 audit.
- **Conveyor/intake daemon:** the harvest→validate→push→review intake is currently MANUAL (controller by hand). Automate it (a governed conveyor daemon) — the deferred [[ce-controller-conveyor-intake-directive]] mechanization.
- **Cross-repo close-bot (#262):** merge-triggered ce-ops auto-close — verify built; if not, build.

## N3 — P1 follow-ons + carry-overs
ce-ops#377 (per-arch base-image digests — proper fix for the arm64-override hack), ce-ops#378 (work-mgmt SSOT doc — review/merge), Fleet-IaC P1 (`.ce/briefs/fleet-iac-p1-framing.md`), #376 process-hole sweep. L4 P1 (vllm-path db fix = R2/GPU-gated). #363-C egress, #663 install-sig advisory→required.

## N5 — Fleet hygiene (enabler)
Prune stale worktrees (~210 + this session's `.ce/wt-ce68x/69x-review`, `wt-*-harvest`; KEEP `.ce/wt-resign-llms` until N1a ships). Codify seat origin-refresh as a `ce`/runbook action.

## Seats (all idle, authed, healthy at handoff)
dev-1 (non-contained, self-pushes), dev-3 (contained ce-vps-codex, fetch-egress, harvest-to-push), dev-4 (contained ce-dgx-codex DGX, HEALED via device-auth, fresh quota — strongest seat → hardest lane; **always launch with explicit `CE_DGX_IMAGE=…0.142.4-aarch64`**). Dispatch mechanics: prompt-pointer+sha, embed briefs for contained seats, arm watchers, harvest contained-seat work (git-bundle out).

## Needs Operator
- **R4:** Nitzan's GitHub handle + scope (N1e contributor path).
- Re-confirm at firsts: spot-check the first live auto-merge (N2); eyeball the install-spec diff before merge (N1a).

## Standing authority (carries into night)
G1 merge-gate · G2 dispatch · G3 ce-ops tickets · G4 seat origin-refresh · G5 build autonomy (stop before live arming-flip) · G6 brain build · G7 daemon/worktree housekeeping · **R1 canary go-live = GRANTED + Option A confirmed** · **R5 install-spec re-sign = authorized for the openssh-client+0.3.1 fix** (future signs still per-instance). R2 (GPU embedder) when GB10 free; R6 anything else irreversible/out-of-envelope → auto-halt + surface.
