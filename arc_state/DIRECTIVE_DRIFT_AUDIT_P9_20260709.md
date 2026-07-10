# DIRECTIVE DRIFT AUDIT — P9 CONTINUATION — 2026-07-09 (STRANGELOOP-1 pool unit)
# Produced by read-only architect_research; controller-verified additions in the footer.
# Method + calibration: DIRECTIVE_DRIFT_AUDIT_20260708.md. Source basis: local state/ledger/
# changelog corpus (GitHub API was unavailable to the worker; controller verified the two
# decidable open questions — see footer).

## Headline findings
- SWEPT 13 closure events. REAL: #366, #367, #382, #463, #488, #500, #346, #357 (code-scope).
  PARTIAL: #467 (gate real; release-sync + content currency never shipped), #149 (.hermes 7 live
  runtime deps; R2 in flight), #491 (dry-run slices real; arming lane orphaned).
  CLOSED-BEFORE-REAL: #184 (VPS /tmp guard inadequate; OOM recurred; stronger fix landed on an
  already-closed ticket). NOT-REAL component: #356 Surface B (brokers never deployed as services).
- PATTERN A — merged≠deployed (3 instances on 2026-07-08 alone): Acceptance-Evidence slice 1
  (#916) does NOT close this for deploy-class tickets — evidence must be a PERSISTENT-STATE probe
  (systemctl is-active), not code-path existence. → Acceptance-Evidence slice 2 requirement.
- PATTERN B — ad-hoc process masquerading as deployed service: "parity proven" memories recorded
  states that died with their sessions (Jul-2 broker canary). Deployment claims need a
  persistent-state check at claim time.
- PATTERN C — slice-1-closes-epic: #491 joins #467/#149. Future cases blocked by #916; already-
  closed epics need manual residual filing.
- PATTERN D — docs claim unshipped verbs (7 beyond ce-inbox, per #910 review) → documented-verbs
  gate (#508 lineage) should be CI.

## Remediation shortlist (prioritized)
P0: (1) P6 broker deployments VPS+DGX as systemd services (dev-3 commit-only until then;
staged brief exists: /home/cedev2/creator-engine/.ce/briefs/ce-armB-broker-dev1.md);
(2) post-hermes-merge: grep the 7 runtime dep files on fresh origin/main; residual if any survive.
P1: (3) #491 residual (arming lane + Operator call); (4) #184 follow-on (OOM monitoring + IaC
persistence of the swapfile fix).
P2: (5) #467 residual → fold into #509 program; (6) speckit docs sweep (12 files).
P3: (7) documented-verbs CI gate; (8) Acceptance-Evidence deploy-class extension (persistent-state
probes).

(Full sweep table and evidence paths: see the P9 worker transcript summary in the arc ledger and
this file's source list — table preserved in the worker output at
/tmp/claude-1003/-home-cedev2-creator-engine/f99580bf-11af-4c3c-9cba-aa07611522b9/tasks/ac5c3cbfacc7b84cd.output)

## Controller verification footer (2026-07-09 ~06:2x)
- ce-ops#491: CLOSED (gh-verified) → Pattern C confirmed; residual required.
- ce-ops#356: CLOSED (gh-verified) → Surface B closed-but-not-real CONFIRMED; broker deployment
  (P6) is the remediation, residual required.
