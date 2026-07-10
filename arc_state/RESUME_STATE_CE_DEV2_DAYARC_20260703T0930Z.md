# RESUME STATE — CE-DEV-2 — 2026-07-03 ~09:30Z (post-Arad-golive checkpoint; supersedes 0720Z)
> MEMORY.md first. Mandate DAYARC_MANDATE_CE_DEV2_20260703.md fully ratified (R-A..R-D, B1) and
> LARGELY EXECUTED. 🎉 MILESTONE: Arad = first external user LIVE in a governed session on
> governed chmod735-dor/mythos.

## ⏸️ AWAITING-OPERATOR (surface first)
1. GitHub plan for chmod735-dor: Team upgrade (rec) vs make-public vs stay-unenforced — branch
   protection floor un-enforceable on free-org private repo (apply leg brownfield_verify_preserved_checks
   refused 403). Working rule meanwhile: PRs-only, nobody pushes mythos main directly. Fix = rerun
   the one leg (idempotent) after upgrade.
2. Support case #4529858: purge watcher armed (bg); on fire → prune local ref
   origin/ce-369-fleet-guard-ssot-denylist + object.

## D1 ARAD — COMPLETE (evidence: /var/tmp/d1b-session-0720.log + d1b-apply-20260703.log + logs on her machine)
Install 0.3.1 GREEN (signed spec b1418f73, no sudo) · plan apply-ready · B1 apply from
/var/tmp/d1b-mythos-apply (mythos-ce App, inst 141552951) → join PR #5 MERGED by Arad · one leg
refused (see above) · ce launch LIVE. Package at her ~/ce-welcome (verified clean). Seat identity:
kind:own mythos-arad (4159494/inst 142925881, client Iv23liYX7gwrsQb01c2f, PEM staged her
~/.ce-secrets, answers file on her machine carries the block). Git: remote switched to SSH
(key registered), local main ff'd to 43d92bf. PENDING HER: constitution ratification (manual path,
commit docs/constitution.md; her old local branch chore/spec-kit-init-and-constitution has draft
material — mine then delete). Local legacy dirs .ce/state(0.2.0)+.hermes on her clone = harmless,
tidy later. PAT footnote: bootstrap token identity-only by design; git creds now via SSH.

## CONVEYOR STATE
- #755 (bundle, epic/L) + #756 (N2 s2, XS): APPROVED + green, in daemon settle → MERGE EXPECTED;
  verify merged on resume; then R-D COMPLETE (demo artifact
  ce-press-merge-evidence-bundle-755-492ed398...-28647680482-1, verdict blocked/non-authority = honest)
  and N2 s2 done → integrator_belt pin-tax DEAD → #383 UNBLOCKED.
- #755 saga (for audit trail): seat self-caught in-place ledger mutation (d1b-09 re-hash),
  cleaned force-push 492ed3988, two-pass re-review APPROVE; near-miss recorded on ce-ops#411
  (ask: universal CI gate failing non-append ledger edits).
- Tier A LIVE (CE_AUTOMERGE_TIER_CARRIER_CHANGELOG=true, set 07:28Z; #412 closed). WATCH: first
  Tier-A auto-merge → verify audit line (tier label + reviewer_venue) + note to Operator.
- dev-4: building #413 Tier B predicate (brief BRIEF_ce413_tierB.md in container; branch
  ce-413-automerge-tier-b; waits for #756 in main before branching). ON ITS MERGE: R-C = controller
  ARMS canary (flag CE_AUTOMERGE_TIER_BRAIN_SUPERSEDE=true), first-5 auto-merges reported w/ audit.
- dev-3: #410 arming-fix ARCHITECT design (read-only; output /var/tmp/CE410_ARMING_FIX_DESIGN.md
  in ce-vps-codex; extract via ssh dev1 + docker exec cat; then → implementation tickets).
  dev-3 NEXT after: #383 argv hardening (now unblocked post-#756).
- dev-1: idle post-#755 → NEXT: N4a AutoReview self-trigger wiring.
- Watchers alive: seat-signals · 2× PR-board · #729-purge. Subagents auto-resume after /clear —
  check provenance before re-dispatching; reviewer workers for 752/753/754/755/756 all done.

## CLIENT-TENANT PROGRAM (contractor pivot)
#421 RATIFIED (all 6 defaults: Model C default · shared+broker default lane w/ own first-class ·
dedicated mount/tenant · tenant venue not ce-ops · autonomy tiers OFF default, client ratifies ·
strict phase sequencing). Gap tickets #422(G1 schema) #423(G7 denylist) #424(G8 egress broker)
#425(G10) #426(G11) #427(G12). #428 P1: adoption template ships CE-shaped ce-validate.yml + no
client-repo check profile — LIVE-REMEDIATED on mythos (mythos-ce[bot] 2f4137f1a: hash-pinned wheel
install + 4 tolerated repo-profile checks, GREEN); product fix outstanding. Phase 1 (Mythos
reference completion) = next program work: key custody → OpenBao tenant mount, tenant manifest
hand-authored, approver_ref provenance (G12).
Design: .ce/state/research/CLIENT_TENANT_DEPLOYMENT_DESIGN_20260703.md (+ CONTROLLER ADDENDUM).

## SCOREBOARD TODAY (through 09:30Z)
Merged: #752 #753 #754 (+ #755 #756 imminent) · Tier A LIVE · Arad onboarded (D1a/b/c complete
minus protection leg) · tickets filed #412-#420 #422-#428 · #421 design ratified · ledger 86
active · docs/site pilot command-surface fixed · 5 governance catches all closed w/ evidence
(2 reviewer, 1 seat self-audit, 1 venue-refusal fail-closed, 1 first-user CI catch).

## EXECUTION NOTES (carry forward; supersedes none)
All prior mechanics from 0600Z/0700Z states still apply (pointer+SHA, herdr re-Enter, harvest
gates, plaintext scan, marker-revalidate ~6min tax, container caveat→host adjudication). New:
herdr composer sometimes needs TWO Enters (three occurrences today) · monitor "NEW PR" lines can
re-announce after empty-poll reset · reviewer self-fire misread → correct venue facts via
SendMessage, don't override · force-push after approve = void + delta re-review via SAME reviewer
agent (worked twice today) · pip hash-mode client workflow pattern in mythos ce-validate.yml.
