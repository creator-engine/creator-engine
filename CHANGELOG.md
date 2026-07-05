# Changelog

All notable release-surface changes for Creator Engine are recorded here.
This file follows the public product-tag direction; internal Creator Engine
G2.* gate identifiers remain roadmap/governance work IDs, not public semver.

## [Unreleased]

(nothing yet — use this section for features landing after 0.3.2 while waiting for the next tag)

## v0.3.2 — release-automation + brownfield-installer hardening (2026-07-05)

Folds forward the parked brownfield-enabled-default schema clarification and the rc2-branch surfaces-manifest/staging fixes, and rolls up the accumulated 146 changelog fragments merged to main since the 0.3.1 tag (release automation, onboarding/installer hardening, launch-runtime and triage-queue work, and CI/governance tooling).

### Added

- **ce-375-scope-impact-p0** (ce-ops#375; validator tooling): **Warning-only Scope impact propagation.**

  - Added optional Scope downstream references and a warning-only impact drift check for ratified Scope records.
- **ce-conveyor-harvest-core** (ce-conveyor; conveyor harvest): **Conveyor harvest core.**

  - Added the slice-1 local conveyor harvest prep helper, design plan, and focused unit coverage.
- **ce-l3-triage-ready-queue-p0** (advisory ce-ops triage queue): Adds the P0 advisory Triage Ready Queue for inbound `creator-engine/ce-ops`
  issues.

  - New hidden `ce triage queue scan|inspect` commands classify recently updated
    open issues and render an advisory queue state.
  - New `ce_ops_triage_queue` runtime reuses `forge_triage.normalize_issue`,
    `_infer_work_class`, `_infer_mutation_class`, and `readiness_blockers` instead
    of forking classification logic.
  - Scheduled workflow runs every 30 minutes in dry-run mode by default, with
    manual `apply=true` available to patch an existing sentinel comment and upload
    local audit evidence.

  The queue is advisory only: it does not ratify, approve, review, merge,
  authorize dispatch, or block CI.
- **ce-l7a-auto-tag** (L7-a; release automation): **Add automatic release tag workflow.**

  - Adds a main-push workflow that reads the validator version source with AST parsing and creates an annotated release tag only for stable semver versions.
  - Adds static contract coverage for tag absence checks, non-semver skips, and contents write permission.
- **ce-l7b-finalize** (L7/day-arc; release automation): **Finalize signed release publish workflow.**

  - Adds a release-finalize workflow that verifies the Operator supplied public detached signature, copies finalized artifacts into docs/, and opens a release-publish PR.
  - Adds guarded reviewer-token approval and auto-merge wiring for the publish PR.
  - Covers the workflow with static unit contract tests.
- **ce-351-queue-daemon-relocation** (ce-ops#351; deploy/queue-daemon): **Durable queue daemon relocation package.**

  - Added a boot-persistent systemd unit for the merge-queue daemon with
    `Restart=always`, journald logging, OpenBao address wiring, and secret loading
    through a host-only environment file.
  - Added a fail-closed launcher with `--health` checks for daemon liveness,
    GitHub token validity, and OpenBao token validity.
  - Added a controller runbook for CE-DEV-1 cutover, approval auto-merge
    verification, DGX retirement, and rollback to DGX.
- **ce-automerge-kill-switch-cli** (L2 auto-merge P1; forge autonomy): **Automerge kill-switch CLI.**

  - **Declared work class:** S
  - Added `ce automerge-kill-switch status|on|off` over the durable live-policy state store.
  - Classified the governed operator kill switch as internal-only while keeping CLI inventory guards explicit.
  - Preserved actuator gate behavior while adding fail-closed operator fallback guidance for failed disarm writes.
- **ce-triage-autolabel** (ce-ops#67; ce-ops triage queue advisory labels): **Add advisory classification labels to the ce-ops triage queue.**

  - Apply-mode now synchronizes deterministic `wc:` and `triage:` issue labels from the existing advisory queue classification.
  - Dry-runs report the would-be managed label delta without writing labels.
  - Label errors are recorded per issue so the advisory queue can continue posting.
- **ce-166-doctrine-coverage** (ce-ops#166; knowledge-ssot doctrine coverage): **Add brain doctrine coverage ratchet.**

  - Add a deterministic doctrine coverage ratchet for governed contract docs.
  - Seed current uncovered doctrine files as explicit exceptions while requiring new doctrine to be asserted or acknowledged; the ratchet only shrinks.
- **ce-361-installer-mirror-policy** (ce-ops#361; release policy): **Codify installer mirror release policy.**

  - Added a draft release policy section for installer mirror immutability, emergency republish exceptions, audit evidence, and signed-release handling.
- **ce-388-conveyor-redesign-adr** (ce-ops#388; conveyor daemon security-redesign ADR): **conveyor daemon security-redesign ADR.**

  Added ADR-0004 proposing the conveyor daemon arm-safety-by-construction model.
  The ADR makes discovery payloads data-only, moves checkout and git/gh authority
  to daemon-owned working directories and pinned daemon config, treats imported
  bundle contents as untrusted validation input, and blocks G-N3 arming until an
  independent security review ratifies explicit arming criteria.
- **ce-398-controller-standup-docs** (ce-ops#398; controller playbooks): **Controller standup duty manifest and runbook.**

  - Added a machine-readable controller duty manifest for replacement-controller standup.
  - Added a self-verifying standup runbook with shadow-only gate authority until the A5 lock primitive lands.
- **ce-n2-triage-pickup-filter** (advisory ce-ops triage pickup filter): Adds an advisory ready-to-dispatch pickup filter to the ce-ops triage queue.

  - New pure pickup-candidate projection reuses the existing triage queue
    classifier/readiness path and `forge_triage.readiness_blockers` instead of
    forking readiness logic.
  - Existing triage queue scan JSON now includes a `pickup` payload containing
    issue numbers, labels, work class, mutation class, lane, and readiness for
    ready, unblocked, unassigned candidates only.
  - Unit coverage verifies ready inclusion, blocked/assigned/in-progress
    exclusion, deterministic ordering, dry-run/no-mutation behavior, and empty
    output.

  The filter is advisory only and does not authorize dispatch or perform any new
  forge mutations.
- **ce-294-press-merge-bundle** (ce-ops#294; forge evidence): **Press-merge evidence bundle v1.**

  - Added the read-only press-merge evidence bundle assembler, schema, hidden inert renderer, workflow artifact upload, and focused tests.
  - Captures the known validate-pr durability gap honestly with validation.available=false.
- **ce-410-alloc-core** (ce-ops#410; validator forge daemon allocation): **Daemon path allocation core.**

  - Added standalone daemon path allocation value objects, receipt verification, randomized runtime-root allocations, and cleanup mechanics for CE-410 slice 1.
- **ce-413-automerge-tier-b** (ce-ops#413; forge automerge): **Auto-merge Tier B brain supersede chores.**

  - Added the gated brain-ledger supersede automerge tier predicate and actuator re-verification.
  - Kept the tier flag default off and added focused policy and actuator coverage.
- **ce-422-tenant-record-schema** (ce-ops#422; validator tenant records): **Add tenant record schema and validator.**

  - Added the `tenant-record` schema with closed-object validation for tenant identity, credential references, confidentiality posture, issue venue, fleet allocation, and governance ratification fields.
  - Added the `tenant_record` validator check, a fictional well-formed tenant example, and focused unit coverage for required sections, pointer-only credential refs, unknown keys, enum failures, and ratification digest shape.
- **ce-388-conveyor-discovery** (ce-388; conveyor daemon discovery): **Add seat-signal discovery for conveyor harvest pickup.**

  - Adds a `ConveyorSeatDiscoveryRunner` that probes daemon-owned seat commands,
    parses `READY-FOR-HARVEST` pane signals, validates canonical branch slugs,
    and emits only the four data fields accepted by the conveyor payload schema.
  - Adds daemon-owned JSON dedupe state for processed `(seat_id, branch, sha)`
    triples, with corrupt-state recovery and atomic tmp-plus-rename writes.
  - Covers ANSI, bullet, wrapped-line, placeholder, diff-echo, last-signal-wins,
    hostile pane text, schema compatibility, and slug-mismatch behavior with
    focused unit tests.
- **ce-388-conveyor-harvest-daemon** (ce-ops#388; conveyor daemon): **Conveyor harvest daemon shadow-mode launcher and entrypoint.**

  - Added the shadow-mode conveyor harvest daemon entrypoint, launcher, service unit, container adapter wiring, and unit coverage.
- **ce-437-s4-runtime-image** (ce-ops#437; deploy/runtime-image): **Publish canonical multi-arch runtime image.**

  - Added the canonical runtime image Dockerfile, GHCR multi-arch publish workflow, consumer digest-pin contract, and focused static validation.
- **ce-443-stuck-lease-runbook** (ce-ops#443; playbooks/controller/runbooks): **Add conveyor daemon stuck-lease recovery runbook.**

  - Added an operator runbook for `DaemonLeaseStale` after an exit-74 heartbeat
    crash, including the fail-closed rationale, `pgrep` live-process checks,
    stale lease removal, launcher relaunch, and the armed semantics of
    `--one-shot`.
  - Consolidated the duplicate "Stuck Lease Recovery" section in
    `deploy/conveyor-daemon/RUNBOOK.md` down to a short symptom + pointer at
    this canonical runbook, and migrated the live-lease refusal message (a
    fact that existed only in the older doc) into the Symptom section here.
- **ce-s1a-docker-runner-backend** (ce-s1a-docker-runner-backend; runtime/runner): **Add plain Docker contained runner backend.**

  - Added a `docker` runner backend that uses the runtime policy's digest-pinned
    image, adds no Docker `--runtime=` flag, and bind-mounts only the policy mount
    manifest.
  - Registered `docker` through runtime policy resolution and the visible runtime
    bridge while preserving raw-fallback refusals for unsupported backends.
  - Extended the runtime-policy contract with `docker` and the ratified
    `controller` role enum addition, with hermetic unit coverage for translation,
    refusal, and bridge composition.
  - Push-readiness follow-up: baselined the `runner.docker_backend` v3 taxonomy
    classification in `_versions.py` and regenerated the CLI/schema autogen
    reference docs so the version-boundary and autogen-sync gates pass clean.
  - Review-pickup follow-up: locked the latent `network=='proxy'` docker-argv
    branch to fail closed (docker-side egress mediation is not implemented) with
    a regression test, and added an Operator-ratified (2026-07-05 day-arc)
    decision citation next to the `controller` role-enum addition in the schema
    and contract doc (see those files for the ticket reference).
- **ce-s1b-seat-image** (operator-ratified day-arc; tenant seat image): **Canonical tenant seat image.**

  - Added the canonical tenant seat image derived from the digest-pinned runtime image.
  - Added static tests and publish workflow coverage for the seat image contract.
- **ce-s1c-launch-default-policy** (ce-s1c-launch-default-policy; runtime/launch): **Default controller launch to onboarded runtime policy.**

  - `ce onboard --apply` now emits a real default controller
    `runtime-policy-record` beside the legacy runtime posture marker.
  - Live `ce launch` resolves the onboarded record by default, validates it, and
    composes the existing visible runtime backend bridge; missing records fail
    closed with onboarding remediation and the explicit `--backend host` opt-out.
  - Documented the well-known runtime-policy path and updated launch tests for
    default Docker composition, host opt-out, missing-record refusal, and dry-run
    behavior.
  - Review fix: a present-but-corrupt onboarded record (missing/mismatched
    `kind`, or non-mapping content) no longer silently falls through to an
    ungoverned raw launch — it now refuses with a distinct, actionable message
    separate from the absent-record case.


- **ce-conveyor-bundle-landing** (ce-conveyor; conveyor): **Conveyor bundle landing.**

  - Added local bundle landing for conveyor harvest branches.
- **ce-conveyor-golive** (ce-conveyor; conveyor): **Conveyor go-live daemon core.**

  - Added a disarmed-by-default conveyor daemon that plans completed-branch harvests without mutation.
  - Added armed harvest-to-land-to-push-to-PR execution through injected runners, with append-only mutation ledger records for push and PR-open attempts.


- **ce-l7e-parity** (L7/day-arc; release automation): **Add release parity promotion gate.**

  - Adds a post-finalize release parity workflow that waits for Pages propagation, verifies the live signed release against checked-out docs and the release tag SHA chain, then promotes the draft GitHub release to latest.
  - Closes the matching AWAITING-OPERATOR signing issue only after parity passes.
- **ce-166-d1b-brain-batch1** (ce-166; brain-assertion-ledger): **D1b brain migration batch 1.**

  - Encoded supported D1b doctrine items as static brain assertions.
  - Removed doctrine-coverage exceptions now covered by active static assertions.
  - Left unsupported current-main claims out of the ledger for follow-up.
- **ce-367-ce-native-init** (ce-ops#367; ce-init): **CE-native ce init project scaffolding.**

  - Adds the public CE-native `ce init` project scaffold with embedded offline templates, right-sized work-class artifacts, stage vocabulary, changelog/path-manifest templates, and local CE skills.
  - Updates README/docs reconciliation and regenerates the CLI reference for the new surface.
  - Refuses `ce init` template writes when a symlink would resolve outside the target project root.
- **ce-369-denylist-from-ssot** (ce-369; validators): **Generate the identity denylist from registry source at runtime.**

  - Added a required-registry generator that writes the CE-internal identity denylist only as a gitignored runtime artifact where the private ce-ops registry is available.
  - Updated the fleet manifest guard to fail open with an explicit advisory when that runtime artifact is absent, while preserving structural regex protections and using generated runtime data when present.
  - Removed the committed generated artifact and package-data shipping for it; committed content no longer carries registry-derived identity summaries.
  - Added a scheduled freshness workflow that checks out ce-ops with `secrets.CE_OPS_READ_TOKEN`, generates the runtime artifact, and verifies it against the private registry without auto-push or auto-PR behavior.
  - Design: default gitignored-artifact approach (not keyed-HMAC) — the round-1 rework replaced a committed unsalted-sha256 denylist with a runtime-only, plaintext-token artifact that is generated on demand from the private registry and never packaged or committed; the artifact loader rejects any 64-hex-digest-shaped token to guard against reintroducing hashed identifiers.
  - Superseded the d1b-39 brain assertion again to re-pin `validators/pyproject.toml` after the rework removed generated artifact package data (squashed on harvest merge: the round-1 v2->v3 intermediate state was corrected by the rework back to byte-identical pyproject.toml content, so the landed ledger carries a single v2(tombstone)->v4(active) supersede instead of two chained hops).
- **ce-410-s8b-sandbox-runner** (creator-engine/ce-ops#410; validation-sandbox): **slice 8b validation sandbox runner.**

  - Promotes the rootless Podman verification worker-container policy.
  - Adds a containerized validation sandbox runner with signed receipts and side-effect ledger recording.
  - Covers the runner with offline unit tests using injected launcher and ledger seams.
- **ce-410-s9-ledger-binding-seam** (creator-engine/ce-ops#410; conveyor-daemon): **slice 9 ledger binding seam.**

  - Requires the validation ledger binding seam for armed conveyor daemon construction.
  - Adds unit coverage for armed refusal and disarmed construction without the seam.
- **ce-437-portability-guard** (validators): Added a control-plane portability guard that blocks undeclared Linux runtime-plane
  assumptions in validator modules while preserving current debt through explicit
  runtime-plane declarations and dated baseline exemptions.

  Reworked command detection to catch wrapped or absolute-path runtime commands and
  added fail-closed manifest coverage for missing, malformed, and stale baseline
  entries.
- **ce-n5-worktree-prune** (ce-ops#N5; validators): **Add fail-safe worktree prune tool.**

  - Added `ce worker worktree-prune` (dry-run by default; `--apply` required for destructive action).
  - Classification uses three-dot content diff vs origin/main (not ancestry alone); dirty/unpushed worktrees are report-only, never touched.
  - Fixes a self-delete defect found in internal review: apply_prune() previously only protected the primary worktree, not the actively-invoking linked worktree; now both are protected (see test_apply_never_removes_invocation_linked_worktree).
  - Hardened invocation-worktree protection to derive independently from the process cwd (symlink-safe, walked to its containing worktree root), not just from `--repo-root`, so a `--repo-root`-pointed worktree A never causes removal of the cwd's own worktree B.
  - Added `empty-tip-content` regression coverage (content-identical-but-diverged branch tip → prunable) and its inverse (diverged and non-empty tip content → `REPORT_ONLY`/`unpushed-commits`), proving the content check gates pruning, not ancestry.
  - Locked registered worktrees are now surfaced as their own `REPORT_ONLY`/`locked` verdict.
- **ce-434-contained-seat-profile** (ce-ops#434; governance): **validate-pr contained-seat profile for harvest-side carriers.**

  - Add `ce validate-pr --profile contained-seat`, a narrow profile that runs the normal preflight while tolerating only `path_manifest_carrier_required` because contained-seat carriers are generated harvest-side.
  - Choose a named profile instead of a general skip flag so validate-pr stays fail-closed: unknown profiles are refused and no broad check-skipping surface is introduced.
  - Keep the profile parseable but hidden from generated CLI help so the existing committed CLI reference remains unchanged.
  - Keep default `ce validate-pr` behavior byte-identical with no profile, and cover the profile, notice line, and refusal paths in validate-pr tests.
- **ce-453-preflight-skip-transparency** (ce-ops#453; validators): **preflight skipped-test transparency.**

  - Report skipped tests from the PR preflight baseline-diff test gate with file counts and pytest -rs reasons when available.
  - Keep skipped tests transparent rather than failing the preflight, and carry the skip count into the final PASS summary.
  - Cover default, zero-skip, and contained-seat profile behavior.

### Changed

- **ce-372-autoupdate-test-hygiene** (ce-ops#372; signed updater tests): **Auto-update startup notice test hygiene.**

  - **Declared work class:** tiny
  - Replaced the startup notice test's hardcoded cache path with pytest tmp_path.
  - Added cached notice_shown coverage so a fresh shown cache suppresses a second notice.
- **ce-374-prepitch-docs-slice** (ce-374-prepitch-docs-slice; public docs overview): **Rendered Creator Engine overview docs page.**

  - Add a styled public overview page for Creator Engine.
  - Link the rendered page from the existing docs section without removing existing markdown docs links.
  - Include a public-safe architecture-at-a-glance diagram for controller, seats, forge, and containment.
  - Update the docs navigation test so the docs section keeps required markdown links and explicitly permits this rendered overview page.
- **ce-380-dgx-launcher-image-guard** (ce-ops#380; validator surfaces manifest guard): **DGX launcher image manifest guard.**

  - Generalized the runsc image default guard across launcher scripts.
  - Added DGX launcher coverage for manifest-aligned and divergent defaults.
- **ce-dev4-surface-update** (ce-ops#377; deploy): **DGX seat image: openssh-client + PyNaCl; codex 0.142.4.**

  Fix contained DGX codex seat (missing ssh-keygen + PyNaCl); codex surface + tag 0.142.4; arm64 base-digest override pending ce-ops#377.
- **ce-l2-automerge-canary-livedata** (L2; automerge canary live-data decision inputs): **Wire live PR data into the automerge canary decision path.**

  - **Declared work class:** S
  - Added pull-request-only live review, approver, declared work-class, and check evidence for automerge decisions.
  - Kept merge-group and query-error paths fail-closed with empty advisory evidence.
  - Reused shared work-class normalization for canary XS/S and legacy tiny/story acceptance.
- **ce-workclass-xsml** (L10; work-sizing validator vocabulary): **Migrate work-class vocabulary to XS/S/M/L.**

  - **Declared work class:** XS
  - Renamed canonical work-class vocabulary from tiny/story/feature/epic to XS/S/M/L without changing included-diff-LOC thresholds.
  - Preserved legacy PR-body and gate aliases for the migration window.
  - Updated validator tests, docs, templates, brain assertions, and generated references for the canonical labels.
- **ce-contributing-guide-ci-steps** (ce-contributing-guide-ci-steps; docs): **Document first-PR CI steps in the contributing guide.**

  - Document the required declared work class line, per-PR changelog fragment, and local `ce validate-pr` preflight for first PRs.
- **ce-339-libsodium-dockerfile** (ce-ops#339; deploy/dgx-runsc Dockerfile): **Add libsodium runtime package to DGX seat image.**

  - Adds Debian bookworm runtime package `libsodium23` to the DGX seat image runtime apt package list.
  - Uses the runtime library package rather than `libsodium-dev` because no headers are needed.
  - CE-TEST-COUPLING-EXEMPT: Dockerfile-only infrastructure change; no testable application logic changed.
  - Follow-on controller step: rebuild the DGX seat image and relaunch dev-4 after this Dockerfile change lands.
  - **Declared work class:** XS
- **ce-385-workclass-doc-vocab** (creator-engine/ce-ops#385; docs authoring): **docs: update work-class authoring vocabulary.**

  - Updated author-facing work-class references to the current XS/S/M/L taxonomy.
- **ce-395-bump-to-main** (ce-ops#395; release): **Add release-bump commit mode.**

  - Add release-bump commit mode that creates a fresh local branch, commits only canonical version sources, and generates PR carriers without pushing or opening a PR.
  - Delete the orphaned release_orchestrate module.
- **ce-407-pin-migration-s1** (ce-ops#407; brain assertion verification): **Migrate pr_preflight brain pins to probes.**

  - Migrates d1b-01, d1b-42, and d1b-43 from pr_preflight.py hash pins to focused probe verification.
  - Registers pr_preflight probe checks and updates the authoritative brain drift ratchet.
- **ce-407-pin-migration-s2** (ce-ops#407; brain assertion verification): **Migrate integrator belt brain pins to probes.**

  - Migrates d1b-10, d1b-11, and d1b-12 from integrator_belt.py hash pins to focused probe verification.
  - Registers integrator belt probe checks and updates the authoritative brain drift ratchet.
- **ce-410-authority-contexts-core** (ce-ops#410; validators): **Typed authority contexts for integrator credentials.**

  - Added typed authority contexts for transport, local git, and validation sandbox boundaries.
  - Removed process-global GH_TOKEN mutation from the integrator gh runner shim.
  - Wired queue-poll and live action construction through explicit context values.
- **ce-410-conveyor-phase-authority** (ce-ops#410; conveyor): **Type conveyor git runner phases and pass explicit subprocess envs.**

  - Added conveyor-local git phase typing until authority_contexts.py lands.
  - Routed local git and validation subprocesses through explicit, scrubbed env mappings.
- **ce-410-integrator-git-phase-split** (ce-ops#410; forge/integrator-belt): **Split integrator git authority by phase.**

  - Route local integrator git commands through LocalGitContext while fetch, push, and ls-remote retain transport credentials.
  - Add regression coverage that records every git subprocess environment and rejects credential-bearing local git envs.
- **ce-412-automerge-tier-a** (ce-ops#412; automerge): **Auto-merge Tier A carrier/changelog split-tier.**

  - Added a default-off carrier/changelog automerge tier flag and path predicate.
  - Recorded tier metadata and reviewer venue in automerge decisions and actuator audit records.
  - Wired workflow policy materialization and unit coverage for Tier A.
- **ce-410-s8c-armed-wiring** (creator-engine/ce-ops#410; conveyor validation): **Conveyor armed-mode validation via sandbox runner.**

  - Wired armed conveyor validation through the validation sandbox runner and recorded receipts.
  - Committed generated carriers before armed sandbox validation so receipts bind the prepared tree.
  - Added an 8c interim fail-closed pre-push assertion: if the landed branch tip tree does not match the validation receipt tree, the item fails before push/PR open.
  - Strengthened fail-closed behavior: absence of a successful validation record now fails the item before any tree-sha comparison (absent = strict), before push/PR open.
  - Documented the 8c interim: slice 9 must promote `validation_ledger_binding` into the armed required-seam list.
  - Design SSOT `/var/tmp/CE410_SLICE8_SPIKE_DESIGN_20260704.md` (sha256 `15db27aa632b1e9f67806665ce8e961e88913186446d14b638c164fb1e5d600f`) assigns full publish reverify to slice 10: re-derive `tree_sha` immediately before push/PR and confirm it equals the receipt-bound tree, with per-phase audit trail.
- **ce-440-s2-cev3-deprecation** (creator-engine/ce-ops#440; validator CLI): **cev3 deprecation notice and internal-groups lock-in.**

  - Adds a direct cev3 invocation deprecation notice while suppressing it for ce forwarding shims.
  - Locks ce v3 forwarding shims out of internal-only command groups.
- **ce-440-s3a-docs-sweep** (ce-ops#440; docs): **Docs sweep to the unified ce command surface.**

  Replaced user-facing cev3 command examples with the unified ce surface.
- **ce-440-s3b-systemd-exec-migration** (ce-ops#440; systemd gate daemons): **Migrate repo systemd units from cev3 to ce.**

  - Migrated the integrator and review pickup systemd units to invoke the unified `ce` CLI surface while preserving daemon arguments.
  - Updated the gate daemon systemd test prefix assertion to allow `ce` and bash launchers only.
- **ce-440-s3c-migration-doc-snippets** (creator-engine/ce-ops#440; operations docs): **docs: align dogfood-migration systemd snippets with the unified ce surface.**

  - Aligns the dogfood migration guide's checked-in systemd examples with the unified `ce` console-script surface.
- **ce-444-queue-daemon-startup-lease** (ce-ops#444; validators/creator_engine_validator/v3_cli.py): **Fail-closed queue daemon startup lease.**

  - Added a default-on singleton lease to the Python `ce queue-daemon` entrypoint
    before the first daemon pass, including clean held/stale refusal output.
  - Added queue-daemon lease heartbeat and release coverage, plus operator
    recovery notes for stale lease cleanup.
  - The daemon now recognizes when its own singleton lease is already held by a
    live, verified ancestor process (its own launcher supervisor) and proceeds
    straight into normal startup instead of refusing — fixing a startup
    deadlock under the canonical launcher while keeping every other refusal
    path (unrelated live holder, stale lease) unchanged and fail-closed.
- **ce-445-c2-daemon-container-plumbing** (ce-ops#445; deploy/daemons): **Daemon container launcher env-file, CA-cert, and tmpfs secret custody plumbing.**

  - Added guarded `CE_DAEMON_ENV_FILE` support, read-only OpenBao CA cert remapping,
    and tmpfs-backed container paths for daemon secret file custody.
  - Extended daemon container runner tests for env-file refusal, CA cert mapping,
    tmpfs args, and byte-identical queue-daemon default argv compatibility.
- **ce-a3-docs-envelope-automerge** (ce-a3-docs-envelope-tiers; automerge policy): **Extend automerge docs envelope tier.**

  - Extend automerge policy and actuator rechecks to cover the ratified docs envelope for docs, root markdown, changelog, and PR manifest paths.
  - Add regression coverage for the #771 docs-envelope AUTO path set and code/work-class refusal cases.
- **ce-l3-triage-apply-completion** (ce-ops#67; ce-ops triage queue automation): **L3 triage apply-mode completion.**

  - Create the triage queue sentinel comment in apply mode when absent, then patch it on later runs.
  - Flip scheduled triage queue runs to apply mode with CE_TRIAGE_APPLY_KILL_SWITCH as the rollback switch.
  - Add unit coverage for exactly-once sentinel creation, scheduled kill-switch wiring, and bounded apply mutations.
- **ce-414-installer-doc-egress** (creator-engine/ce-ops#414; installer docs): **installer docs: version-symbolic release paths and egress allowlist.**

  - Documents version-symbolic release download paths and the manifest as the authority.
  - Adds the default one-liner egress allowlist to the installer contract and pilot runbook.
  - Shrinks the public-docs confidentiality ratchet after removing the stale public issue reference.
- **ce-434-playbook-contained-profile** (ce-434; controller dispatch playbook): Document the contained-seat validation profile in the dispatch playbook.

  - Contained seats whose carrier is generated harvest-side now get the real
    command: `ce validate-pr --profile contained-seat`.
  - The directive describes the profile as the full suite minus the harvest-side
    carrier gate, with the contained-seat carrier notice printed.
  - Non-contained seats and harvest/controller runs remain on full
    `ce validate-pr`; the standing preflight bar is unchanged.
- **ce-445-c5prep-daemon-smoke** (ce-ops#445; deploy/daemons): **Add daemon container stateful restart smoke coverage.**

  - Added a host-operator smoke script that runs the canonical daemon container
    adapter twice against one scratch state root and asserts lease release,
    reacquisition, Docker uid ownership, and (via a full recursive content scan
    of the scratch state root, not just known mount points) absence of the
    smoke's signing-secret content on host state after stop, with best-effort
    container/runner cleanup on any exit path.
  - Documented the daemon image uid ownership contract and first-boot Docker
    remediation in the daemon container README.
  - Aligned canonical image Dockerfile runtime dependency check order and added
    static/unit coverage for the smoke contract and Docker missing-root branch.
- **ce-801-installer-envvar-docs** (installer docs): **installer docs: enumerate gate-daemon env-file variables.**

  - Adds the installer contract's gate-daemon env-file variable list, including the full OpenBao-backed review-pickup SecretRef set.
- **ce-compliance-doc-version-refs** (ce-compliance-doc-version-refs; docs): **Use version-symbolic compliance evidence refs.**

  Replaced stale hardcoded download-release paths in the SSDF/SLSA conformance
  matrix with the current-release convention used by the installer contract.
- **ce-docs-stale-wheel-envvar** (ce-docs-stale-wheel-envvar; docs): **Document the stale-wheel override in contributor setup.**

  - Explain that stale installed validator wheels can refuse gate commands when the source checkout is newer.
  - Name `CE_ALLOW_STALE_WHEEL=1` as the explicit one-off override and keep reinstalling or updating the wheel as the durable fix.
- **ce-runner-helper-dedup** (ce-ops#447; runner docker gvisor translation): **Deduplicate Docker runner translation helpers.**

  - Hoist shared mount, policy-field, and launch-probe translation helpers into a public runner seam.
  - Route both plain Docker and gVisor proxy backends through the shared helpers without changing rendered argv semantics.

### Fixed

- **ce-l4-launch-hydration-fallback** (ce-L4; validator launch runtime): **Launch hydration deterministic fallback.**

  - Retry Controller launch recall hydration with the deterministic default store when vllm-openai is unavailable or dimension-mismatched.
  - Cover deterministic fallback and rebuild-stable keyword/graph recall invariants.
- **ce-351-launcher-argparity** (ce-ops#351; deploy / queue-daemon launcher (config/infra)): **Fix arg-parity gap in queue-daemon relocation launcher — wire missing `--approval-wall-secret-ref-policy-sha`.**

  - **`deploy/queue-daemon/launch-queue-daemon.sh`** — added `--approval-wall-secret-ref-policy-sha`
    arg (sourced from new required env var `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA`); added the
    var to `validate_required_env` and the usage/help block.  Without this arg the relocated VPS
    daemon would fail to fetch the approval-wall secret from OpenBao on cutover, silently blocking
    all auto-merges.
  - **`deploy/queue-daemon/RELOCATION.md`** — added `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA` to
    the required-keys section of the cutover runbook so operators populate it in the env file.

  No change to fail-closed logic, secret handling, or unrelated args.  The `--json` arg was
  already present in the launcher; confirmed not missing.
- **ce-373-subprocess-timeouts** (ce-ops#373; validator preflight): **Bound validate-pr network subprocess calls.**

  - Added a shared network subprocess timeout override for validate-pr and live onboard GH/git network calls.
  - Surfaced simulated subprocess timeouts as actionable preflight/onboard errors instead of hangs.
  - **Declared work class:** M
- **ce-337-selfpush-canary** (ce-ops#337; vps-runsc egress broker): **Self-push broker stable socket mount and canary.**

  - Fixes the VPS launcher to mount broker socket directories instead of restart-sensitive socket inodes.
  - Adds a contained self-push canary that fails on stale broker sockets, broker refusal, or non-no-op responses when requested.
  - Documents live diagnosis: dev-3 broker services were running, but the container-held push/review socket mounts returned ECONNREFUSED after daemon restarts.
- **ce-386-wheelhouse-xdist-group** (ce-ops#386; validator tests): **Serialize wheelhouse built-surface tests under xdist.**

  - Added the wheel-build xdist group to the built-surface wheelhouse tests and the packaging contract wheel parity test so shared source-tree wheel builds serialize under loadgroup.
- **ce-386-xdist-wheelbuild** (ce-ops#386; validator tests): **Serialize wheelhouse built-surface wheel builds under xdist.**

  - Mirrored the wheel-build xdist grouping style from test_wheel_bake.py on built-surface tests that invoke source wheel builds.
- **ce-387-holdlabel-symmetry** (ce-ops#387; forge controller inbox): **Hold-label symmetry for controller inbox.**

  - Reused the full shared issue-side blocking hold-label union for PR awaiting-operator classification.
  - Covered PR labels without body markers across the union: `wip`, `blocked`, `waiting`,
    `status:*` variants such as `status:checkpoint`, `do-not-claim`,
    `dependency-blocked`, existing awaiting-operator labels (`awaiting-operator`,
    `hold`, `awaiting-operator/hold`), and held/on-hold aliases including case variants.
- **ce-388-payload-data-only** (ce-ops#388; validators/conveyor-daemon): **Wire ADR-0004 payload schema into conveyor daemon discovery.**

  - Wired ConveyorDaemonItem.from_mapping() through the ADR-0004 data-only schema before raw discovery field access.
  - Legacy command, base, remote, and path-bearing discovery mappings now reject with value-free audit records.
  - Schema-rejected discovery items are isolated per item so one bad payload cannot drop the rest of the batch.
  - Added daemon and schema regressions for missing, typed, non-mapping, and legacy-control payload failures.
  - Superseded d1b-10, d1b-11, and d1b-12 brain assertions to re-pin integrator belt evidence for this branch.
- **ce-390-confidentiality-scanner-coverage** (ce-ops#390; public-repo confidentiality scanner): **Widen public-repo confidentiality scan to all tracked text files.**

  Widened the public-repo confidentiality scanner from a docs-only extension allowlist to full coverage of all git-tracked text files, closing a gap where confidential ce-ops#N ticket references or other forbidden patterns could leak through non-doc file types.

  - Full-coverage widening: scan now walks all tracked text files (binary-sentinel skipped) instead of a fixed docs-suffix allowlist.
  - Structural carrier exemption accepts both the bare `ce-ops#N` and the repo-qualified `creator-engine/ce-ops#N` forms in generated changelog frontmatter (`issue:` line) and PR-manifest headers only; the same ticket ref appearing in body prose still fails closed.
  - Scan errors (unreadable file, forbidden-pattern match failure) fail closed rather than being silently skipped.
  - Pre-existing tracked-text baseline hits are allowlisted via the existing debt-ratchet mechanism; remediation is tracked internally, not via a new external program.
  - Adds 3 new tests proving qualified-form frontmatter/header refs pass with an empty allowlist, plus 3 companion tests for the existing bare-form + qualified-body-prose-fails coverage.
- **ce-391-triage-advisory-text** (ce-ops#391; validator cli): **Surface commissioned unscheduled pickup triage advisory text.**

  - Added plain-text `ce pickup triage` output for commissioned unscheduled advisory count and issue details, matching the existing JSON payload signal.
- **ce-402-preflight-failclosed** (ce-ops#402; validator preflight): **Fail closed when baseline-diff pytest does not execute tests.**

  - Makes the validate-pr baseline-diff gate fail closed when pytest is missing, crashes, or collects zero tests.
  - Preserves zero-new-failures behavior for genuine identical pytest failures after tests execute.
  - authoring-doc line deferred -- rides the brain-migration lane
  - Supersedes the three preflight brain assertions so their evidence hashes match the fail-closed preflight runner.
- **ce-404-wall-remint-on-head-mismatch** (ce-404; integrator belt): **Wall remint on head mismatch.**

  - Treat stale approval-capability markers with `head_mismatch` as remintable only when a trusted authorized current-head approval exists.
  - Emit `head_mismatch_no_current_approval` when a stale marker cannot be reminted because no trusted current-head approval is present.
  - Supersede d1b-10, d1b-11, and d1b-12 brain assertions to re-pin integrator belt evidence for this branch.
- **ce-brain-chained-supersede** (ce-brain-chained-supersede; brain runtime): **Chained brain assertion supersedes.**

  - Fixed the single-level supersede cap in brain assertion current-view validation.
  - Relaxed only superseded_by target resolution: supersede chains may pass through superseded records, but must terminate at exactly one active assertion; cycles are rejected.
  - This unblocks evidence re-pins on assertions already at -v2 without changing append mechanics, record shape, or ledger content.
- **ce-410-conveyor-alloc-wire** (ce-ops#410; conveyor daemon allocation provenance): **slice 2: conveyor daemon allocation receipts (armed-path provenance).**

  - Replaced the default-true `daemon_owned_paths_allocated` bit with `DaemonPathAllocator` receipts; raw discovery mappings via `from_mapping` stay data-only.
  - Armed conveyor construction now refuses without an injected allocator; armed runs allocate receipted paths for data-only items before prepare/land/push/PR and reject direct item paths lacking a valid receipt for the current allocator instance.
  - Retained confinement checks as defense-in-depth alongside allocator receipts.
  - Added secret-free allocation audit logging (allocation id, item key, root-relative paths, mode-check results, cleanup status).
- **ce-410-integrator-alloc-wire** (ce-ops#410; integrator belt live-repair workspace allocation): **slice 3: integrator workspace allocation via daemon receipts.**

  - Replaced predictable --work-root repair paths with daemon allocator-issued randomized workspaces (allocator.allocate_integrator_workspace receipts).
  - Added fail-closed --runtime-root queue-poll wiring and explicit --work-root refusal.
  - Cleanup now only proceeds by receipt (no rmtree of deterministic paths).
  - Added offline coverage for allocator-backed workspaces, receipt cleanup, and unsafe runtime roots.
  - Consumes the daemon path allocator module landed in the prior slice (#758) read-only.
- **ce-388-fastfollow-lease-ux** (ce-ops#388; conveyor daemon): **Fast-follow conveyor daemon lease UX and one-shot launcher flag.**

  - Added clean direct-entrypoint lease refusal handling with exit 73.
  - Renamed the launcher finite-pass flag to `--one-shot` and made `--dry-run` fail closed.
  - Documented stuck lease verification and recovery.
- **ce-415-brownfield-enabled-fix** (ce-415; installer brownfield inventory): Derive `brownfield.enabled` from real brownfield probe signals instead of
  defaulting empty probes to true. Empty non-git directories now report disabled
  brownfield adoption, while detected Git history, workflows, or test commands
  enable the brownfield inventory.
- **ce-417-pilot-runbook-gaps** (creator-engine/ce-ops#417; pilot documentation): **Document pilot brownfield apply prerequisites.**

  - Corrected the solo-pilot sudo guidance so the default os-native backend does not imply an unused privileged install.
  - Added pilot-facing brownfield apply prerequisites, clone/cd guidance, and the live-driver App-token permission nuance.
- **ce-428-client-workflow-template** (ce-ops#428; onboard apply emits a client-repo CE validation workflow): **client workflow template for adopted repos.**

  - Replaces the adopted-repo workflow with a signed-download wheel install and `ce check .ce/`.
  - Pins the temporary client-profile tolerate list to the four CE-resident checks pending the client-profile follow-up.
- **ce-429-repo-root-forward** (ce-ops#429; forge automerge): **Forward automerge repo root.**

  - Forwarded the parsed automerge decide --repo-root value into policy decision evaluation.
  - Added CLI coverage from a non-root working directory.
- **ce-445-daemon-container-test-gaps** (ce-ops#445; validators): **daemon container env-file/cacert refusal tests and conveyor invocation pin.**

  - Added daemon container launcher coverage for missing CE_DAEMON_ENV_FILE and CE_DAEMON_CACERT_FILE refusal paths, asserting clean stderr and no container engine invocation.
  - Added a byte-identical default conveyor-daemon invocation pin to preserve existing behavior when optional plumbing variables are unset.
- **ce-445-g10-image-daemon-deps** (ce-ops#445; deploy): **Bundle gate-daemon runtime dependencies in canonical images.**

  - Install GitHub CLI from the official signed apt repository in both canonical runtime Dockerfiles while preserving offline validator wheel builds.
  - Keep `git` installed and add static Dockerfile-content tests for the `gh` keyring/repository pins in `validators/tests/unit/test_runtime_image.py` and `validators/tests/unit/test_oci_image.py`.
- **ce-445-g9-adapter-uid-model** (ce-ops#445; deploy/daemons): **Daemon container adapter uid and state-root ownership model for Docker.**

  - Declared the canonical daemon image uid/gid contract as `CE_DAEMON_IMAGE_UID`
    defaulting to `10001`, and run the container as that uid/gid.
  - Changed host-side daemon state prep to create missing roots only, verify
    existing roots without chmod, and fail closed on Docker uid mismatches with a
    copy-pasteable `chown -R <uid>:<uid> <state_root>` remediation.
  - Pinned queue and conveyor secret tmpfs mounts with `uid=`/`gid=` options and
    updated the byte-identical container argv tests for the deliberate argv change.
- **ce-brownfield-refusal-message** (ce-brownfield-refusal-message; validator cli): **Distinguish brownfield adoption credential-resolution refusals.**

  - Kept the no-escalation brownfield apply refusal text unchanged.
  - Added a distinct refusal when the dual adoption escalation env vars are set but App credentials cannot resolve, with remediation for kind: own PEM and kind: shared broker setups.
- **ce-docs-brownfield-answers-version** (brownfield adoption docs): **Show the required answers file version in the brownfield adoption example.**

  Add `answers_version: 1` to the documented brownfield answers fragment so the
  example starts with the schema-required version key before operators run
  `ce install --plan`.
- **ce-npm-path-fix** (live-canary; validator): **Fix npm profile PATH discovery.**

  - Replaced dynamic npm global-bin discovery with a stable prefix-derived path.
  - Added a directory-exists guard to the shared PATH prepend helper so missing or garbage paths are ignored.
  - Added regression coverage for rewriting the managed block and ignoring stdout error text from npm stubs.
  - Noted that `docs/install.sh` and `docs/downloads` mirrors embed a duplicated pre-fix copy of this block; those signed release surfaces are out of scope here and the fix rides the 0.3.2 re-sign.
- **ce-onboard-didyoumean-guard** (ce onboard CLI): **Hint installer-only flags to `ce install`.**

  - Refuse stale installer-flow flags passed to native `ce onboard` with exit 2 and a stderr hint to rerun the same arguments under `ce install`.
  - Keep native `ce onboard` dispatch unchanged for first-run orchestrator flags.


- **ce-370-local-preflight-pr-body** (ce-ops#370; validators): **Local validate-pr honors PR body test-coupling exemptions.**

  - Local `ce validate-pr` now sources PR body text for the test-coupling gate when available, matching CI exemption handling while preserving strict fallback behavior.
- **ce-377-per-arch-base-digests** (ce-ops#377; surfaces): **per-arch base-image digests.**

  - Pin Rust and Debian base-image digests per target architecture for VPS amd64 and DGX arm64 builds.
  - Teach surface rendering to select the base-image digest for the requested target architecture while preserving existing digest-map output for non-base surfaces.
  - Add a surfaces manifest guard for dual-arch base images.

  Follow-up: live DGX codex-runsc image reconciliation is deferred to dev-4.
- **ce-379-workclass-choices-compat** (ce-379; validators): **Work-class validator choices accept canonical and legacy names.**

  - Accept canonical XS/S/M/L and legacy tiny/story/feature/epic work-class inputs in validator preflight parser paths.
  - Reuse the shared WORK_CLASS_INPUTS alias set and normalize through normalize_work_class.
- **ce-n1d-sshkeygen-preflight** (ce-ops#197; install): **ssh-keygen prereq actionable error in verify paths.**

  Fail-closed ssh-keygen remediation in install-spec, update, v3 verify paths.
- **ce-379-workclass-preflight-parity** (ce-379; validators): **Local PR preflight mirrors canonical work-class names.**

  - Keep `ce validate-pr` help and carrier errors aligned with `XS/S/M/L` while documenting legacy aliases.
  - Add regression coverage proving canonical carrier lines and legacy aliases normalize through the same floor behavior.
- **ce-381-automerge-decide-pathset** (ce-ops#381; ci): **Automerge decide uses PR-owned changed paths.**

  - Resolve pull_request changed paths from the GitHub PR files API before falling
    back to a fetched-base three-dot git diff.
  - Add workflow-level regression coverage for stale-base docs PR classification.
- **ce-382-brain-drift-falsered** (ce-ops#382; validators): **Brain drift validation ignores stale local runtime state.**

  - Prefer tracked `.ce/brain/assertions.yaml` for repo-local drift checks even
    when ignored `.ce/state/brain/assertions.yaml` exists.
  - Keep canonical artifact drift fail-closed while adding regression coverage for
    stale local state and genuine canonical divergence.
- **ce-370-prbody-local-parity** (ce-ops#370; validators): **Local validate-pr test-coupling PR body parity.**

  - Local `ce validate-pr` now passes explicit PR body files through to the test-coupling gate and falls back to the branch carrier when present, while staying strict when no local body source exists.
  - Moved shared git helpers out of `work_sizing_floor` private symbols for reuse by test-coupling.
- **ce-376-unscheduled-sweep** (ce-ops#376; forge-triage): **Surface commissioned unscheduled issues in forge triage.**

  - Add an advisory commissioned_unscheduled section to forge triage output.
  - Mark commissioned_unscheduled_status as arc_missing when the payload lacks the arc issue.
  - Keep dispatchable arc items unchanged and emit no mutations for the sweep section.
  - Cover default and configurable commissioned predicates with unit tests.
- **ce-382-brain-drift-local-reconcile** (ce-ops#382; validators): **Local brain drift reconcile.**

  - Add `ce brain sync` for idempotent local runtime reconciliation.
  - Auto-reconcile ignored `.ce/state/brain` drift during local validate-pr when tracked `.ce/brain` sources are unchanged.
  - Preserve canonical `.ce/brain` drift gating and add actionable remediation text.
- **ce-391b-has-milestone-scalar** (ce-ops#391; validators): **Fix forge triage milestone scalar classification.**

  - Tightened `_has_milestone` scalar fallback so false-y unknown milestone shapes remain unmilestoned while truthy scalar references count as milestones.
  - Added forge triage classification coverage for dict, list, `None`, empty string, bare string, and integer milestone payloads.
- **ce-403-scanner-hardening** (ce-ops#403; validators): **Harden public docs confidentiality scanner.**

  - Harden the confidentiality scanner so stale baseline entries, empty scans, stat failures, and tracked-file enumeration failures fail closed.
  - Add regression tests for duplicate generated carrier issue metadata and scanner failure paths.
- **ce-383-conveyor-argv-hardening** (ce-ops#383; validators): **Harden conveyor daemon argv ref handling.**

  - Add a git push option terminator before daemon remote/refspec positionals.
  - Reject unsafe base, remote, branch, landed branch, and PR base ref shapes before git/gh argv construction.
  - Keep PR title/body as unrestricted free text in fixed gh flag-value slots.
  - **Declared work class:** tiny
- **ce-410-s10-publish-reverify-audit** (ce-ops#410; conveyor): **slice 10: final publish re-verification + per-phase audit.**

  Part of the conveyor publish hardening arc (slice 10 — final slice before the Re-Arming Evidence Bundle)

  Pre-existing checks preserved:
  - Validation sandbox receipts record the daemon-owned worktree tree.
  - Before publish, the landed branch tree is compared to the latest validation record tree.

  Added checks:
  - Publish-time landed head commit is re-derived from the repo checkout and compared to the landing result before tree identity is checked.
  - Publish-time base ancestry is re-checked with `git rev-list --left-right --count`.
  - Publish-time diff paths are parsed fail-closed from `git diff --name-status --find-renames` and compared to the per-PR carrier manifest.
  - Checkout-local transport config is rejected for `core.hooksPath`, `credential.helper`, and `url.*.insteadOf`, including Git's lowercased `core.hookspath` and `url.*.insteadof` output.
  - Allocation, validation, and publish phases emit structured audit logs without receipt nonce/signature leakage.
- **ce-445-g8-dockerfile-offline-setuptools** (ce-ops#445; deploy): **Install offline setuptools before canonical wheel builds.**

  - Copy `validators/wheelhouse-dev` into both canonical-image wheel-builder stages and install `setuptools` with `--no-index` before building the validator wheel with unchanged `--no-deps --no-build-isolation` flags.
  - Fix `build-image.sh` staging: `stage_context()` and `print_stage_context_commands()` now include `wheelhouse-dev` in the staged context dir so `COPY validators/wheelhouse-dev` in the Dockerfile resolves correctly.
- **ce-portability-guard-hygiene** (ce-ops#437; validators/tests/unit/test_portability_plane.py): **Portability guard test hygiene.**

  - Isolate runtime-only subprocess command fixtures.
  - Add wrapper and absolute-path command fixtures.
  - Document fail-closed runtime-command prose behavior.
  - **Declared work class:** tiny
- **ce-401-doctrine-coverage-fastfollow** (ce-ops#401; knowledge-ssot doctrine coverage): **Harden doctrine coverage ratchet edge cases.**

  - Treat an absent authoritative brain assertion ledger as empty coverage instead of corrupt or unreadable.
  - Document the ratchet's linkage-only semantics and single-root live invocation decision.
  - Add regression tests for duplicate exception entries and stale exceptions outside governed trees.
- **ce-403-scanner-hardening-fastfollow** (ce-ops#403; validators): **Record public docs scanner hardening fast-follow.**

  - Completed semantic novelty check for the public docs confidentiality scanner fast-follow.
  - The requested hardening behaviors are already present on the fresh main base, so this branch carries the governed evidence without duplicating scanner implementation.
- **ce-415-followup-tinies** (CE-415; brownfield install answers schema + boundary coverage): **Clarify brownfield enablement defaults and pin the git-history-only boundary.**

  - `brownfield.enabled` no longer advertises default-true behavior in the install
    answers schema; live enablement is derived from read-only project probe
    signals.
  - Added focused CLI coverage proving a project with git history, no CI
    workflows, and no detected test commands still enables brownfield adoption.
  - Regenerated the schema reference with `python3 scripts/gen_schema_reference.py
    --write`; it was already content-current for this nested description change.
- **ce-446-base-resolve-robust** (ce-ops#446; governance): **robust moved-base comparison-base resolution in governance workflow.**

  - Resolve pull-request comparison bases through the GitHub compare API before local diff validation, avoiding shallow checkout parent traversal when the recorded PR base is behind origin/main.
  - Fetch only the server-resolved merge-base commit for local validation and report remaining graph/API failures as infrastructure failures.
  - Supersession-append the validate workflow brain assertion SHA pin for the edited workflow bytes.
  - Ratchet the brain-drift active assertion count because the validate-workflow assertion supersession intentionally adds one active ledger record.
- **ce-451-surfaces-checker-hardening** (validators): **Harden the surfaces manifest consistency checker.**

  - Treat literal `UNSET` digests as unpinned unless covered by the current CE seat image debt allowlist.
  - Ratchet the CE seat image placeholder so pinning the digest requires removing the allowlist entry.
  - Replace substring Dockerfile image matching with exact aliases and explicit image overrides.
- **ce-49-skew-guard-quickwin** (creator-engine/ce-ops#49; validators): **quick-win: refuse gate commands under stale-wheel version skew.**

  - Refuse gate-relevant `ce` commands when an installed package is older than the target creator-engine checkout.
  - Warn and proceed for non-gate commands, with an explicit override escape hatch.
- **ce-796-804-review-followups** (review-followups-796-804; validation): **Review follow-ups for stale-wheel and contained-seat guards.**

  - Add the silent no-skew stale-wheel guard test for matching source and installed validator versions.
  - Align non-gate stale-wheel warning escape wording with the gate refusal path and pin message ordering.
  - Document the exact-code coupling for the contained-seat path-manifest carrier bypass at both ends.

### Documentation

- **ce-docs-quickstart-step-numbering** (ce-docs-quickstart-step-numbering; quickstart guide): **Renumber quickstart steps.**

  - Renumbers the quickstart guide headings into a coherent user-facing 1 through 5 sequence.


- **ce-l2-spotcheck-openssh-note** (ce-ops#197; guide): **getting-started: openssh-client prerequisite note.**

  Note the ssh-keygen/openssh-client prerequisite for external installs.
- **ce-n15-docs-html** (ce-ops#37; site): **Render public docs to HTML.**

  - Render 6 public guide docs (understanding-ce, pilot-runbook, contributing-to-ce, solo-dev-onboarding, solo-ceo-onboarding, SECURITY_MODEL) from Markdown to styled HTML pages matching the docs/index.html dark theme.
  - Update docs/index.html #docs section links from .md to .html for all 6 rendered docs; llms-install.md remains raw .md (machine-fetched signed spec).
  - Update validators/tests/unit/test_site_index_docs_nav.py to expect .html links.
  - Cross-link strategy: published doc cross-links use rendered .html; unpublished docs inside docs/ use GitHub blob URL; paths escaping docs/ tree use repo-root blob URL.
  - Product-lens scrub: all 6 source docs and rendered HTML are clean of ce-ops# ticket refs and internal host identifiers.
- **ce-320-install-narration** (ce-ops#320; agent-native install first-touch UX): **Newcomer-clean narration for agent-native install verification.**

  Instruct the installing agent to run the §0 signature ceremony quietly and surface a single plain-language confirmation (fail-closed hard stop on any verification failure preserved); reword the homepage paste-prompt to lead with the provenance promise; re-sign llms-install.md canonical bytes with ce-root-v1 (namespace ce-spec-v1). Verification commands byte-identical.
- **ce-329-scrum-to-ce-guide** (ce-329; guide): **Draft Agile/SCRUM to CE SDLC onboarding guide.**

  - Replace the existing Agile/SCRUM guide with a public draft grounded in CE spec, plan, task, review, carrier, changelog, and ratification flow.
  - Anchor the SCRUM mapping to CE's Frame -> Shape -> Build -> Review -> Ship vocabulary and link readers to the welcome, understanding, contributing, and canonical vocabulary guides.
- **ce-393-command-deprecation-policy** (ce-ops#393; contracts): **Command deprecation policy.**

  - Add a public command deprecation policy for governed shrinking of the v1 top-level command surface.
  - Add the command deprecation manifest with the current source-derived top-level command budget and no active deprecations.
- **ce-pilot-docs-daytoday** (pilot-docs-audit-20260703; pilot-facing guides (docs/guide/solo-ceo-onboarding.md, docs/guide/solo-dev-onboarding.md, docs/index.html)): **Pilot-facing command-surface corrections + collaborator section.**

  - Corrected every documented command in `solo-ceo-onboarding.md` and
  `solo-dev-onboarding.md` whose verb belongs to `cev3` (scope, shape, ratify,
  drive, artifacts, show, merge, report, status, inbox) but was shown as a
  bare `ce` command, matching `pilot-runbook.md`'s existing naming convention.
  `ce launch` was left untouched — it is a real `ce` command.
  - Fixed `docs/index.html`: `ce fanin show` (not a real subcommand) corrected
  to `ce fanin inspect`; the Solo + Dev doc-card's "with `ce` commands"
  wording corrected to `cev3` to match the corrected guide.
  - Added a new "Working with a collaborator on your repo" section to
  `solo-ceo-onboarding.md` covering how governance, review, ratification, and
  the merge gate behave once a second person has write access to the repo.
- **ce-438-complete-walkthrough** ("438"; guide): **Complete Walkthrough public guide.**

  - Add the Complete Walkthrough public guide and rendered page.
  - Retire the legacy step-by-step page and route public docs to the new walkthrough.
- **ce-454-dependency-unlock-contract** (ce-454; dependency unlock contract): **Dependency unlock contract.**

  - Add a documentation-only dependency unlock contract for blocker declarations, re-evaluation events, unlock mutation semantics, idempotency, replay guards, and fail-closed behavior.
  - Add the new contract page to the seeded doctrine coverage exception list in `.ce/brain/doctrine-coverage.yaml`.
  - Keep executor code, workflow wiring, schemas, and privileged actions out of scope.
- **ce-docs-cesession-framing** (no-ticket; pilot runbook session framing and brownfield answers example): **Document ce session terminal framing.**

  ## Summary
  - Present `ce session` as the terminal-first governed launcher in the pilot runbook.
  - Add `answers_version: 1` to the brownfield answers example so it matches the install answers schema.

  - **Declared work class:** tiny

  ## Validation
  - `ce validate-pr` green locally before push.
- **ce-docs-pilot-welcome** (guide): **Pilot welcome handoff guide.**

  - Extend the public welcome guide with first-read install handoff guidance.
  - Clarify the signed one-liner and `llms-install.md` agent playbook as equivalent install paths.
  - Point first governed sessions to the quickstart and pilot runbook, and name issue-reporting evidence.
- **ce-onboarding-docs-accuracy** (no-ticket; public onboarding docs): **Correct public onboarding command guidance.**

  - **Declared work class:** story

  - Rewrite the solo developer onboarding guide around the real first-run flow: `ce onboard` first, then `ce launch` after onboarding.
  - Add day-one prerequisites for a coding-agent CLI and `.hermes/` gitignore coverage.
  - Correct stale install-spec examples to use `ce install --spec`.
  - Shrink the public-doc confidentiality allowlist for cleaned onboarding contract references.

  CE-TEST-COUPLING-EXEMPT: existing public-doc confidentiality ratchet tests cover allowlist shrink behavior; this change only removes stale allowlist entries after cleaning docs.

### Stories

- **ce-l7f-integration** (L7-f; automatic release CI): **Release finalize integration coverage.**

  - Added slow integration coverage for orchestrate -> test-key sign -> finalize -> docs-copy guard parity.
  - Verified the copied docs tree with release artifact parity, install spec signature verification, and local latest signed release resolution.
- **ce-410-s8a-shared-launcher** (ce-ops#410; validation-runtime): **slice 8a: shared container-launcher primitive.**

  - Add a shared Podman launcher primitive for detached and foreground ephemeral container runs.
  - Refactor worker allocation to consume the shared detached argv path without changing behavior.
- **ce-410-validation-env-scrub** (ce-ops#410; validation subprocess env-scrub sandbox seam (slice 7 rework)): **Add validation sandbox env-scrub subprocess seam.**

  - Added a typed validation-subprocess seam (`ValidationSandboxSpec` / `run_validation_sandbox`) that constructs its execution context via `ValidationSandboxContext.from_sandbox(...)` and revalidates the env allowlist against a widened credential-shaped-key filter before every invocation.
  - Routed `conveyor.py`'s `_default_validate_runner` through the sandbox seam while preserving the slice-6 validate command and scrubbed `PYTHONPATH`/`TMPDIR`/`PATH` environment (regression-pinned in `test_conveyor.py`).
  - Extended (not replaced) the slice-4 `forge/authority_contexts.py` module: widened `_FORBIDDEN_CREDENTIAL_KEYS`/added token-pattern matching, added `require_no_credential_env`/`is_credential_env_key` helpers; `TransportCredentialContext`, `LocalGitContext`, and `ValidationSandboxContext.from_sandbox` are unchanged.
- **ce-437-adr-two-plane** (ce-ops#437; two-plane OS architecture ADR): **Add ADR-0014 for the two-plane OS architecture.**

  - Recorded the ratified portable Python control plane and canonical Linux container runtime plane decision.
  - Marked the prior OQ-1 `os-native` solo mapping superseded by the container-first architecture.
- **ce-388-d1-pickup-openbao-supplier** (ce-388; review-pickup OpenBao token supplier): **Review-pickup can refresh its GitHub token from SecretIdentity/OpenBao per pass.**

  - Added review-pickup token SecretRef defaults for the reviewer GitHub token.
  - Added the `--pickup-token-secret-*` flag family and file-only target refusal
    so configured daemon runs use the SecretIdentity materialize/read/revoke path.
  - Added per-pass token refresh plus bounded retry when a supplier is configured,
    while preserving the existing static-token path when it is not.
  - Added focused offline smoke coverage for unconfigured compatibility, env-target
    refusal, backend defaults, per-pass refresh, and bounded supplier failure.
- **ce-388-d2-pickup-openbao-deploy-tests** (review-pickup OpenBao deployment surface): **Add the review-pickup OpenBao deployment surface and D1 behavior coverage.**

  - Gate daemon systemd docs now describe the OpenBao env variables, exact
    allowed SecretRef entry, and static-token fallback during rollout.
  - The review-pickup systemd unit carries a commented OpenBao-ready replacement
    command while the active command preserves the static fallback.
  - Unit tests cover review-pickup token supplier construction, fork-unsafe
    `env:` target rejection, per-pass token refresh, retry logging, and bounded
    supervisor restart behavior.

### Chores

- **ce-l1-install-doc-fix** (ce-ops#358; install): **Install spec: openssh-client prereq + 0.3.1 alignment, re-signed.**

  Add openssh-client prerequisite note + align one-liner prose to 0.3.1, and re-sign the canonical spec with the offline ce-root-v1 trust root.

### Ci

- **ce-l7-injection-cleanup** (ce-ops#0; release): **Harden release workflow GitHub expression injection boundaries.**

  - **Declared work class:** tiny
  - Moves release workflow GitHub expression values out of shell run blocks and into env indirection.
  - Preserves release tag validation while removing direct expression interpolation from touched run blocks.

### Governance

- **ce-366-mainhead-resolver-adr** (ce-366-mainhead-resolver-adr; docs adr): **Ratify the main-HEAD artifact resolver/builder/verifier trust contract.**

  - ADR-0003 is Accepted — ratified by the Operator on 2026-07-02: Option A (commit-SHA pinning plus local
    reproducible build) is the accepted trust model for the already-live `ce clean-main-install` and
    `ce update --track main` main-HEAD install surface, retroactively as-is, with no code-level
    ratification gate added to those existing commands.
  - Document how `ce update --track main` composes with, but stays separate from, the signed-release chain.
  - A general ratification-gate pattern for future trust surfaces is tracked separately as a follow-up in
    the internal issue tracker; it does not gate the surface ratified here.

### Other

- **ce-432-tenant-embedding-endpoint-ux**: # Tenant embedding endpoint UX

  - Added explicit launch-time brain recall configuration via `CE_BRAIN_RECALL_EMBEDDER`, `CE_BRAIN_RECALL_ENDPOINT`, `CE_BRAIN_RECALL_ENDPOINT_MODEL_ID`, and `CE_BRAIN_RECALL_ENDPOINT_DIM`.
  - Added `recall_status` to Controller brain-bootstrap payloads and launch result JSON so unconfigured/unavailable recall is visible while SSOT bootstrap remains fail-closed.
  - Added a non-fatal `ce doctor` recall endpoint advisory check.
  - Updated launch runtime tests for hydrated, unavailable, and unconfigured recall states.
  - Rework: added real unit tests for `probe_controller_recall_endpoint` (no-endpoint shortcut, http/https default-port selection, malformed endpoint, real reachable/unreachable sockets) and for `CE_BRAIN_RECALL_ENDPOINT_DIM` invalid-value graceful degradation.
  - Rework: launch path now fails fast on a configured-but-unresponsive recall endpoint via a cheap bounded pre-probe before `open_surface(...).hydrate_session(...)`, and passes a short explicit timeout (`LAUNCH_RECALL_ENDPOINT_TIMEOUT_SECONDS`) to the embedding adapter instead of its 60s default.
  - Rework: non-blocking folds — corrected doctor docstring, added a `[WARN]` marker for the non-fatal advisory check, and downgraded UNCONFIGURED launch logging from WARNING to info-level.
- **ce-437-s3-containerize-daemons**: # ce-437 slice 3 - containerize daemons

  - Added a fail-closed filesystem lease module for armed daemon singleton gates,
    including atomic acquisition, explicit audited stale takeover, idempotent
    release, and heartbeat updates.
  - Required an injected daemon lease for armed conveyor daemon startup while
    leaving disarmed/report-only planning leaseless.
  - Added shared daemon container packaging and converted the queue daemon systemd
    path to the contained runner, with `CE_DAEMON_UNCONTAINED=1` documented as the
    legacy direct-launch escape hatch.
  - Added a `queue-daemon` singleton lease supervisor to the queue launch path so
    contained and uncontained queue loops share the same live-daemon gate.
  - Rework: same-host expired leases now honor live PIDs, conveyor passes
    heartbeat between item boundaries and stop fail-closed on heartbeat loss, and
    the queue supervisor terminates its child with exit 74 on heartbeat errors.
- **ce-440-s1-cli-unification**: CLI unification slice 1:

  - Renames the v3 public adoption command from `onboard` to `install`.
  - Moves the v1 dispatch planner to `ce pickup dispatch-plan`.
  - Adds subprocess-only `ce` forwarding shims for the v3 public command groups except `playbook`.
  - Keeps a one-release-cycle `onboard` alias on the `cev3 install` subparser (with an explicit `_DISPATCH` entry, since argparse surfaces the literal alias string rather than the canonical subcommand name) so the release-signed `docs/install.sh` and the slow-tier `test_install_bootstrap.py` keep working unchanged; `docs/install.sh` migrates to `install` on the next release cut (release-coupled, deliberately deferred out of this PR).
- **ce-onboard-relaunch-ux**: # Onboard relaunch UX

  - Declared work class: story.
  - Added a safe relaunch path that archives stale launched seat surfaces only when the prior sentinel is verifiably dead and no tmux session is live.
  - Kept ambiguous launched surfaces fail-closed with remediation pointing at `ce reap once`.
  - Surfaced sentinel tail-event details, including exit code and command, when onboarding launch dies before the single-controller assertion can pass.
  - Added a `ce doctor --require-visible-launch --harness ...` PATH precheck for the configured harness binary.
  - Regenerated the committed CLI reference for the new `ce doctor --harness` option.
  - Added unit coverage for stale archive-and-proceed, ambiguous liveness refusal, exit-127 diagnosis, and doctor harness check pass/fail.
  - Fix (review follow-up): the launch-gate now reads `events.jsonl` STRICTLY before deciding archive-vs-refuse — any unparseable line, or any `launched` event with a missing/non-positive-int/bool pid, is treated as ambiguous and refuses (fail-closed), closing a gap where a mixed dead-pid/corrupt-pid shape — or a wholly-unparseable events file — could bypass the reuse gate and let a second live seat spawn under the same identity. `seat_sentinel`'s tolerant reader is unchanged (other observability consumers still rely on it).
  - Fix (review follow-up): `ce doctor`'s codex harness-binary check now delegates to `codex_launch_spec.resolve_codex_harness_binary` (the exact resolution the launcher uses — `CE_CODEX_HARNESS` override used exclusively when set, else composed PATH merging live PATH with the known-good dirs) instead of a bare `shutil.which`, so doctor never reports green for a codex binary the launcher would actually refuse to resolve.
  - Fix (round-2 review follow-up): `_strict_events_file_scan` now treats `OSError` on `read_text` of an existing events file as ambiguous (`return True, []`) rather than silently proceeding (`return False, []`); an unreadable-but-present sentinel file is indistinguishable from one we cannot verify, so the gate refuses. The genuinely-absent-file branch (is_file() False) is unchanged. `_archive_stale_launched_surface`'s inline pid extraction now delegates to `_parse_positive_pid` so the two definitions cannot desync (behavioral change: `bool` pids and zero/negative pids previously accepted by the lax isinstance check are now consistently rejected at both call sites).

### Test

- **ce-ci-runblock-injection-guard** (ce-ops#703; ci): **CI run block injection guard test.**

  - Add a parser-based unit guard for GitHub Actions expressions embedded in workflow `run:` blocks.

### Tiny

- **ce-451-zeros-digest-guard** (creator-engine/ce-ops#451; surfaces manifest placeholder digest guard): **Reject placeholder surface sha256 digests.**

  ## Summary

  - Reject all-identical sha256 placeholder digest strings as unpinned in the surfaces manifest consistency check.
  - Keep legitimate mixed sha256 digests and the CE seat image `UNSET` allowlist behavior working.

  ## Validation

  - `PYTHONPATH=validators python -m pytest validators/tests/unit/test_surfaces_manifest.py -q`
  - `ce validate-pr --repo-root .`

  - **Declared work class:** tiny
- **ce-launch-hydration-warning-ux** (canary-C UX gap (no ce-ops ticket); validators/creator_engine_validator/launch_runtime.py hydration-skip warning gating + tests + changelog): **Hydration warning UX.**

  - Declared work class: tiny.
  - Suppressed the tenant-facing recall hydration warning when no embedding endpoint is explicitly configured (now logged at debug, not warning).
  - Reworded the warning for a configured-but-unreachable embedding endpoint to state launch impact (recall quality reduced, launch proceeds) and remediation (fix the endpoint or unset the env var).
  - Threaded a new `endpoint_configured` field through the recall status payload so `_emit_recall_status` can distinguish "unconfigured" from "configured but unreachable".
  - Added unit coverage for the unconfigured (debug/no-warning) and configured-but-unreachable (warning-with-remediation) hydration paths.

## v0.3.1 — spec-kit retirement (2026-06-30)

Spec-kit is fully retired. This release removes the vendored spec-kit skill
files and `.specify/` tree, amends constitution Principle X to the CE-Native
Spec Substrate doctrine, and ships follow-on onboarding, egress, and
validator-gate improvements that landed between 0.3.0 and 0.3.1.

### Removed

- Vendored spec-kit skills (14 `.claude/skills/speckit-*` + 9 `.agents/skills/speckit-*` directories) — Phase 1 retirement
- `.specify/` tree (Phase 2) — `.specify/memory/constitution.md` moved to the amended constitution location

### Changed

- Constitution Principle X amended from "Spec Kit Compatibility" to "CE-Native Spec Substrate" (version 1.1.0 → 2.0.0); source ratified 2026-06-30

### Added

- macOS container onboarding runbook via Linux container on Docker Desktop
- Verified origin/main HEAD artifact resolver and clean-install path
- Option C OpenShell egress delegation: os-native egress policies delegate to OpenShell when available, fail closed otherwise
- CE-native test-coupling `validate-pr` gate that blocks non-test source changes when the PR changes no tests

### Fixed

- `ce doctor` packaging check scoped to CE source-tree context — normal user repos skip the developer packaging-contract check
- Install-spec signature guard is now a blocking CI gate
- Onboarding docs updated: `ce brain init` documented as a required one-time launch prerequisite for mounted macOS container workspaces
- Mac-container onboarding guide now runs `ce brain init`, `ce onboard`, and `ce launch` from the mounted repo in order, with RED-G-4 remediation guidance
- Completion-report evidence-chain and spend inspect hints now call `ce artifacts <scope_id> --run-id <run_id>` instead of passing the run id as the required scope positional

## v0.3.0 — clean-install milestone (2026-06-27)

The release that makes a fresh `ce` install "just work" for real users — no
hand-holding, no hand-patching. Headlined by the install-blocker fixes a real
onboarding surfaced on the published 0.2.0 wheel.

### Fixed

- `ce brain init` (and every schema-validating command) now works from any directory — schemas are packaged inside the installed wheel instead of resolved from a source checkout, so commands no longer crash when run outside the repo
- `ce launch` pane-identity parsing is robust across tmux builds that sanitize tab characters (fixes a startup failure on tmux 3.4)
- Brownfield `ce onboard --apply` resolves the forge actor identity before building the join-PR scaffold, so adopting an existing repo succeeds end-to-end
- Install one-liner switched from `| sh` to `| bash`, avoiding a crash on systems where `/bin/sh` is dash (e.g. Ubuntu)

### Added

- Deterministic signed-release staging: `release`, `release-stage`, `release-bump`, and `release-changelog` subcommands bump the version, aggregate release notes, and stage a publishable, signature-shaped install mirror — root signing stays a single Operator gesture
- Surface-bump carrier schema, runbook, and consistency guard for the surfaces manifest
- Governed fleet rollout primitive with digest-pinned container images
- `ce ask` support-agent foundations
- Auto-generated CLI and schema reference documentation
- Welcome / getting-started onboarding front-door and step-by-step walkthrough

### Changed

- Self-identity drift detection in the knowledge source-of-truth
- Trust-tier graduation criteria and a human-contributor role added to the contributor guide
- Vendored wheelhouse refreshed for the offline cross-platform install (x86_64 + aarch64)

### Security

- Peer-credential attestation (SO_PEERCRED) on the self-push broker connection
- Socket-activated egress broker

## v0.2.0 — self-hosting milestone (2026-06-25)

### Added

- Governed Worker tier: in-process sub-agent roles (architect_research, implementer, reviewer, verification)
- `ce worker run --role <role>` — governed worker launch-and-collect
- Approval wall with OpenBao credential backing — merges require a capability token
- Cross-repo ce-ops issue auto-close bot (merge-triggered)
- Host-persistent contained-seat logging (logs survive container teardown)
- Herdr authenticated reach plane — Operator can attach to contained seats without sudo docker exec
- Operator steer lock — serializes Operator input vs autonomous gate dispatch
- Belt autonomous conveyor: stranded-PR sweep + lane-pickup daemon
- `ce fleet status` — aggregated fleet observability view
- `ce seats ls` — seat liveness read-model
- Contained-seat self-push and self-review via injected credential (transport-deputy pattern)
- Merge-queue dequeue primitive + integrator settle window
- Credential-wall approval gate (approval requires a capability forks/seats lack)
- Auto-carrier generation: `ce carrier` generates and self-verifies carriers
- Release-artifact parity CI guard (served install.sh hash == published SHA256SUMS)
- Cross-repo PR closes-linkage guard validator

### Changed

- Work classes reframed as CE ceremony tiers (not Agile work items)
- foreman/swarm canon enforced deterministically at governance layer (not prompt-hope)
- Codex Ring-0 tokenless contained launch: credentials NEVER enter container env/metadata

### Fixed

- Lane harness-matrix row restored after regression
- Integrator reads latestOpinionatedReviews (gate approval count correct)
- Verify-by-reaction dispatch confirmation hardened

### Security

- Contained-seat launch fails closed if gVisor containment proof is missing (probed containment)
- Egress fail-closed confinement for contained seats
- Per-dev forge App credential isolation (CDX-D-9 clause)

## v0.1.0 — first public product tag direction

Status: planned / not yet published.

`v0.1.0` is the first public product tag direction for Creator Engine. It is
intended to package the current governed kernel and release-ready validator /
package substrate from `origin/main` after the release-surface work merges and a
separate Operator-ratified publication gate authorizes tag and release creation.

This planned first release keeps `creator-engine-validator` at package version
`0.1.0`; the first product tag `v0.1.0` is coupled to that validator package
version for the initial public cut.

Included direction:

- governed Creator Engine kernel and documentation currently landed on `main`;
- `creator-engine-validator` package substrate at `0.1.0`;
- public release policy, changelog, README release pointer, and pre-1.0 security
  support wording.

Not included as shipped runtime:

- draft v2 specification and validator substrate, which remain internal/draft
  roadmap material;
- G2.* roadmap/gate identifiers as product versions;
- tag publication or GitHub release publication before a later, separate
  Operator-ratified publication gate.
