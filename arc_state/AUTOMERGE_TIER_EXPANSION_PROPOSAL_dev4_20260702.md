# Automerge Tier Expansion Proposal

Evidence read: `/var/tmp/n4c-design-read`, detached at
`2290798396e20b52bf7595e4f442ace48438715b`. This is a design proposal only;
none of the tiers below is effective without Operator ratification and a
separate implementation change.

## 1. Current-State Map

Today the live-capable automerge path can produce `AUTO` only for the existing
`docs`/`none` auto classes, and only when all ordinary PR gates are already
satisfied. The constants define `AUTO`/`GESTURE`, armed run modes
`ceo|strangeLoop`, and the tiny/story canary ceiling in
`validators/creator_engine_validator/forge/automerge_policy.py:26-38`.
The checked-in path classifier marks `AUTO_CLASSES` as `{"none", "docs"}` and
treats every other mutation class as gesture/manual in
`validators/creator_engine_validator/forge/mutation_classifier.py:25-31`.

Policy materialization from GitHub variables currently enables only the `docs`
class, and only when `CE_AUTOMERGE_RUN_MODE` materializes as `ceo` or
`strangeLoop`; every class other than `docs` is written with
`auto_merge=false` in
`validators/creator_engine_validator/forge/automerge_policy.py:286-322`.
The mutation policy's required check is `"Validate governance artifacts"` and
the `docs` path envelope is exactly `docs/**`, `*.md`, `.ce/changelog/**`, and
`.ce/pr-manifests/**` in
`validators/creator_engine_validator/forge/automerge_mutation_policy.yaml:16-23`.
Code, schema, deploy, governance, identity, security, attestation, and
redaction paths are separately classified in
`validators/creator_engine_validator/forge/automerge_mutation_policy.yaml:24-83`.

The decision engine blocks `AUTO` unless all of these are true:
ratification gates are exactly `auto_back_gate`, required checks are green,
review decision is `APPROVED`, size band is not `split_required`, declared work
class is `tiny`/`XS` or `story`/`S`, mutation class is not a gesture class,
kill switch is off, run mode is armed, the class flag is true, an enabling ref
is present, and author/approver are distinct
(`validators/creator_engine_validator/forge/automerge_policy.py:406-440`).
That uses the sizing table where `none` and `docs` map to `auto_back_gate`,
while `code` maps to `distinct_review, operator_merge`; higher-risk classes add
operator gates
(`validators/creator_engine_validator/work_sizing.py:63-97`).

The actuator independently re-verifies the decision before touching GitHub:
armed run mode, `decision=AUTO`, kill switch false, class flag true,
tiny/story canary ceiling, enabling ref present, live policy still armed and
not killed, live author/approver independence, and live required checks green
(`validators/creator_engine_validator/forge/automerge_actuator.py:66-124`).
Only after those predicates pass does it call the plan-by-default GitHub
auto-merge helper with `apply=True`; the helper itself plans unless `apply` is
explicitly true
(`validators/creator_engine_validator/forge/auto_merge.py:115-153`).
The actuator writes a secret-free audit record with status, reason, acted,
decision, run mode, kill switch, class flag, work class, mutation class, repo,
PR, head, branch, base, author, approver, `single_pr`, and enabling-ref
presence
(`validators/creator_engine_validator/forge/automerge_actuator.py:404-446`).

The decide workflow is read-only for repository contents and PR metadata,
materializes policy from repository variables, resolves changed paths via
`gh pr view --json files` or a three-dot `git diff` fallback, reads live review
and check state, emits one decision JSON, and uploads it as an artifact
(`.github/workflows/automerge-decide.yml:34-56`,
`.github/workflows/automerge-decide.yml:58-152`,
`.github/workflows/automerge-decide.yml:154-260`,
`.github/workflows/automerge-decide.yml:263-362`). The actuate workflow runs
only after a successful decide workflow, checks out the default branch with
write PR permissions, materializes the same policy variables, downloads exactly
one decision JSON, calls the actuator, and uploads the audit JSONL
(`.github/workflows/automerge-actuate.yml:14-27`,
`.github/workflows/automerge-actuate.yml:44-66`,
`.github/workflows/automerge-actuate.yml:68-117`).

