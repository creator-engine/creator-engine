# ☀️ DAY-ARC MANDATE — 2026-07-03 — ⏸️ PENDING OPERATOR RATIFICATION
Theme: first external user onboarded (Arad) + the two ratified autonomy designs built and
canaried + night-arc carryover. Ratified inputs (2026-07-03, in-session): auto-merge tier
proposal (A+B approve, C staged behind B canary, D rejected; audit lines add reviewer-venue
field) · press-merge bundle design (all 6 asks; v1 schema includes Tier-B ledger fields).

## D1 — ARAD ONBOARDING (first priority, time-boxed to her availability)
- D1a INSTALL CANARY (before touching her machine): run the live one-liner
  (creator-engine.dev/install.sh) end-to-end in a clean throwaway env on our infra; verify signed
  spec + trust root + 0.3.1 wheelhouse + `onboard --inventory` complete. Any failure → fix lane
  BEFORE the session with Arad. Also spot-check pilot-runbook.md steps against live behavior
  (doc-accuracy pass exists; this is the final freshness check).
- D1b REMOTE INSTALL (her machine, via tailnet ssh): prepare `ce-install.answers.yaml` upfront
  (IaC-style per pilot-runbook §1; secrets only as env://file://prompt:// refs; sudo pre-granted
  ONLY as the scoped list the runbook allows). Run the one-liner with CE_ANSWERS. The two human
  seams stay human: sudo approval + GitHub-App authorization click (Arad, guided). STOP-line:
  any deviation from the documented runbook on her machine → halt + report, no improvisation.
- D1c E2E VERIFY + HANDOFF: inventory OK → `--plan` → `--apply` seams per runbook → smoke
  `ce launch` in ~/ce-mythos/mythos → welcome-package pointer (she reads in README order;
  constitution ratification is HER act, not ours). Record the full session transcript/evidence.
- NEEDS FROM OPERATOR (blocking D1b): Arad's tailnet hostname/IP + ssh user/access method +
  OS confirmation (mac-container path vs linux) + scheduled window + who sits on the sudo seam.

## D2 — RATIFIED AUTONOMY BUILDS
- D2a press-merge bundle demo (work class S, file list per design §5): press_merge_evidence.py
  assembler + inert `ce` CLI renderer + decide-workflow upload step + tests + (if repo practice
  requires) schema file. v1 schema INCLUDES Tier-B ledger fields (old/new record+active counts,
  head hashes, superseded IDs). Demo on ≥1 real arc PR. Read-only permissions; never-list per design.
- D2b auto-merge Tier A (carrier/changelog split-tier): per-tier flag CE_AUTOMERGE_TIER_CARRIER_CHANGELOG,
  audit labels + reviewer-venue field, path predicate. Flip live on merge (subset of already-live docs class).
- D2c auto-merge Tier B (brain-supersede chores): machine predicate (append-only assertions.yaml
  + tombstone/vN pair + count-bump + XS + one chain/PR + no forbidden fields), per-tier flag,
  audit w/ ledger evidence fields. CANARY: arm for real supersede PRs; first 5 canary merges
  reported to Operator with audit records; kill-switch documented. (N2's supersede slices become
  the natural canary traffic.)
- Sequencing: D2b/D2c touch automerge_policy/classifier/actuator — serialize vs each other,
  disjoint from D3's files. Tier C NOT built (staged pending B evidence); Tier D rejected.

## D3 — NIGHT-ARC CARRYOVER
- N2 pin-migration (ce-ops#407, dev-4, serial slices: pr_preflight → integrator_belt → SHA256SUMS
  → workflows → docs; doctrine brief = ce407-...-RATIFIED.md). Ledger lane owner. Its supersede
  PRs double as Tier-B canary traffic once D2c is armed.
- #383 argv hardening (post-#750, integrator/conveyor path).
- N4a self-triggering AutoReview wiring (dev-1).
- #410 conveyor-arming fixes: turn the 4 blockers into implementation tickets (architect slice
  first: daemon-owned allocation + credentialless validation sandbox design).
- Denylist follow-ups (ce-ops#369 closeout notes): regen vs live registry (CE_OPS_READ_TOKEN),
  freshness-workflow drift-detection design, CI rule denying committed generated artifact,
  scanner coverage for tests/** fixtures.
- N5 as capacity: #408 dev-1 contained PREPARE (no cutover), #400/#339 staged image fixes.

## STANDING
Support case #4529858 (reply-2 with Operator; purge watcher armed; on purge → prune local ref).
Watchers maintained · resume states + ⏸️ queue · report context each turn · ledger appends
serialized (single lane, owner=N2 after D2c predicate lands) · full preflight before every push ·
controller-side plaintext scan on every harvest.

## AUTHORITY (the batch ratification requested)
GRANTS REQUESTED TODAY: (R-A) Arad remote-install execution per D1 runbook+stop-line ·
(R-B) Tier A flip-live on merge · (R-C) Tier B canary ARM after predicate merges, bounded to
first-5-report + kill-switch · (R-D) press-merge demo on a real PR · standing G1–G5 continue.
REMAIN RESERVED: Tier C build · Tier D · conveyor arming (blocked by #410 anyway) · dev-1 cutover ·
release signing · history scrub · anything on Arad's machine beyond the documented runbook.

## SEAT ROUTING (initial)
dev-4 = N2 slices (ledger owner) then D2c predicate · dev-1 = D2a bundle build + N4a ·
dev-3 = D2b Tier A + #383 then #410 architect slice · controller = D1 Arad lane (only lane
driven directly, external-facing + access lives here) + gate/review conveyor.
