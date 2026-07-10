# NIGHT-ARC MANDATE — CE-DEV-2 — 2026-07-04 evening — RATIFIED (Operator, ~18:30Z, form-echo "Ratify as drafted", full ambition incl. C5 gated cutover)
> Prepared ~18:25Z at Operator request ("very ambitious — starting early, dev ops now more
> efficient, throughput and long-run stability proven"). Cutover gap ticket = ce-ops#445;
> startup lease = ce-ops#444; key custody = ce-ops#442. Supersedes NIGHTARC_MANDATE_CE_DEV2_20260704.md
> for tonight. Day-arc SSOT remains DAYARC_MANDATE_CE_DEV2_20260704.md (containerized-first endgoal,
> ctx>45% definitive-/clear). Priority directive carries over: core platform lanes SOLE focus;
> Arad/Nitzan/N1.5 stay parked.

## Theme: close the arming loop + make the containerized gate real
Two spines, worked in parallel across the 3-seat fleet, everything staged so the Operator's
morning session is pure ratification + flips.

## Lanes (priority order)
- **N-A Carryover flush (continuous)**: harvest→independent-review→merge the three in-flight
  units (dev-1 ce-440-s3b · dev-3 ce-388-fastfollow-lease-ux · dev-4 ce-410-s10). After S3b
  merges: dispatch ce-440-s3c (3-line INSTALLED_CE_DOGFOOD_MIGRATION.md snippet fixup, tiny).
  Keep every freed seat re-stocked from N-C/N-D/N-F.
- **N-B Re-Arming Evidence Bundle (after s10 merges)**: assemble per CE410_ARMING_FIX_DESIGN
  "Re-Arming Evidence Bundle Required" (code evidence · test evidence · independent-review
  evidence for slices 2,6,8,9,10) into .ce/state/research/CE410_REARMING_BUNDLE_<date>.md.
  Mark ⏸️ AWAITING-OPERATOR, surface FIRST in the morning. NO arming flip tonight (R-reserved).
- **N-C Containerized gate substrate** (fact base: A2_QUEUE_DAEMON_CUTOVER_STAGING_20260704.md):
  - C1: build `creator-engine/ce-validator:0.3.1` NATIVELY on DGX aarch64 from the #781
    scaffolding; verify Architecture=arm64 + a smoke `cev3 --help` in-container. LOCAL build only —
    no registry publish (publish = FleetIaC/registry decision, not tonight).
  - C2: launcher plumbing PRs closing G3-G6 (env contract, BAO_CACERT mount provision, DGX env
    file staging, tmpfs mount for the wall secret in container form — memory-only custody restored).
  - C3: ce-ops#444 queue-daemon fail-closed startup lease (reuse A1 DaemonLease; disjoint from
    s10's conveyor_daemon.py claim — verify territory at dispatch).
  - C4: cutover preflight checklist executed to GREEN (staging doc section 1) in dry form.
  - **C5 (STRETCH, pre-authorized by A2-SEQ ratification, execute ONLY if ALL true)**: C1-C4 green
    · zero PRs in flight or awaiting gate · kill-switch launcher re-verified · quiet window ≥2h
    before any expected PR traffic → execute stop-old→start-new cutover, watch 2 intervals green,
    then overnight soak counts as day 1 of 3. ANY anomaly → rollback to host launcher + halt lane +
    ⏸️ marker. If preconditions not all true, stage and leave for morning.
- **N-D review-pickup OpenBao identity wiring** (A2 precondition 2, decoupled per ratification):
  design + implement OpenBao-pointer credential wiring so review-pickup runs --identity ce-dev-2
  from vault refs (no cross-host PAT copies). Architect-research first (existing
  --approval-wall-secret-* backend pattern in v3_cli is the template). Containerized go-live on
  dev-1 = only if wiring + image for VPS (amd64) both land; otherwise stage.
- **N-E Fleet hygiene**:
  - Resolve the standing rc2-checkout anomaly deliberately: the main checkout's dirty
    codex-0.142.4 bump files (ce-ops#377 territory) — dispatch or archive with evidence, stop
    carrying it as a footnote.
  - ce-ops#442 interim hardening quick-win: PreToolUse deny rule for worker-context reads of
    ~/.ce-keys/ce-root-v1* (option b), if implementable in controller config tonight.
- **N-F Automation tail (seat-filler, only when N-A..N-D can't absorb a seat)**: ce-ops#395
  bump-to-main tag-timing policy draft · close-bot #262 · L3 triage apply-mode design.

## Authority for tonight
Standing grants G1-G5 continue (merge/dispatch/wall/canary within ratified envelopes). C5 cutover
rides the A2-SEQ Option A ratification with its own gates above. RESERVED (auto-halt → ⏸️):
arming the conveyor (Re-Arming = morning ratification) · any registry publish · external release /
tenant-facing changes · fleet-wide seat rollout · history scrub · anything outside the ratified sets.

## Standing constraints (unchanged)
Bounded work-units · full validate-pr one-pass green before push · independent non-author review on
every PR · signed-artifact STOP-line in every brief · pointer+SHA dispatch + territory check +
semantic novelty check · /clear seats before new mandates · controller inlines nothing · checkpoint
+ /clear at ctx>45% · resume = newest RESUME_STATE_CE_DEV2_* by mtime, dual-write dev-1 mirror.

## Morning hand-off deliverables (what the Operator should find)
1. ⏸️ CE-410 Re-Arming Evidence Bundle ready for ratification.
2. Carryover PRs merged; board re-stocked or cleanly parked.
3. Containerized gate: image built+verified, plumbing merged, preflight green — cutover either
   soaking (if C5 gates were met) or one-command ready.
4. review-pickup OpenBao wiring landed or staged with a precise remainder.
5. Checkpoint resume-state + this mandate updated with per-lane outcomes.