Rollback today is coarse: `ce automerge-kill-switch on` toggles the durable
global kill switch, with `status|on|off` implemented in
`validators/creator_engine_validator/ce_cli.py:4201-4257`, and the variable
fallback is `CE_AUTOMERGE_KILL_SWITCH=true`
(`validators/creator_engine_validator/ce_cli.py:4230-4236`). It disables all
automerge classes, not one tier.

## 2. Candidate Next Tiers, Risk Ascending

### Tier A: Carrier/Changelog-Only Mechanical Regens

Recommendation: approve as an explicit sub-tier only if the Operator wants
separate kill-switching and audit labels for a subset that is already inside
today's `docs` class.

Machine-checkable PR-class predicate:
all changed paths are under `.ce/changelog/**` and `.ce/pr-manifests/**`; at
least one `.ce/pr-manifests/<slug>.md` carrier exists; no path outside those
directories; carrier path manifest count/hash must match the final base..HEAD
path set using the existing fenced-manifest logic
(`validators/creator_engine_validator/checks/path_manifest_fidelity.py:76-105`,
`validators/creator_engine_validator/checks/path_manifest_fidelity.py:269-303`,
`validators/creator_engine_validator/checks/path_manifest_fidelity.py:324-358`).

Required evidence bundle:
`Validate governance artifacts` green
(`validators/creator_engine_validator/forge/automerge_mutation_policy.yaml:16-17`);
GitHub `reviewDecision=APPROVED`; author and approver distinct; declared work
class ceiling `XS` or `S`; mutation class must remain docs; path envelope limited
to `.ce/changelog/**` and `.ce/pr-manifests/**`; decision and actuator audit must
name `tier=carrier_changelog_mechanical`.

Review class:
existing independent review is sufficient; no additional specialist review.

Residual risk:
low, but stale or misleading carrier/changelog text can alter operator
coordination. The path-manifest verifier reduces path-set drift, but it does not
prove natural-language summary quality.

Blast radius if wrong:
coordination and audit narrative pollution for one PR; no source, workflow,
gate, or validator behavior changes if the path predicate is correct.

Rollback story:
turn off only `CE_AUTOMERGE_TIER_CARRIER_CHANGELOG=false` or the equivalent
per-tier class flag; global rollback remains `ce automerge-kill-switch on`.

### Tier B: Brain-Ledger Supersede Chores

Recommendation: approve only after adding a dedicated classifier/predicate and
audit fields. Do not include broad `.ce/brain/**`.

Machine-checkable PR-class predicate:
changed paths are exactly `.ce/brain/assertions.yaml`, one corresponding
`.ce/changelog/*.md`, and one corresponding `.ce/pr-manifests/*.md`; the ledger
diff contains only append-only records plus the minimal prior-record
`status: active -> superseded` and `superseded_by: <new-id>` change; new records
have contiguous `sequence`, correct `prev_hash`, correct `content_hash`, and no
forbidden host/credential/account/token fields. The existing ledger verifier
already models `record_count`, `active_count`, and head hash summaries
(`validators/creator_engine_validator/brain_runtime.py:122-138`,
`validators/creator_engine_validator/brain_runtime.py:807-842`), validates
authoritative ledgers before syncing
(`validators/creator_engine_validator/brain_runtime.py:344-389`), blocks
forbidden identifier keys
(`validators/creator_engine_validator/brain_runtime.py:414-440`), and validates
hash chain, sequence, and supersede targets
(`validators/creator_engine_validator/brain_runtime.py:443-525`). The actual
ledger shape uses `sequence`, `prev_hash`, `content_hash`, `status`, and
`superseded_by` fields in `.ce/brain/assertions.yaml:1-25` and an observed
supersede pair in `.ce/brain/assertions.yaml:1039-1080`.

Required evidence bundle:
`ce brain verify`/validator brain checks green; `Validate governance artifacts`
green; carrier path-manifest fidelity green; declared work class ceiling `XS`;
reviewDecision `APPROVED`; author/approver distinct; decision audit must include
old and new `record_count`, `active_count`, `head_content_hash`, and the exact
superseded IDs.

Review class:
independent review by a non-author is required; prefer brain/governance-aware
reviewer for the first canary tranche.

Work-class ceiling:
`XS` only for one supersede chain per PR. Multiple supersedes, new doctrine
scope, or doctrine-coverage changes require human merge.

Path envelope:
only `.ce/brain/assertions.yaml`, `.ce/changelog/<slug>.md`, and
`.ce/pr-manifests/<slug>.md`. Explicitly exclude `.ce/brain/doctrine-coverage.yaml`,
brain runtime code, recall indexes, embeddings, and generated state.

