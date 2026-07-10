# 0.3.4 Release Candidate List — 2026-07-08
## ASSEMBLE-ONLY — cut + signing is an Operator co-sign ceremony
The release tag, install.sh SHA256 pin update, and ce-root-v1 signature are
non-delegable Operator actions. Do not execute those steps from this file.

---

## Baseline
**Last signed release: v0.3.3** (PR #857, commit `7d2baed9e`, 2026-07-06)
- Release staging dirs present locally: `0.3.0`, `0.3.1` (0.3.2/0.3.3 released via automation, no local staging dir)
- Git tags for v0.3*: none present in local tag namespace; canonical record is main-side release commit

---

## Candidate Commits (origin/main since 7d2baed9e)

### Pre-arc  —  2026-07-06 (post-0.3.3 same-day)
| PR | Title | Work class | Category |
|----|-------|------------|----------|
| #858 | docs(design): ce-ops#464 worktree-debt classified sweep | tiny | design |
| #861 | Harden client CI SHA256SUMS verification | story | infra |
| #862 | fix(docs): bump public docs to 0.3.3 | tiny | fix |
| #863 | fix: pin 0.3.3 image digests | tiny | fix |
| #865 | fix(verify): honor declared protections:reference (ce-ops#474) | tiny | fix |
| #866 | feat: add controller posture banner | story | feature |
| #867 | feat(ci): version-drift gate for current-version claims (ce-ops#467 s1) | story | feature |
| #869 | test: isolate wheel determinism artifacts | tiny | infra |
| #870 | docs: design SSHSIG signing deputy for ce-root-v1 (ce-ops#481) | tiny | design |
| #871 | Add ce takeover dry-run core | story | feature |
| #873 | ce-ops#477 takeover refusal and watcher re-arm | story | feature |

### (a) Day-arc  —  2026-07-07 (14 merges)
| PR | Title | Work class | Category |
|----|-------|------------|----------|
| #859 | Add merge_group trigger to adoption workflow template | tiny | infra |
| #864 | feat(launch): in-launcher reviewer-authority envelope minting (ce-ops#426 G11) | story | feature |
| #868 | feat(claims): work_claims lifecycle — state machine, YAML schema, ce claim verbs (ce-ops#476) | story | feature |
| #872 | feat: add egress broker forge read lane (ce-ops#475 s1) | story | feature |
| #874 | feat: add continuity drill harness | story | feature |
| #875 | feat(broker): JIT seat credential lane (ce-ops#228 s1) | story | feature |
| #876 | feat(cli): teach CE journey next steps | tiny | feature |
| #877 | docs: add canonical CE journey guides | story | docs |
| #878 | feat: seed shaping from PRD context | story | feature |
| #879 | feat: add Codex controller promotion evidence packet (ce-ops#480) | story | feature |
| #880 | ce-ops#479 harness promotion parity matrix | story | infra |
| #881 | feat(onboard): genesis brain ledger + brain-init refusal-that-teaches (ce-ops#489) | story | feature |
| #882 | validators: guard brain ledger tail freshness | story† | infra |
| #885 | fix: refresh onboard workflow template | story† | fix |

† #882 and #885 share carrier `ce-885-882-followups` (declared: story).

### (b) Night  —  2026-07-07/08 (10 merges)
| PR | Title | Work class | Category |
|----|-------|------------|----------|
| #883 | Codify forge housekeeping runbook | tiny | docs |
| #884 | docs: design host-ops broker v1 | tiny | design |
| #886 | Design recursion bottom-out policy | tiny | design |
| #887 | docs: design ephemeral controller provider seam | tiny | design |
| #888 | feat(brain): memory-layer slice 1 — decision/lesson kinds + hydrate contract (ce-ops#488) | story | feature |
| #889 | design: CE-491 Option A merge-time brain append intent materialization | tiny | design |
| #890 | fix: #885/#882 follow-up batch — spec refusal, stderr surface, test pins | story† | fix |
| #891 | Harden runsc launcher durable paths | XS‡ | infra |
| #892 | docs: design seat-side preflight | tiny | design |
| #893 | Add DGX runsc hygiene coverage | XS‡ | infra |

‡ #891 and #893 share carrier `ce-891-hygiene-pair` (declared: XS).

---

## Candidate Summary
| Category | Count |
|----------|-------|
| feature  | 14    |
| fix      | 5     |
| docs     | 2     |
| design   | 7     |
| infra    | 7     |
| **Total**| **35**|

---

## Changelog Fragment Coverage (origin/main:.ce/changelog/)
All 35 candidate PRs appear covered. Mapping verified for:
- Pre-arc: ce-459, ce-464, ce-467, ce-474, ce-478, ce-477, ce-033-digest-pin, ce-472
- Day-arc: ce-461b, ce-426, ce-476, ce-475, ce-477 (drill+refusal), ce-228, ce-486, ce-485, ce-487, ce-480, ce-479, ce-489, ce-885-882-followups
- Night: ce-495, ce-482, ce-483, ce-484, ce-488, ce-491-optiona, ce-885-882-followups, ce-500, ce-499, ce-891

**No missing-changelog blockers identified.** (Audit: 35 candidate PRs, all map to ≥1 dated fragment.)

---

## Release Mechanics Reminders (do not execute here)
1. **Cut off CURRENT main** — verify merge-base is origin/main tip (`b2a2c27c3`) before tagging.
2. **install.sh is a RELEASE op** — any sha256-pinned file update triggers the full signed-release flow.
3. **ce-root-v1 signing = Operator co-sign** — non-delegable; follow spec-signing playbook; workers must not sign.
4. **Carrier requirement** — the release PR itself needs a declared work class carrier; slug must match branch name.
5. **Changelog obligation** — assemble `.ce/changelog/<slug>.md` fragments into CHANGELOG before tagging.
6. **Version bump** — update `current-version` claim and public docs to 0.3.4 as part of the release PR.
