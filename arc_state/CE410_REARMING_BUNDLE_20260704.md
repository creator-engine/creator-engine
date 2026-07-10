# ✅ RATIFIED — CE-410 Re-Arming Evidence Bundle — Operator, 2026-07-05 ~03:05Z
> Binding form: in-session Operator reply "ce-410 - ratified as written", adopting the
> form-echo decision text in "## Ratification ask" below verbatim. Enables armed conveyor
> operation within deployment gates (shadow-first, containerized form, A2-SEQ singleton);
> code-class autonomous approve/merge remains NOT granted (separate R1 ask).
> Assembled by CE-DEV-2 per CE410_ARMING_FIX_DESIGN_20260703.md "Re-Arming Evidence Bundle
> Required" and the ratified night-arc lane N-B. SURFACE FIRST next Operator session.
> All ten slices merged to main; CE-410 is code-complete as of #788 (2026-07-04 18:38Z).

## Ratification ask (form-echo — reply with this text to bind)
"RATIFY CE-410 RE-ARMING: the arming preconditions of CE410_ARMING_FIX_DESIGN (allocation
receipts, authority-context separation, credentialless validation sandbox, armed-required seams,
final publish re-verification + audit) are met with independent review on every gate-adjacent
slice. Armed conveyor operation is authorized within the ratified deployment gates (shadow-first,
containerized form, A2-SEQ singleton rule). Code-class autonomous approve/merge remains a
SEPARATE R1 ask and is NOT granted by this ratification."

## 1. Slice provenance (11 PRs, all merged; approver ce-dev-2 in every case)
| Slice | PR | Branch | Merged | Merge SHA |
|---|---|---|---|---|
| 1 alloc-core | #758 | ce-410-alloc-core | 07-03 | a73b406f |
| 2 conveyor-alloc-wire | #761 | ce-410-conveyor-alloc-wire | 07-03 | 1bab54ed |
| 3 integrator-alloc-wire | #760 | ce-410-integrator-alloc-wire | 07-03 | 367741b6 |
| 4 authority-contexts | #762 | ce-410-authority-contexts-core | 07-03 | ca7c0dda |
| 5 git-phase-split | #764 | ce-410-integrator-git-phase-split | 07-03 | 842592c5 |
| 6 conveyor-phase-authority | #763 | ce-410-conveyor-phase-authority | 07-04 | c96fbc87 |
| 7 validation-env-scrub | #768 | ce-410-validation-env-scrub | 07-04 | 68a1473e |
| 8a shared-launcher | #773 | ce-410-s8a-shared-launcher | 07-04 | 1ed5c0b8 |
| 8b sandbox-runner | #777 | ce-410-s8b-sandbox-runner | 07-04 | e57f3e04 |
| 8c armed-wiring | #780 | ce-410-s8c-armed-wiring | 07-04 | 9e552e2f |
| 9 armed-refusal-seam | #784 | ce-410-s9-ledger-binding-seam | 07-04 | 04afa74c |
| 10 publish-reverify-audit | #788 | ce-410-s10-publish-reverify-audit | 07-04 | 1ddb5616 |

## 2. Independent-review evidence (design requirement: gate-adjacent slices reviewed independently)
7/7 gate-adjacent slices (2, 6, 8a, 8b, 8c, 9, 10) carry SUBSTANTIVE independent-review bodies —
zero bare approvals. Highlights: s2 = 11/11-point gate checklist w/ line evidence; s6 = round-trip
CHANGES_REQUESTED→remedied→re-approved; s8a/8b = rework cycles with all blocking findings
verified resolved; s8c = four review rounds; s10 = full fail-closed trace at merged head
(reviewer confirmed: no path where a failed re-check reaches push or pr-create; checks re-derive
from daemon-owned checkout at publish time; GIT_CONFIG_* smuggling blocked by full env
replacement; audit sinks nonce/signature-leak tested). Review bodies live on the PRs.

## 3. Code + test evidence verification (independent read-only verification worker)
13/13 items VERIFIED; 65/65 tests passed in the run (test_daemon_allocation 6/6 incl. forgery +
root-permission; test_authority_contexts env-scrub sentinels incl. GH_TOKEN/SSH_AUTH_SOCK/
GIT_ASKPASS/approval-wall; test_integrator_belt per-phase env split; test_conveyor_daemon 53/53
incl. r1-r4 regressions — banned control fields, hostile/dotdot/outside-root paths, TOCTOU).
Key code anchors: daemon_allocation.py:172-241 (receipts), conveyor_daemon.py:366-389
(armed-required list: path_allocator, daemon_lease, receipt_issuer, validation_ledger_binding),
authority_contexts.py:136-300 (three context types), conveyor.py:467 (allowlist env, no environ merge).
**Provenance caveat (recorded for honesty):** this verification ran at main@3a930d05 (pre-#788),
so its slice-10 view reflects the 8c-era tree. Slice-10 specifics (explicit behind==0 rev-list
check, manifest-fidelity re-check, config-mutation check, per-phase audit + four dedicated
refusal tests) are covered by: the #788 independent review at merged head da357d83 (section 2),
validate-pr 19/19 on that head, and green CI at merge. No re-verification gap of substance.

## 4. Residual items (none blocking arming-logic correctness; all tracked)
- ce-ops#443 (A1 daemon fast-follows: lease UX/test, --dry-run misnomer, recovery runbook) — in
  implementation on dev-3 tonight.
- ce-ops#444 (queue-daemon startup lease) + #445 (containerized deployment gaps; G1/G7 closed by
  the local arm64 image build, G8 Dockerfile fix in implementation on dev-4 tonight) — these gate
  DEPLOYMENT form, not arming correctness.
- #788 reviewer non-blocking coverage notes: no dedicated rename-entry manifest test; secondary
  rev-list behind-path exercised only via happy-path default.
- Design's slice-8 production-sandbox evidence: sandbox runner rides the ratified
  worker-container policy (podman-verification-v1.yaml, validated at runtime; refusal if absent).

## 5. What ratification enables / does not enable
ENABLES: armed conveyor daemon operation (real allocation receipts, sandboxed validation,
publish re-verification) within deployment gates: shadow-first rollout, containerized form
(two-plane), A2-SEQ singleton rule, kill-switch retained.
DOES NOT ENABLE: code-class autonomous approve/merge (separate R1 ask per the day-arc mandate
Shape-1); registry publish; any tenant-facing change.