Residual risk:
medium-low. The change is data-only and hash-verified, but it changes the memory
substrate that governs future behavior and recall. A syntactically valid but
semantically wrong assertion can persist.

Blast radius if wrong:
future agents may recall or cite a bad doctrine assertion until superseded or
reverted; runtime code and credentials are not directly modified if the path
predicate holds.

Rollback story:
disable `CE_AUTOMERGE_TIER_BRAIN_SUPERSEDE`; if a bad PR lands, append a
correcting supersede record or revert the ledger/changelog/carrier PR, then
rerun brain verify.

### Tier C: Test-Only Diffs

Recommendation: approve as a canary only after adding a `test_only` policy tier
that is narrower than `code`; do not auto-merge under the existing `code` class.

Machine-checkable PR-class predicate:
all non-carrier changed paths are tests: `validators/tests/**`, or filenames
matching `test_*.py` or `*_test.py`; no production source, schema, workflow,
deploy, governance, identity, security, attestation, redaction, lockfile,
generated, vendored, or fixture-binary path; no changes to test runner
configuration or CI workflow. The current sizing floor has an internal test-path
recognizer for `validators/tests/**` and Python `test_`/`_test.py` names
(`validators/creator_engine_validator/checks/work_sizing_floor.py:85-92`), but
the current mutation classifier would still classify `validators/**` as `code`
(`validators/creator_engine_validator/forge/automerge_mutation_policy.yaml:24-30`),
so this requires a new predicate before ratification.

Required evidence bundle:
full `Validate governance artifacts` green; all existing required checks green
from the live actuator check path
(`validators/creator_engine_validator/forge/automerge_actuator.py:269-315`);
path predicate proof artifact listing every changed path and why it is test-only;
declared work class ceiling `XS` initially; independent review approved by
non-author; no `CHANGES_REQUESTED`.

Review class:
independent engineering review; for the first tranche, require a reviewer other
than the usual author seat and keep canary size to one PR at a time.

Work-class ceiling:
`XS` until observed clean for a fixed tranche; never above `S` without another
Operator decision.

Path envelope:
test files only plus required carrier/changelog. Exclude fixtures that can
change validator semantics through golden files unless a separate predicate can
prove they are passive expected outputs.

Residual risk:
medium. Test changes can remove coverage, weaken assertions, or encode new
expected behavior even when production code is untouched.

Blast radius if wrong:
CI quality can silently degrade; a bad test-only merge can make later production
regressions easier to land.

Rollback story:
disable `CE_AUTOMERGE_TIER_TEST_ONLY`; revert the test PR or restore prior tests;
rerun full validation and inspect subsequent PRs that depended on the weakened
tests.

### Tier D: Tiny Work-Class Code Diffs With Full Green + Independent Review

Recommendation: reject for now. Revisit only after lower tiers have audit
history and the actuator can enforce a path/semantic envelope more precise than
`code`.

Machine-checkable PR-class predicate:
declared work class `XS`; included source additions below the XS floor
threshold; no schema/deploy/governance/identity/security/attestation/redaction
paths; no workflow, gate, wall, release, credential, transport, sandbox, or
policy files; full required checks green; independent approval on current head.
The existing size classifier treats under 400 included changed lines as
`target_advisory`/`XS`
(`validators/creator_engine_validator/checks/work_sizing_floor.py:140-178`) and
the PR-diff floor uses `git diff --numstat --find-renames <base>..HEAD`
(`validators/creator_engine_validator/checks/work_sizing_floor.py:306-354`).

Required evidence bundle:
full validation green; live required checks re-read by actuator; independent
engineering review; current-head approval; source path manifest fidelity; a
machine-readable "not privileged surface" proof against the mutation policy
envelope.

Review class:
independent engineering review plus Operator merge remains the default. This
tier should not bypass the current `code` ceremony, which explicitly requires
`distinct_review, operator_merge`
(`validators/creator_engine_validator/work_sizing.py:72-74`).

Work-class ceiling:
`XS` only.

Path envelope:
non-privileged source under `validators/**`, `tools/**`, `src/**`, `app/**`,
`apps/**`, or `packages/**`, excluding any file that influences forge
credentials, GitHub mutations, validation sandboxing, workflow control, release
automation, or policy classification.

