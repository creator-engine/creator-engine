# PR path manifest — `ce249-split-relocate-and-scrub` · public confidentiality split (ce-ops#249)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the internal-tracker per-PR
manifest convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests \
  --head-ref ce249-split-relocate-and-scrub --require-carrier
```

and requires this PR's `base..HEAD` diff (computed `--no-renames`) to equal exactly
the authorized path-set below (the carrier lists itself); the repo-wide fidelity scan
requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-approved ce-ops#249 public-repo confidentiality split. The authoritative
verified product-vs-internal classification (controller, 2026-06-26) is the scope
record: relocate 23 internal-only docs to the private tracker (backed up
byte-identically), scrub 8 product docs that stay public, and de-link the surviving
public docs from the relocated set so the public surface carries no dangling internal
links.

Base:
`4747e7f3ad893a7ce729c0341ecc3a4b5aaa0f12` (current public `main` at handoff).

Scope adjudication:
IN: (1) DELETE the 23 verified RELOCATE files (internal fleet/daemon/rehearsal ops,
live delivery-tracking instances, internal strategy/research design notes, the
account-switch script + report). (2) SCRUB 8 KEEP-BUT-SCRUB product docs IN PLACE —
reword internal-tracker ticket references to generic phrasing, generalize the two
account logins in the GitHub-native coordination protocol, and generalize the one
host-specific mention in the controller runtime contract. (3) DE-LINK every surviving
public doc that linked into the relocated set (convert each dangling relative Markdown
link to a plain inline filename reference) so the dangling-internal-doc-link guard
stays green. (4) Shrink the public-docs confidentiality `_KNOWN_PENDING` allowlist by
removing the now-deleted and now-clean files (the ratchet may only shrink). (5) Scrub
the harness-matrix RENDERER (`harness_matrix.py`) so the generated public matrix doc
is regenerated clean (the doc is rendered from code; scrubbing the doc alone would
break the render-fidelity contract), and update its test + the integrator systemd test
that hard-referenced a now-relocated doc. (6) Add the changelog fragment + this carrier.

OUT: any content change to the relocated docs (they are deleted verbatim, preserved in
the private tracker); any product-meaning change beyond confidentiality scrubbing and
mechanical de-linking; any code change beyond the render-fidelity + relocated-doc
test couplings the deletions/scrubs force.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=57

AUTHORIZED_PATHS_SHA256=ed96fa3e073398bcb3a058a45f0202dcfd6c1985f24907e761b11e6eb4dd54f5

```text
.ce/changelog/ce249-split-relocate-and-scrub.md
.ce/pr-manifests/ce249-split-relocate-and-scrub.md
.ce/reports/cue-account-renames-20260620.md
.ce/state/research/DESIGN_ce113_openbao_20260619T031542Z.md
.ce/state/research/DESIGN_ce115_controller_containment_20260619T043931Z.md
.ce/state/research/DESIGN_ce135_openbao_secret_zero_broker_20260620.md
.ce/state/research/DESIGN_ce158_trust_anchor_20260621T025918Z.md
.ce/state/research/DESIGN_ce39_merge_throughput_20260619T032314Z.md
docs/architecture/pilot-deployment-transport.md
docs/architecture/pilot-roadmap.md
docs/architecture/pilot-uiux-model.md
docs/architecture/README.md
docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md
docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md
docs/delivery/BACKLOG.md
docs/delivery/DEFINITION_OF_DONE.md
docs/delivery/DEFINITION_OF_READY.md
docs/delivery/DEPENDENCIES.md
docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md
docs/delivery/KANBAN.md
docs/delivery/MERGE_APPROVAL_CHECKLIST.md
docs/delivery/NEXT_TASK_PROTOCOL.md
docs/delivery/PUBLIC_READINESS_GATE.md
docs/delivery/README.md
docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md
docs/delivery/RELEASE_DEPLOY_GOVERNANCE.md
docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md
docs/delivery/REVIEW_GATE.md
docs/delivery/RISK_REGISTER.md
docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md
docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md
docs/governance/CODEX_FIRST_CLASS_SCOPE.md
docs/operations/CLEAN_ROOM_REHEARSAL.md
docs/operations/CONTAINED_LAUNCH_PROOF.md
docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md
docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md
docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md
docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md
docs/operations/HERMES_FORK_UPSTREAM_SYNC.md
docs/operations/INTEGRATOR_BELT_DAEMON.md
docs/operations/MERGE_QUEUE_ENABLEMENT_RUNBOOK.md
docs/operations/ONBOARD_APPLY_PROTOCOL.md
docs/operations/PARALLEL_PAIR_REHEARSAL_RUNBOOK.md
docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md
docs/operations/REVIEWER_TRIAGE.md
docs/operations/REVIEW_PICKUP_DAEMON.md
docs/operations/ROLE_BOUNDARY_FAILSAFE_STAGE_1_DESIGN.md
docs/operations/ROOT_WORKTREE_INVARIANT.md
docs/operations/SEAT_CE_OPS_READONLY_CHECKOUT.md
docs/operations/SEAT_REAPER_PROTOCOL.md
docs/operations/SWITCH_OPENAI_ACCOUNT.md
docs/operations/V1_DELIVERY_REHEARSAL.md
scripts/switch-openai-account.sh
validators/creator_engine_validator/harness_matrix.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_harness_matrix.py
validators/tests/unit/test_public_docs_confidentiality.py
```
