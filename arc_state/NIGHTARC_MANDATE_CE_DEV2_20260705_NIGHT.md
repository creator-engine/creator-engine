# NIGHT-ARC MANDATE — CE-DEV-2 — 2026-07-05 night — ✅ RATIFIED (Operator, ~19:4x local 2026-07-05, form: "ratified as written" — R1-R7 granted; D1 click timing open-surface-when-ready, D2 optional-untaken, D3 default assemble-only)
> Supersedes DAYARC_MANDATE_CE_DEV2_20260705.md on ratification (day execution log stays SSOT
> for what shipped). Companion context: tmp/thread-20260705/dark-factory-design.md (ce-ops#454),
> the day transcript, MEMORY.md.

## Day-state at drafting (~19:30 local)
21 PRs merged (#813–#833) + #834; 0.3.2 ceremony mid-flight: PR #838 built, wheel-verified,
SIGNED (canonical ddfbc963, round-2 after review caught stale 0.3.1 prose INSIDE the signed
region — re-staged + re-signed), full preflight GREEN, narrow re-review running. Open conveyor:
#835 (fix building), #836 (approval banked, recompute pending), #837 (round-2 building), #839
(review pending). Seats building: dev-1 #433→#423 serial, dev-3 #424, dev-4 #405-ADR.
Three-way assertions.yaml collision sequenced: #838 → #835 → #836 (locked order).

## ⏸️ OPERATOR DECISIONS NEEDED AT RATIFICATION
- D1 — ce-seat ghcr visibility CLICK timing: chain is #838 merge → tag release/v0.3.2 →
  publish-seat-image (auto) → digest-pin PR → CLICK → canaries → Arad pack. If you can stay
  ~30-60 min post-ratification the whole DoD closes tonight; otherwise N-A parks at the click
  and canaries+Arad complete in the morning (one click, then I re-drive autonomously).
- D2 — optional: narrow mythos-ce App from all-repos back to {mythos, ce-canary-sandbox}.
- D3 — Arad handoff DELIVERY: default = I assemble the pack tonight, YOU send it (external
  comms stay R-class). Say the word if you want delivery authorized differently.

## Lanes
### N-A — 0.3.2 pipeline completion (first priority)
1. #838: on narrow re-review APPROVE → approve as ce-dev-2 → queue merges.
2. Tag release/v0.3.2 MANUALLY at the merge commit (pre-empts the auto-tag/CI dual-fire race,
   ce-ops#395 residue); treat CI release.yml's duplicate draft release + AWAITING-OPERATOR
   issue as no-ops and close them with a pointer to the manual ceremony.
3. publish-seat-image fires on the tag → capture manifest-list digest → small PR: pin
   surfaces/manifest.yaml seat-image entry (FULL metadata tuple per #823 ratchet) + REMOVE the
   UNSET allowlist tuple → review → merge.
4. ⏸️ D1 CLICK → verify anonymous pull of ce-seat.
5. Canaries vs LIVE 0.3.2: A (fresh ce-canary-a, VPS one-liner), B (/var/tmp/ce-canary-b DGX,
   llms-install.md-fed agent), C completion (controller-inline PEM apply vs
   chmod735-dor/ce-canary-sandbox, commands logged in CANARY_C_LOG.md) → DoD evidence pack.
6. Arad handoff pack assembled (welcome base = #821; tenant-specific cover OUTSIDE the repo).
7. rc2 branch disposition: delete ce-release-0.3.1-rc2 + its stale 0.3.1 staging (fixes were
   folded forward into #838); reconcile/close the release-staging drift ticket (#416-class).

### N-B — conveyor completion (parallel, non-gating)
#835 redundancy-fix → re-review → post-#838 ledger recompute → merge. #836 recompute →
submit banked approval → merge. #837 round-2 (3 review blockers + CI stub) → re-review →
merge. #839 (#433 U1) review → merge. Then: dev-1 #423 U2, dev-3 #424, dev-4 #405-ADR —
harvest/review/merge each. Seats restocked from backlog per no-idle directive throughout
(candidates: #405 follow-through, #427/#426 G-series, #455 once ce-415 content is on main,
#420 custody design).

### N-C — ticket close-out + filing sweep (post-#838)
Close with evidence: #443 #434 #451 #431(on merge) #430(delivered by #826 — verify) #447
units #448 #449 #450; #428 → close a+b, respawn (c) e2e-fixture as own ticket. FILE new:
egg-info wheel-bake self-clean (bit 3× today); release-stage prose-version lint (today's
re-sign cause — grep old semver in canonical before emitting bytes-to-sign); client-CI
SHA256SUMS signature-chain hardening (from #830 review); uppercase-digest + per-arch
placeholder residue (from #827 review); --list-checks/--profile UX nit (from #834).

### N-D — dark-factory slice 1: merge-triggered dependency unlock EXECUTOR (post-#838)
Per ratified #454 sequencing (implementation after 0.3.2; slice 1 = cheapest, hurt twice
2026-07-05). Contract vocabulary already merged (#828, docs/contracts/dependency-unlock.md).
Build: merge-event action (attach to ce-ops-autoclose.yml precedent) that re-evaluates
readiness_blockers for open items declaring the merged PR/issue as blocker and flips
eligibility (label mutation per contract), idempotent + replay-guarded, SHADOW-FIRST
(log-only mode), kill-switched, fail-closed per the contract incl. the closed-without-merge
rule banked on #454. NO belt actuation (piece 3) and NO ephemeral controllers (piece 5)
tonight — design-ratified but sequenced later. Stretch (if slice 1 lands early): piece-4 seed —
extend work_claims.py's marker comment through lifecycle states (clawsweeper pattern,
extension of running code, forge-side only, no daemon).

### N-E — hygiene (quiet windows)
Worktree prune (60+ .ce/wt-* accumulated; keep parked/active only). MEMORY.md index over
budget (38.8KB > 24.4KB — trim entries to one line, move detail to topic files). C5 queue-
daemon containerized cutover retry in a GENUINE quiet window (rebuild image from post-0.3.2
main first; host launcher = kill-switch; ≥3 arc-day soak clock restarts on cutover).

### N-F — morning handoff
Resume state + board serialization. Nitzan contributor-lens PREP as DRAFT only (CONTRIBUTING/
access/gates skeleton per ce-nitzan memory) — no external comms, details TBD with Operator.

## Bounds (unchanged, standing)
Gate stays singleton; ce-root-v1 signing stays this seat (no further signing expected tonight
— 0.3.2 spec already signed); no arming beyond ratified envelopes (L2 docs-class automerge
only; N-D ships SHADOW); no external comms/delivery (D3); R-class → auto-halt → morning.

## DECISION ANSWERS (Operator, ~19:5x local)
- D1: click PARKED TILL TOMORROW → N-A runs steps 1-3 tonight (merge #838 → manual tag →
  seat-image publish → digest-pin PR merged), then ⏸️ AWAITING-OPERATOR marker at step 4;
  canaries A/B/C + DoD evidence + final Arad pack completion = MORNING, first thing after the
  click. Tonight: pre-assemble every canary-independent piece of the Arad pack.
- D2: mythos-ce App stays all-repos (as is).
- D3: agreed — controller assembles, Operator sends.