Residual risk:
high relative to the other candidates. Tiny code can still alter authority,
validation, or future merge behavior.

Blast radius if wrong:
repository behavior can change immediately; if the touched code is in
validation, forge, or queue surfaces, future PR gating can be compromised.

Rollback story:
keep human-gated. If ratified later, require `CE_AUTOMERGE_TIER_TINY_CODE` as a
separate opt-in, a one-click tier kill, and immediate revert of the landed PR on
bad actuation.

## 3. Kill-Switch and Observability Requirements

Global requirements:
retain the existing global `CE_AUTOMERGE_KILL_SWITCH` and CLI surface
(`validators/creator_engine_validator/ce_cli.py:4201-4257`), but add
independent tier flags so an Operator can disable one tier without disabling
docs-class automerge. The decision JSON and actuation audit must include:
`tier`, `tier_flag`, `tier_predicate_sha`, `path_envelope`, `evidence_bundle`,
`review_class`, `work_class_ceiling`, and the existing actuator fields from
`validators/creator_engine_validator/forge/automerge_actuator.py:404-446`.

Tier A kill switch:
`CE_AUTOMERGE_TIER_CARRIER_CHANGELOG=false`. Conformance audit line:
`status=Actuated reason=all_predicates_green decision=AUTO mutation_class=docs tier=carrier_changelog_mechanical tier_flag=true path_envelope=.ce/changelog,.ce/pr-manifests work_class in {XS,S} checks_green=true reviewDecision=APPROVED author_login!=approver_login`.

Tier B kill switch:
`CE_AUTOMERGE_TIER_BRAIN_SUPERSEDE=false`. Conformance audit line adds
`old_record_count`, `new_record_count`, `old_active_count`, `new_active_count`,
`old_head_content_hash`, `new_head_content_hash`, and `superseded_ids`, proving
append/supersede-only behavior.

Tier C kill switch:
`CE_AUTOMERGE_TIER_TEST_ONLY=false`. Conformance audit line adds
`test_only_paths=true`, `excluded_privileged_paths=0`,
`ci_config_paths_changed=false`, and `fixture_semantics=none|passive`.

Tier D kill switch:
do not ship. If ratified later, require `CE_AUTOMERGE_TIER_TINY_CODE=false` by
default and an audit line with `privileged_surface_paths=0`,
`operator_ratification_ref`, and `source_diff_ceiling=XS`.

## 4. Ratification Asks

1. Carrier/changelog-only mechanical regens: default `APPROVE-SPLIT-TIER`.
Create an explicit tier and per-tier kill switch for the already-docs subset;
keep existing independent review, full green, and XS/S ceiling.

2. Brain-ledger supersede chores: default `APPROVE-CANARY-AFTER-PREDICATE`.
Authorize implementation of a dedicated predicate for append/supersede-only
`.ce/brain/assertions.yaml` chores, XS-only, one supersede chain per PR, with
brain verifier summaries in the audit record.

3. Test-only diffs: default `APPROVE-CANARY-AFTER-PREDICATE`.
Authorize a new `test_only` tier, XS-only at first, with full validation,
independent review, explicit exclusion of CI/test-runner config, and per-tier
kill switch.

4. Tiny code diffs: default `REJECT-FOR-NOW`.
Keep code diffs human-gated under the current `distinct_review, operator_merge`
ceremony until lower-risk tiers have production audit history and a stricter
non-privileged source predicate exists.

## 5. Non-Goals: Human-Gated Regardless

Keep human-gated regardless of this proposal:
release creation, tag/signing/version publication, release artifact or
install-spec edits; gate, wall, queue, merge, auto-approve, reviewer authority,
or automerge policy/config changes; GitHub Actions workflow edits; mutation
policy envelope edits; schema/deploy/governance/identity/security/attestation
and redaction classes; credential, OpenBao, egress broker, transport, sandbox,
or daemon path changes; CODEOWNERS or reviewer registry changes; conveyor
arming, push, PR creation, or any action that lets landed content steer
privileged execution.

ADR-0004 supplies the standing safety constraint for future automation: payloads
from contained seats must be data-only, must not steer execution or authority,
working directories/remotes/base refs must be daemon-owned, validation must be
sandboxed and credentialless, transport authority must stay separated from
validation, and no auto-approve/merge authority is included without separate
Operator-ratified policy (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:55-88`,
`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:90-149`,
`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:151-167`,
`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:176-200`).
