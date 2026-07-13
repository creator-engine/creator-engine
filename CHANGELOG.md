# Changelog

All notable release-surface changes for Creator Engine are recorded here.
This file follows the public product-tag direction; internal Creator Engine
G2.* gate identifiers remain roadmap/governance work IDs, not public semver.

## [Unreleased]

## v0.3.6 — NIGHT-6: heartbeat ladders + checkpoint protocol + forge spawn + ratifier queue (train 2, 2026-07-12)

### Highlights

- Complete the **daemon heartbeat ladder** (S1 schema → S2 belt/integrator → S3 review-pickup → S4 alarm consumer): every background daemon now emits bounded, non-secret liveness records and stale/failed daemons raise structured alarms without changing service authority.
- Ship the **`ce checkpoint` verb** and the controller continuity checkpoint protocol: redaction-safe, SHA-verified resume-state handoff for durable controller sessions.
- Add the **M2 governed review-acting spawn provider** (default-OFF, Operator-armed): a flock-claimed, sequenced provider primitive that hands caller-owned reviewer evidence to the M4 ratifier queue without forge or gate authority.
- Wire the **M4 ratifier-queue to the CLI** (SL-DAY-2 P1, NIGHT-6 W1): proposal-only queue, CLI surface, systemd unit, and reversible controller handoff path.
- Block double-assignment at the **work-claims layer (M6)**: fresh foreign claims at acquire are now hard-blocked with structured evidence.
- Fix the **install-answers schema mirror drift** (ce-ops#992) that caused every fresh install to fail with `INSTALL_REFUSED artifact_hash_mismatch`; the docs mirror is now byte-identical to the canonical validators copy and a CI guard prevents future drift.
- Add a **Dockerfile image-build smoke tier** (ce-ops#543) to PR validation: sha-verified `hadolint` + Docker Buildx `--check` for committed Dockerfile changes.

_Selected 19 changelog fragment(s) since release/v0.3.5._

### Added

- **ce-539-checkpoint-skill** (ce-ops#539; controller continuity checkpoint skill): **Add a redaction-safe controller checkpoint skill.**

  - Requires an untracked, SHA-256-verified resume-state file containing only
    delta since the prior checkpoint.
  - Separates probed, asserted, and unknown facts while preserving authority and
    role boundaries.
  - Provides deterministic completeness and safe resume procedures without
    creating readiness, forge, or gate side effects.
- **ce-daemon-heartbeat-contract-s1** (none; shared daemon heartbeat schema and passive emitter): Add a bounded, non-secret daemon heartbeat schema with deterministic validation.
  - Add atomic latest-state emission plus an injected structured-journal and periodic-running seam.
  - Cover identity, timestamp, status, monotonic pass, atomic-replacement, and confidentiality behavior.
- **ce-daemon-heartbeat-review-s3** (none; review-pickup daemon liveness): **feat(daemons): review-pickup heartbeat adoption (S3).**

  - Adopt the passive daemon-heartbeat contract in review pickup with a user-state latest record.
  - Emit startup, pass lifecycle, and bounded wait-seam liveness records without changing review routing behavior.
- **ce-539-checkpoint-verb-protocol** (ce-ops#539; controller ergonomics): **Add a deterministic local-only checkpoint verb and agent protocol.**

  - Validate labeled, redaction-safe handoff facts before atomically persisting an owner-only resume record.
  - Report the exact persisted-byte hash without asserting authority, gate status, or `/clear` completion.
- **ce-541-unresolved-connection-surface** (ce-ops#541; onboard connection advisory surfaces): **Surface unresolved onboarding connection.**

  - Add a fail-closed, read-only projection of the most recent onboarding ledger invocation.
  - Surface an unresolved forge identity connection in `ce status`, an advisory red/FAIL doctor
    line without changing doctor exits, and a stderr-only `ce launch` warning that preserves JSON.
  - Cover exact-cascade recognition, clearing, unknown ledger states, and pre-spawn behavior.
- **ce-543-image-smoke-tier** (ce-ops#543; validation): **Add a pinned Dockerfile image-build smoke tier to PR validation.**

  - Check committed `deploy/**/Dockerfile` changes with sha-verified hadolint and Docker Buildx `--check` only.
  - Keep unchanged carriers as a no-tooling no-op and prohibit image publication flags.
- **ce-550-brain-reconcile-verb** (ce-ops#550; governance): **brain reconcile verb.**

  - Add deterministic plan-gated static evidence reconciliation.
- **ce-daemon-heartbeat-belt-integrator-s2** (none; belt and integrator daemon liveness): **feat(daemons): belt and integrator heartbeat adoption (S2).**

  - Adopt the passive daemon-heartbeat contract for the belt and integrator daemons, including startup, running, pass-complete, and terminal lifecycle records.
  - Keep the belt as its existing per-invocation systemd loop: each invocation resumes the prior heartbeat index, avoiding a broader CLI-loop redesign.
  - Record stopping or failed terminal heartbeats for belt, integrator, and review-pickup exits without changing their operational authority.
- **ce-m2-review-spawn-provider** (M2; forge): **Governed review-acting spawn provider — core (M2 part 1).**

  - Adds a default-OFF, flock-claimed, strict JSON provider primitive without forge, queue, or attestation authority.
  - Defaulted pending Operator policy: capacity=0, timeout=180 seconds, retention=86400 seconds, and sandbox attestation is disabled until explicitly configured.
  - Production deployment, alert routing, and recovery ownership remain unassigned pending Operator policy.
  - Retry budget remains the existing shared acting budget; the provider records per-failure outcome codes without allocating a new retry budget.
- **ce-m2-spawn-provider-integration** (M2; forge): **Governed review-acting spawn provider — sequenced integration.**

  - Adds the default-OFF ce review-spawn-provider forwarding seam and reports explicit policy without launching a reviewer.
  - Folds all M2 provider terminal outcomes before the adapter can append them, preserving no-duplicate handling for UNCERTAIN_COMMENT.
  - Adds tailored structural coverage for the oneshot systemd unit without imposing daemon restart invariants.
- **ce-s4-heartbeat-alarms** (none; daemon liveness alarms): **feat(daemons): add heartbeat alarm consumer (S4).**

  - Classify validated daemon heartbeat records and emit bounded, secret-free alarm evidence for stale or failed daemons.
  - Add a five-minute user timer without changing long-running gate-daemon supervision.
- **ce-m6-claims-double-assignment-block** (ce-ops#38; validators): **Work-claim acquisition now blocks fresh foreign claims at the claims layer.**
- **ce-m4-ratifier-queue-cli-wiring** (ce-m4-ratifier-queue-cli-wiring; M4 ratifier queue CLI wiring): **M4 ratifier queue CLI wiring.**

  Proposal-only runtime, CLI, systemd wiring, reversible controller handoff, and ratified brain evidence supersession.

### Changed

- **ce-544-seat-image-signing-strip** (ce-ops#544; DGX contained-seat Git signing defaults and static Dockerfile coverage): **Disable inherited Git signing in the DGX seat image.**

  Set the DGX seat image's system Git configuration to disable commit signing for
  all container users and remove stale signing-key and signing-format selectors.

  The image must be rebuilt before this source-only change takes effect. Roll it
  out through the 0.144.1 pin canon, one seat and the canary first.
- **ce-548-schema-gen-constraints** (ce-ops#548; schema reference generation): **Render direct numeric schema constraints in the generated reference.**

  - Include `exclusiveMinimum`, `exclusiveMaximum`, and `multipleOf` when they occur directly on a projected field.
  - Cover the three keywords with a copied-schema generation regression test.

### Fixed

- **ce-538-hookpack-delivery** (ce-ops#538; onboard claude hooks launch): **Ship the tenant Claude hook-pack.**

  - Packages the Claude hook scripts and settings template in the validator wheel.
  - Materializes the hook-pack during fresh workspace onboarding without overwriting incompatible tenant settings.
  - Preserves default Claude resume behavior when additional harness arguments are supplied.
- **ce-install-schema-mirror-sync** (none; install / docs schema mirror / parity guard): **fix(install): sync docs/schemas install-answers mirror to canonical + parity guard.**

  - Copy `validators/creator_engine_validator/schemas/install-answers.schema.yaml` (sha256 `621a76f2…`) to `docs/schemas/install-answers.schema.yaml`, restoring byte-parity with the signed spec pin.
  - Add a CI parity guard (`test_docs_schemas_install_answers_mirror_is_byte_identical_to_validators_canonical`) that fails on drift and passes only when the mirror equals the canonical validators copy.
  - Root cause: PR #924 updated the canonical schema but did not sync the docs mirror, leaving the mirror at hash `be67d554…` while the 0.3.5 signed spec pin references `621a76f2…`. Result: `INSTALL_REFUSED artifact_hash_mismatch` on every fresh install.
- **ce-546-preflight-fail-closed** (ce-ops#546; validators): **PR preflight now refuses incomplete pytest baseline-diff evidence.**

### Design

- **ce-m2-review-spawn-provider-design** (M2 governed review-acting spawn provider): Adds the ratification-ready, default-OFF contract for a provider which obtains
  an immutable PR-head reviewer worktree, collects a bounded reviewer finding,
  and hands caller-owned evidence to the pure M4 ratifier queue. This carrier is
  design only: it makes no provider, deployment, or ratifier-state change.

## v0.3.5 — docs + CLI parity + reliability (train 1, 2026-07-11)

### Highlights

- Get started with confidence using the new **Start Here** guide, platform support matrix, and
  troubleshooting guide. The refreshed README and clearer first-run documentation make it easier
  to understand the product journey and find the right next step.
- Use a clearer, current command experience: public CLI guidance has been reconciled with
  supported commands, installation-root options are documented, and setup guidance no longer
  depends on retired local-state steps.
- Install and operate Creator Engine more reliably with stronger install verification,
  portable deployment guidance, safer contained-launch checks, and improved recovery guidance
  when a background workspace needs attention.
- Run contained coding-agent environments (DGX and VPS) with the current default model tier, while preserving
  the existing high-reasoning launch posture.
- Benefit from more dependable background operation: improved disk-space safeguards, durable
  service health signals, safer retry and recovery behavior, and clearer operator-facing
  diagnostics.
- Follow a more understandable path from planning through review and release, with improved
  onboarding material, release-readiness foundations, and user-visible status guidance.

_Selected 81 changelog fragment(s) since release/v0.3.4._

### Added

- **ce-conveyor-intake-s1** (conveyor-intake-s1; conveyor daemon intake queue dry-run planning): **Add flag-gated conveyor intake queue planning.**

  - Add a file-backed intake queue with `pending/`, `claimed/`, and `done/` states.
  - Wire the conveyor daemon runner to log dry-run `WOULD_DISPATCH` plans for idle seats when `CE_CONVEYOR_INTAKE_ENABLED=1`.
  - Document the queue layout and keep live dispatch out of this slice.
- **ce-513-ratification-binding-design** (docs): **Design ratification authorization binding.**

  - Added a docs-only design for binding agent-invoked ratification and merge
    apply to recorded operator authorization events.
  - Covered derived HMAC `approver_ref`, key custody and rotation through the
    approval-capability mint pattern, `authorization_source` evidence records,
    merge-apply capability markers, smoke-test coupling, validator/gate
    enforcement layers, migration from legacy hex refs, a mergeable slice plan,
    and before/after threat analysis.
- **ce-p3-rehearsal-s1** (deploy rehearsal harness): Add Fresh-Tenant Rehearsal harness (slice 1) at `deploy/rehearsal/`: a fail-closed clean-container runner, authoritative JSON evidence format, usage documentation, and Docker-free dry-run smoke coverage for the documented CEO first-hour stage list with explicit `CE_REHEARSAL_STUB:` markers for live model, GitHub, pull request, and completed-run steps.
- **ce-p5-seatwatch-s1** (ce-p5-seatwatch-s1; seat-watch daemon observe-only slice 1): **Add seat-watch daemon slice 1 (observe-only).**

  Add seat-watch daemon slice 1 (observe-only) at `deploy/seat-watch/`: polls configured seat panes on a configurable interval, emits structured JSONL events (`ready_signal`, `blocked_signal`, `idle_without_signal`, `pane_error`, `dispatch_delivery_ack`), ships with a systemd unit, launcher script, 20 targeted unit tests, and a design doc. Reuses existing seat-probe argv machinery from `conveyor_discovery`; singleton lease; no dispatch authority in slice 1.
- **ce-p8-review-daemon-s1** (ce-p8-review-daemon-s1; review-pickup dry-run daemon slice 1): **Add review-pickup dry-run daemon slice 1 (advisory/observe-only).**

  Adds `forge.review_dry_run` module wrapping `forge.review_pickup.poll_review_pickup(dry_run=True)` with an Operator-held gate and a named JSONL feed. Emits `WOULD_ASSIGN` and `WOULD_SKIP` decisions per PR per pass; no GitHub writes in any path. The Operator-held gate checks the `awaiting-operator` label (fail-open on API error) and an optional held-list file. Fourteen offline unit tests cover both gates and the bounded/rate-limited daemon loop. Slice 2 will add the `cev3 review-dry-run` CLI surface wired to `gate-daemons.env`.
- **ce-505-guided-journey-research** (docs): **Add guided journey UX research and design.**

  - Added a CEO-first design for the guided journey surface, centered on
    `Frame -> Shape -> Build -> Review -> Ship`, the awaiting-operator inbox,
    batch ratification, vacation-test replay, and completion reports as the
    emission feed.
  - Captured explicit decisions with rationale and rejected alternatives while
    preserving the rule that the UI is a read-model and emission surface of the
    one governed face, never a second authority.
- **ce-511-seatwatch-s2-events** (seat-watch daemon slice 2 events): **Add seat-watch slice 2 detector event durability.**

  Seat-watch now persists `idle-without-signal` and `dispatch-undelivered`
  detections as structured JSONL records under the daemon state root, with
  `seat_id`, `class`, `evidence`, and `timestamp` fields. Adds a supervised
  systemd example for restart-on-failure posture and focused unit coverage for
  the detector ledger and exit-code expectations.
- **ce-518s2-reconcile-feed** (validators): **Add a report-only live feed for stale ticket reconciliation.**

  - Added a thin `gh` adapter that collects open tickets and recently merged PRs
    into the frozen stale-ticket reconcile contract.
  - Kept the sweep report-only: findings render as text or JSON, while only live
    collection failures produce a non-zero exit.
- **ce-materializer-adr-arming** (materializer arming ADR): Adds ADR-0015 resolving the materializer pre-arming decisions for authority,
  credential custody, and lease topology.

  - Arming should happen through a governed PR that flips the constant, plus an
    Operator co-sign artifact under the ratified release-signing model.
  - The dedicated App credential is issued via the vault_signer pattern (per-call
    OpenBao KV v2 read → /dev/fd pipe → openssl; key never on disk, never in
    worker env), anchored to the ce-kv/forge/github-apps/<app-name>/private-key
    family from the OpenBao secret-path map.
  - The current single-host singleton uses MaterializerLease wrapping
    daemon_lease.acquire("brain-append", ...) in brain_intent_materializer.py,
    with a hard revisit before any second host or instance gains brain-append
    capability.
- **ce-n11s1-intake-queue-substrate** (N-11 slice 1; conveyor intake queue): **Add durable conveyor intake claim lifecycle.**

  - Pin queued briefs by SHA, declare controller path territory, and retain legacy queue APIs.
  - Add atomic claim/release/complete transitions, TTL stale reclaim, and a best-effort append-only NDJSON claim ledger.
  - Add a verified seat-pull handoff adapter with concrete normal work-claim/territory evidence, no-follow brief snapshots, and canonical launch metadata.
  - Fence finite-TTL queue ownership with opaque claim tokens and generations, serialize stale-reclaim/launch transitions, and hand launchers a descriptor-anchored snapshot that fails closed on replacement.
  - Recover or refuse queue crash windows deterministically, durably publish snapshots without partial final bytes, and close retained descriptors on fence-transition refusal.
  - Bind publication and lifecycle lookup to stable unit identity across priority and JSON/YAML filename variants; refuse malformed queue input and invalid bounded claim TTLs as structured seat-pull outcomes.
  - Treat malformed or schema-invalid pending records as structured queue-state refusals rather than empty work, normalize controller-evidence parser failures through owned-claim release, and preserve fractional TTL precision through launch fencing.
- **ce-n15a-skip-anomaly** (merge queue daemon detection): Added detection-only alarms for repeated identical skip decisions and PRs that
  remain approved without merging beyond their configured pass-age threshold.
  Alarms are recorded beside the daemon liveness state and emitted loudly to
  journald; they do not alter queue decisions or PR state.
- **ce-n15b-composition-probe** (N-15b; validation composition detection): **Add a detection-only composition probe for representative changes against the current main tip.**

  - Validate a real hook-free, unsigned composed commit against its exact immutable main parent.
  - Retry from a standalone no-hardlink local clone so Git common state cannot contaminate classification.
  - Sanitize every Git subprocess environment and disable hooks so ambient Git state cannot redirect composition.
  - Run nested validation in that same scrubbed environment and report only validations that actually ran.
  - Fail closed with bounded primary and cleanup evidence unless Git and filesystem cleanup verifies.
  - Preserve merge-conflict classification on retries and suppress incidents whenever cleanup fails.
  - Validate request shape before side effects and bound/redact validator and incident evidence.
  - Return validator and optional incident-sink failures without misclassifying them as merge aborts.
  - **Declared work class:** S
- **ce-n8-queue-daemon-iac** (none; queue daemon deployment topology): **Queue daemon IaC declaration.**

  - Declare a portable queue-daemon systemd topology and corrected liveness-state configuration.
  - Forward the contained liveness-state path and verify container arguments.
- **repair-n1s2-review4-dev3** (ce-n1s2-review-pickup-acting; review-pickup acting): **Add default-OFF review-pickup acting chain.**

  Adds an explicitly armed reviewer-spawn and PR-comment path. The acting pass is
  durably deduplicated, posts only through the Issues comments API, records
  per-item failures without crash-looping, and requires an Operator-provided
  spawn command template. The service remains unarmed by default.
- **ce-n3-dualformat-sync-gate** (none; validator PR preflight): **Dual-format sibling sync gate.**

  - Adds a PR-diff validator check for tracked Markdown/HTML sibling pairs.
  - Wires the check into local validate-pr so a change to one sibling fails until
    the matching sibling is also touched.
  - Adds focused unit coverage for paired updates, one-sided Markdown changes,
    one-sided HTML changes, and unpaired Markdown files.
- **ce-sl3-ready-attestation-nudge** (SL-3 READY validation-attestation reducer): Adds a pure, injected-facts reducer that proposes pending, SHA-mismatch,
  validator-live, green-attested, or failed READY-validation states. It performs
  no observation, validation, queue, harvest, process, filesystem, network, or
  forge action.
- **ce-sl3-supervisor-nudge-snapshot** (validator / supervisor read model): **SL-3 supervisor nudge snapshot.**

  - Added a pure, typed classifier for injected stale-review, seat, duplicate,
    capacity, queue, coverage, and context-checkpoint observations.
  - Proposals are deterministic, deduplicated, and fail closed for malformed or
    incoherent snapshots; this slice has no discovery or actuation surface.

### Added

- **ce-f1-storage-admission** (VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710 §C/F-1.2+F-1.3; disk headroom admission + scratch reaper slice 1): **Suite disk-headroom admission gate + deterministic scratch reaper (F-1.2 + F-1.3 slice 1).**

  Addresses the recurrent 100%-disk fill class identified in the 2026-07-10 VPS storage-gate incident.

  **F-1.2 — Headroom admission gate:**
  - New module `validators/creator_engine_validator/disk_headroom.py` exposing `check_headroom(path, min_free_gb)`, `free_gb(path)`, `DiskHeadroomError`, and `effective_min_free_gb()`.
  - `pr_preflight.py` gains a `disk_headroom (suite pre-flight)` check that runs immediately before the baseline-diff test command stage.  The gate fails-closed (returns 1) with a message naming `disk_headroom` and the measured free GiB when space is below the threshold (default 30 GiB; overridable via `CE_SUITE_MIN_FREE_GB`).  The pytest suite is never spawned when this check fails.

  **F-1.3 slice 1 — Deterministic scratch reaper:**
  - New script `deploy/storage-reaper/reap-scratch.sh`: sweeps `/var/tmp/wt-*` (48h), `/var/tmp/pt-*` (24h), and dangling Docker images.  Logs reclaimed bytes per category to stdout (journald when run under systemd).  Idempotent, refuses nothing, shellcheck-clean.  Supports `--dry-run` flag.
  - Systemd service template `ce-storage-reaper.service` + daily timer `ce-storage-reaper.timer` (Persistent=true, 30-minute RandomizedDelaySec).

  **Tests:**
  - 18 unit tests for `disk_headroom.py` (threshold pass/fail via `os.statvfs` mock, env override, `DiskHeadroomError` attributes) plus preflight integration tests confirming the gate blocks before pytest and passes with adequate disk.
  - 8 subprocess tests for `reap-scratch.sh --dry-run` including aged-fixture detection (wt-* at 50h, pt-* at 30h), below-threshold exclusion, no-delete guarantee, and unknown-flag exit.

### Added

- **ce-491-optiona-slice2** (CE-491; brain intent materializer): **Extend the Option A brain append intent materializer dry-run surface.**

  - Wire the append-intent XOR gate into local PR preflight beside the direct ledger stale-tail gate.
  - Add first-parent `origin/main` intent history scanning, HELD closeout-window evaluation, and a one-cycle materializer run-loop skeleton.
  - Harden materializer state/armed-write bounds and add focused unit coverage for scan, closeout, run-loop, and hold-path remediations.
- **ce-497-controller-state-sync-s1** (ce-497; controller-ops): **Add controller state snapshot tool.**

  Adds a governed, dry-run-by-default controller snapshot tool for arc state, dispatch state, and optional controller memory. Snapshots include a structured manifest, hashes, source identity, timestamp, and portable restore instructions. The shared credential-path policy and descriptor-anchored, fail-closed symlink handling exclude credential-bearing paths, while verified descriptor-relative atomic publication keeps manifest hashes and payload bytes coherent and refuses stale output reuse or swapped output parents. Memory defaults are derived from the selected repo and can be explicitly overridden. Live push wiring remains out of scope for this slice.
- **ce-518-stale-ticket-reconcile-s1** (validators): **Add report-only stale ticket reconciliation.**

  - Added an offline reconciliation module that compares caller-provided open ticket
    data and merged PR data with conservative branch/ref heuristics.
  - Added deterministic text and JSON report rendering with focused unit coverage.
- **ce-f3-migration-runbook** (controller-ops): **Codify controller migration completeness.**

  Adds a controller migration completeness runbook covering role definitions,
  memory, credentials, session infrastructure, and merge-gate topology with
  acceptance evidence for each checklist item. Extends controller state snapshots
  to carry `.claude/agents/*.md` role definitions through the manifest and
  published snapshot tree so restored controllers can resolve worker roles before
  dispatch.
- **ce-n3-documented-verbs-gate** (round-3-unit-a; validator): **Add a documented `ce` verb registry gate.**

  - Added a validator check that imports the in-process `ce` argparse registry and scans tracked markdown docs for taught `ce <verb>` invocations in code fences and inline code spans.
  - Added explicit forward-teaching and baseline-debt seams so current docs debt is visible while new unshipped verb teachings fail.
  - Wired the check into the generic registry, a focused CLI scan command, and `ce validate-pr`.

### Changed

- **ce-docs-cli-parity** (docs-cli-parity; public guide tree (docs/guide)): **Align guide CLI references and keep Welcome orientation-only.**

  - Moves the day-one install and handoff material out of `welcome.md` and into
    `quickstart.md`, leaving Welcome as orientation plus navigation.
  - Removes the retired local-state gitignore prerequisite from the governed-seat
    quickstart.
  - Records a full `docs/guide` CLI reference sweep against the shipped `ce`
    parser surfaces; no missing verbs were found.
  - Replaces retired `cev3` CLI references (`cev3 onboard/session/ratify/drive/report/merge`) in the
    governed-seat quickstart with the current `ce install --plan/--apply` and `ce launch` surface.
- **ce-hermes-retirement** (onboard state): **Complete user-facing Hermes state retirement.**

  - `ce onboard` now requires canonical `.ce/state/` bootstrap state instead of hard-requiring a `.hermes/` gitignore precondition.
  - Legacy `.hermes/` directories are tolerated as advisory-only compatibility state.
  - Updated CLI help, deployed runsc defaults, hook evidence roots, and functional docs to point at `.ce/state/`.
  - Left v1-frozen templates and schema constants untouched for separate product follow-up.
- **ce-readme-overhaul** (readme-overhaul; public README, CLI reference, and README version-drift gate): **Overhaul the public README, add the public CLI reference, and extend README version drift coverage.**

  - Replace the stale README status narrative with a public-facing product overview, stage model, quickstart, modes table, status pointers, and documentation fan-out.
  - Move the public `ce` command inventory to `docs/reference/cli.md` and keep README linked to that reference.
  - Keep release freshness structural by pointing readers to the release badge, changelog, and GitHub Releases instead of hand-maintained dated status prose.
  - Extend the current-version drift validator so README CE-version text claims are checked against the canonical package version.
  - Add unit coverage for matching README version text, stale README version text, version-free README content, CLI-reference parity, and the README reference link.
- **ce-427-approver-ref-provenance** (install answers ratification provenance): Install answers ratification bindings can now carry client App provenance for
  the approver reference. A focused minting helper derives and verifies the
  client-bound digest, while the schema keeps legacy bindings valid and requires
  complete provenance when the provenance object is present.
- **ce-512-redeploy-portability** (ce-512; deploy/singleton-redeploy): **Make singleton redeploy portable across deployment hosts.**

  - Added service-user rendering for the queue daemon systemd unit.
  - Kept linked worktree checkout validation compatible with the daemon container
    mount model.
  - Updated the health probe path to compose rendered unit `Environment=` values
    with the host env file, including OpenBao CA handling.
  - Rewrote the relocation runbook with parameterized host, user, path, state, and
    OpenBao settings.
  - Kept `container_launcher.py` in the portability plane manifest so future
    launcher path changes remain covered by the portability guard.
- **ce-516-item3-brain-window** (governance): **Correct autoclose fail-closed evidence.**

  - Correct the autoclose workflow comment to describe fail-closed token handling.
  - Supersede the stale brain evidence pin with the exact updated workflow hash.
- **ce-p2-acceptance-evidence** (P2 acceptance autoclose): **P2 Acceptance-Evidence autoclose hardening.**

  - Parse the PR body `Acceptance-Evidence:` field for issue validation evidence.
  - Enforce warn-mode handling for tracked issues labeled exactly `directive`.
  - Fail closed with exit 1 when the required cross-repo token is absent.
  - Add focused unit coverage for the parser, directive-label behavior, and token absence path.
- **ce-469-install-root-docs** (installer docs): **Document installer root override behavior.**

  - Documents `CE_INSTALL_ROOT` in the installer contract as the environment
    equivalent of the bootstrap `--install-root` override.
  - Adds `CE_INSTALL_ROOT` to the CLI install/update environment reference with
    the default root fallback.
- **ce-terra-default-flip** (contained DGX and VPS Codex launchers): Plain contained DGX and VPS Codex launches now default to `gpt-5.6-terra` with high reasoning effort unchanged.
- **ce239-wall-openbao-supplier** (review pickup OpenBao supplier): Record the Round 2 approval-wall-adjacent OpenBao supplier gate for
  controller review-pickup token handling.

  review-pickup can source the reviewer GitHub token through the generic
  SecretIdentity/OpenBao supplier path instead of resolving one static token for
  the daemon lifetime.

  - Rebased the parked branch onto `origin/main` at
    `6ce9527e1a9da3c578266db42b79625fe86392cd`.
  - Verified queue-daemon startup lease symbols remain present after rebase.
  - Verified `origin/main` already carries the review-pickup CLI secret flag
    family, `_review_pickup_token_supplier_from_args()`, and per-pass
    `run_review_pickup_loop()` token supplier/runner refresh with bounded retry.
  - Preserved the existing static review-pickup token resolution path when the
    pickup token secret flag family is unconfigured.
  - Normalized the review-pickup default OpenBao path constant to the literal
    `forge/reviewer/gh-token`.
  - Left deployment files, approval-wall runtime behavior, signed artifacts, and
    queue-daemon lease code untouched.
- **ce-docs-product-lens-cleanup** (public documentation): **Clarify the product journey in public documentation.**

  - Rewrote the README and first-run guides around what users can do with Creator Engine.

### Fixed

- **ce-491-prearming** (CE-491; materializer pre-arming checklist): **Close materializer pre-arming review findings.**

  - Bumps the materializer audit actor version to `ce-491-prearming`.
  - Normalizes materializer evidence paths before enforcing `.ce/state` bounds.
  - Documents the HeldError artifact asymmetry beside the handler.
  - Adds run-preflight coverage proving the brain append intent/direct ledger XOR gate fires in the real check sequence.
- **ce-503-refresh-guard** (onboard refresh-workflow recognition guard): **generation-aware refresh workflow recognition.**

  - Accepts prior CE-shipped validate workflow generations during `ce onboard --refresh-workflow`.
  - Keeps refresh fail-closed for workflows that only mention the validator without the CE workflow structure.
  - Deliberately refuses G1-era workflows with renamed job headings; modified CE workflows are foreign.
- **ce-followups2-20260708** (review follow-ups / validator preflight / deploy smoke): Batch two follow-up fixes from merged review findings.

  - DGX runsc image rendering now defaults surface build args to the host architecture
    and accepts `--arch` when cross-building.
  - Singleton redeploy smoke coverage accepts both install and unchanged dry-run paths,
    while redeploy rendering escapes backslashes and cleans temp files on early function
    exits.
  - Seat-ready preflight now normalizes registered autogen surface paths consistently
    and has companion coverage for schema-reference autogen repair commits.
  - The seat-ready pytest worker cap is pinned directly in unit coverage.
- **ce-461-merge-group-e2e** (validators): Adds a slow adoption integration fixture that drives a non-CE-shaped repository through the brownfield join-PR scaffold and verifies the emitted validation workflow keeps merge-queue trigger parity without carrying internal repository paths.
- **ce-453a-hashpin-hotfix** (validate-pr / signed-artifact-pins / path-manifest-fidelity): **Hotfix: signed-artifact-pins fails closed on real file; path-manifest scan counts negative fixtures as offenses.**

  Two gate-side defects introduced by #935 are causing uniform branch-validate failures:

  - **signed_artifact_pins (VAL-SIGNED-ARTIFACT-PINS-INVALID):** `_extract_signed_yaml` was
    calling `yaml.safe_load` on the entire HTML-comment body of `docs/llms-install.md`, including
    the human-readable prose paragraph that precedes the YAML block.  The prose contains
    colon-bearing text (e.g. `(no CE tooling: that is what breaks the bootstrap circularity)`)
    that YAML rejects as malformed mappings.  Additionally, the YAML section itself contains
    `python_requires: >=3.14` where `>` is inadvertently treated as a YAML block-scalar
    indicator.  Fix: skip the prose paragraph (non-blank lines before the first blank separator)
    and sanitize inline mapping values that start with `>` or `|` but are not valid YAML
    block-scalar headers before passing to `yaml.safe_load`.  A new `SPEC_WITH_PROSE` fixture
    and a live `docs/llms-install.md` test guard against regression.

  - **path_manifest_fidelity (false offenses from negative fixtures):** the registered `run()`
    check's `_iter_documents` directory sweep included `examples/malformed/handoffs/*.md` —
    intentionally malformed fixtures (`count-mismatch.md`, `hash-mismatch.md`,
    `init-py-corruption.md`) designed to produce errors in the integration-test "malformed
    examples rejected" harness.  These files were producing false `path_manifest_count_mismatch`,
    `path_manifest_hash_mismatch`, and `path_manifest_init_py_corruption` offenses during the
    repo-wide scan.  Fix: add `_is_under_malformed_examples` guard in `_iter_documents` (follows
    the same convention used by `identity.py` and `sidecar_utils.py`).  The negative-fixture
    integration tests continue to pass because they pass each file as an explicit path, which
    takes the `root.is_file()` branch and is never filtered.
- **ce-469-verify-install-root** (validators): **Verify installs against the requested install root.**

  `ce verify-install` now reports the effective root in machine-readable output
  and refuses install-state or live venv probes that resolve outside that root.
- **ce-519-doctor-agent-scan-default** (doctor): **Run the coding-agent CLI scan in default doctor mode.**

  - Surface a missing configured harness CLI as an advisory doctor finding by default.
  - Preserve hard refusal for missing harness runtime when visible launch is required.
- **ce-520-reap-selfservice-kill** (reap / stale tmux self-service): **`ce reap once` now teaches the operator how to clear stale live tmux launch surfaces.**

  - Adds tmux-specific operator guidance when a launched/no-exit seat is stale but
    its recorded PID is still live.
  - The escalation JSON and escalation record now name the exact tmux session and
    the self-service `tmux kill-session -t ...` command, followed by `ce reap once`.
  - Pins the behavior with focused `seat_reaper` policy-layer unit coverage.
- **ce-523-sentinel-signal-race** (ce-523; seat sentinel tests): **Deflake the trapped-signal sentinel wrapper test.**

  - Wait deterministically for the wrapper's trapped-signal `exited` record before
    asserting the exit contract, removing a parallel-runner timing race without
    weakening the required signal-derived exit code.
  - Preserve the product signal that a killed seat still leaves reliable lifecycle
    evidence for harvest and operator diagnosis.
- **ce-523c-sentinel-trapped-signal-deflake** (seat sentinel tests): **Deflake the trapped-signal sentinel wrapper test.**

  - Synchronize the test with foreground-child creation before sending the
    whole-process-group signal, so SIGHUP deterministically exercises the
    wrapper trap rather than racing the child launch.
- **ce-529-broker-refusal-robustness** (egress broker): **Keep the SELF-PUSH broker available after request failures.**

  - Convert normal push guard denials into audited broker refusals.
  - Return structured internal-error responses for forge failures and keep accepting later requests.
  - Tolerate clients that disconnect while a request is being received.
  - Classify host audit, persistence, and courier failures separately from client disconnects.

### Fixed

- **ce-followups-20260708** (validators, host-ops-broker): **Review follow-up batch for merged PR minors.**

  - Tighten host-ops broker fail-closed kill-switch and schema minor findings from merged PR #898.
  - Scope seat-ready autogen commits to the regenerated artifact and pin the missing PR #896 test coverage.
  - Isolate the stale checkout artifact determinism test in a temporary repo copy; partially addresses #504 minors only, with MAJOR broker arming findings remaining out of scope.
- **ce-523b-jit-deflake** (523; Deflake test_live_cli_mismatched_peercred_rejects_jit_mint_without_credential — BrokenPipeError/ConnectionResetError race on AF_UNIX rejection path; tight 2s thread-join replaced with poll-with-deadline.): **test: deflake JIT peercred rejection race.**

  The live-socket peercred rejection test was flaking under xdist load because the
  server can check `SO_PEERCRED` and close the connection before the client's
  `sendall` returns, causing a `BrokenPipeError` or `ConnectionResetError` that the
  test treated as unexpected. Separately, a fixed 2 s `thread.join` deadline was too
  tight on a loaded CI runner.

  Fix: tolerate `BrokenPipeError`/`ConnectionResetError` on `sendall` as an expected
  part of the AF_UNIX rejection path (the 403 response is already buffered), handle
  EOF gracefully in the receive loop, and replace the `join(timeout=2)` with a
  `_poll_until` helper that allows up to 30 s for the server thread to exit. The core
  assertion — no credential minted, 403 returned, audit record correct — is
  unchanged.
- **ce-f1s2-preflight-env-propagation** (preflight subprocess environment propagation): Preserve caller-provided pytest temporary-directory and option settings when preflight launches inner test suites.
- **ce-f2-gate-hardening** (VPS_STORAGE_GATE_INCIDENT_20260710; gate): **Gate hardening: homeless attempt log, disk-headroom refusal, liveness state export.**

  Implements F-2 from `VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710.md §C/F-2`, three
  behaviors that prevent the merge-gate crashloop that occurred when the root disk
  hit 0 bytes (05:24–05:30 UTC 2026-07-10):

  - **F-2.1 — Homeless attempt log (`deploy/daemons/run-daemon-container.sh`):**
    `setup_attempt_log` no longer depends on `$HOME` for the log directory. Fallback
    order is now: `CE_DAEMON_LOG_DIR` → `LOGS_DIRECTORY` (systemd `LogsDirectory=`
    injection) → journald-only degradation (warning to stderr, daemon continues).
    Every failure path emits a `WARNING:` to stderr and returns successfully; the
    daemon NEVER exits because a log file cannot be created.

  - **F-2.1b — `LogsDirectory=` unit addition (`deploy/queue-daemon/ce-queue-daemon.service`):**
    Added `LogsDirectory=ce-queue-daemon` / `LogsDirectoryMode=0700` so systemd
    provisions `/var/log/ce-queue-daemon` and exports it as `LOGS_DIRECTORY` for
    the contained launch path.

  - **F-2.2 — Startup disk-headroom check (`deploy/queue-daemon/launch-queue-daemon.sh`):**
    Added `check_disk_headroom` function that runs in `main_uncontained` after
    `validate_required_env` but BEFORE `exec_with_queue_daemon_lease`. If the
    filesystem hosting `CE_DAEMON_STATE_ROOT` (or nearest existing ancestor) has
    fewer than `CE_DAEMON_DISK_HEADROOM_GB` GiB free (default 5), the script exits
    with code **75** and an error message naming `disk_headroom`. This refusal
    happens before the singleton lease is acquired so a low-disk boot does not
    block future lease takeover.

  - **F-2.3 — Liveness state export (`validators/creator_engine_validator/forge/integrator_belt.py`):**
    `run_daemon_loop` accepts a new `liveness_state_path` keyword argument (falls
    back to `CE_DAEMON_LIVENESS_STATE_PATH` env var). After each `daemon_pass_complete`
    log entry, `_write_liveness_state` atomically refreshes a JSON file containing
    `last_pass_timestamp`, `pass_index`, and `failed_count`. Write failures are
    non-fatal (warning to stderr, loop continues). An external watchdog can now
    detect stale passes without parsing docker logs.

  Extend-don't-weaken: all existing tests pass without modification.
- **ce-f2-logsdirectory-bind** (deploy): **F-2.1b repair: restore `LogsDirectory=`/`LogsDirectoryMode=` binding in `ce-queue-daemon.service`.**

  The `ce-f2-gate-hardening` PR (#969's successor) merged F-2.1 (homeless-log
  fallback chain), F-2.2 (disk-headroom pre-lease refusal), and F-2.3 (atomic
  liveness-state export) into main. The `LogsDirectory=ce-queue-daemon` /
  `LogsDirectoryMode=0700` binding that lets systemd provision the log directory
  and inject it as `LOGS_DIRECTORY` was omitted from the merged service file.

  This patch restores the two missing lines so the F-2.1 `LOGS_DIRECTORY`
  environment fallback is provisioned automatically on service start rather than
  depending on `CE_DAEMON_LOG_DIR` being set externally.

### Documentation

- **ce-496-controller-bootstrap-doc-s1** (ce-496-controller-bootstrap-doc-s1; operations): **Controller bootstrap runbook.**

  - Add a replacement-controller bootstrap runbook with public placeholders and explicit identity, state, and parity gaps.
  - Add smoke tests for path references, confidentiality scrub, and the unavailable state restore inverse.
  - Admit the new operations runbook to the exact public-doc operations-tree exception ratchet.
  - Align takeover and continuity drill examples with the current CLI parser's required arguments.
  - List the YAML reader prerequisite required by the documented registry fallback command.
  - Separate standby surface provisioning from manual takeover acceptance evidence for the current tracked script.
  - Mark the current standby provisioning script as pending repair instead of a directly executable live step.
  - List the file-sync prerequisite required by the documented manual restore commands.
- **ce-materializer-appkey-custody-runbook** (materializer credential custody): **Add the materializer App-key custody runbook.**

  - Documents role-based credential custody, rotation, revocation, and recovery.
  - Records the ADR-backed per-call signer and single-host lease constraints.
- **ce-agents-execution-routing** (AGENTS.md / fleet policy): **Add execution-routing / no-inlining section to AGENTS.md.**

  New section "Execution Routing — No Inlining" inserted between "Dispatch Discipline" and
  "Hard-Stop Rules" in `AGENTS.md`. Covers two binding rules:

  - **Bright-line delegation rule.** A controller turn is limited to: reading state,
    adjudication, brief composition, pointer sends, and single probes. Any unit needing more
    than ~3 mechanical tool calls (sweeps, harvests, preflights, cross-host recon, batch file
    ops, reviews) MUST be delegated to a spawned worker from `.claude/agents/`. Controller
    context is the factory's scarcest resource.

  - **Wait-contract rules.** One-shot task agents may be awaited once. Persistent sessions
    (seats/foremen) MUST NOT be awaited — they never emit a completion signal; use pane reads
    between turns and durable READY signals. Two consecutive empty waits trigger liveness
    check + single re-dispatch or escalation. Finished subagents must be explicitly closed
    (slot hygiene).

  **Why now.** SL-DAY arc evidence (2026-07-10 night) recorded in
  `.ce/state/research/SL_DAY_LEDGER_20260711.md`: an inline wait-loop burned ~60 % of
  controller context in a single turn before being caught. The wait-contract diagnosis
  from that incident is now policy-level text so every agent session sees it at bootstrap.
  Operator directive 2026-07-11, SL-DAY arc remedy b.
- **ce-docs-start-here-matrix**: New Start Here guide and platform support matrix.
- **ce-docs-troubleshooting**: New troubleshooting guide for install and setup
- **ce-skills-v11-xs-adoption** (agent prompt and shaping dialogue discipline): **Adopt the ratified skills-v1.1 prompt-layer practices and pin brain assertion.**

  - Adds review smells, two-axis review guidance, and refactoring ownership.
  - Adds bounded TDD, HITL Frame dialogue, and research persistence conventions.
  - Ratified Operator amendment (2026-07-11): append tombstone + v3 brain assertion for
    `brain-assertion-d1b-14-reviewer-readonly-prepared-worktree` to pin the updated
    reviewer.md evidence hash; supersedes v2 via B2 append-only pattern per
    brain_runtime `correct` semantics.

### Stories

- **ce-materializer-deploy-unit** (materializer deploy pre-arming): **Add dry-run materializer deployment support.**

  - Adds a supervised dry-run materializer service, environment template, and health-capable launcher with arming disabled by default.
  - Extends singleton redeploy support so operators can dry-run or redeploy the materializer service through the same bounded flow used by existing singleton daemons.
  - Adds focused deploy tests for the systemd unit shape, dry-run redeploy path, and rendered health-probe environment.

### Chores

- **ce-publication-pipeline-canary-20260711** (internal): Internal release-pipeline verification marker; no user-facing changes.

### Design

- **ce-509-release-acceptance-design** (CE-509; release acceptance stage): Designs the release-acceptance stage between merge and ship.

  - Defines the RC-to-promote state machine and repository-visible acceptance
    record location.
  - Makes the existing fresh-tenant rehearsal harness the default promotion
    evidence path.
  - Requires release-ticket closure to link acceptance evidence, including
    persistent-state probes for deploy-class claims.
  - Names the ring-0 dogfood seat as the first consumer after promotion.

### Documentation

- **ce-506-daemon-vs-agent-rubric-design-s1** (ce-506; design): **Add the daemon-vs-agent routing rubric.**

  Proposes a routing rubric for deterministic daemons and bounded agent-organs,
  applies it organ by organ, defines an SSOT-first advisory hydration contract,
  and sketches AutoReview and belt-driven triage patterns. AutoReview is bound to
  trusted digest-pinned policy and cannot approve or ratify; recall remains a
  rebuildable non-canonical projection. DESIGN-PREVIEW: hold for Operator review
  before merge; this artifact is not ratified and grants no implementation
  authority.

### Implementation

- **ce-510-ship-gate-s2** (release acceptance gate mechanics): Adds the release-acceptance state machine mechanics for RC ship-gating.

  - Models repository-visible release-acceptance records and governed state
    transitions for candidate promotion through closure.
  - Fails closed when rehearsal evidence lacks RC identity fields needed for
    promotion binding.
  - Adds pure closure-integrity checks so release-ticket closure requires linked
    acceptance evidence and persistent-state probes for deploy-class claims.

### Other

- **ce-419-mint-broker-server**: # ce-419 Mint Broker Server

  - Added the loopback-only mint-broker HTTP server entrypoint.
  - Added the systemd unit, example config, and focused unit coverage for routing,
    loopback binding, config permissions, and body-free access logging.
- **ce-470-infra-identity-schema**: Identity registry schema now accepts tenant App metadata, documents registry precedence, and keeps the public example strictly placeholder-valued (real tenant identifiers live only in the internal registry).
- **ce-490-contained-launch-preflight-s1**: ## ce-490-contained-launch-preflight-s1

  - fix(launch): add pre-spawn policy validation for contained launch - slice 1

    Adds `_validate_contained_launch_plan()` to launch_runtime and wires it into
    the contained-launch path. It fires when `plan.runtime_policy is not None`,
    so bare and host-backend launches are unaffected.

    Three plan-time gaps are checked before any docker/runtime side effect:

    (a) Placeholder image digest (`sha256:000...000`) is a policy-content defect
        verifiable from the record alone; it is always refused with instructions
        to re-run `ce onboard` after runtime_posture resolves
        (`G6-LAUNCH-POLICY-INVALID`, `ContainedLaunchPreflightRefused`).

    (b) Absent bind-mount sources are checked against THIS host's filesystem.
        Optional agent-config dirs (`~/.claude`, `~/.config/claude`, `~/.codex`,
        `~/.config/codex`) are conditionally omitted when absent and emit a
        warning. Any other absent source path, or a sentinel-wrapper path not
        covered by a surviving mount, raises `ContainedLaunchPlanUnverifiable`
        (a `ContainedLaunchPreflightRefused` subclass).

    `launch()` treats (a) as a hard pre-spawn refusal, matching the original
    design. It treats (b) as a *warning* (logged via `LOGGER.warning`,
    non-fatal): the v3 runner backends (`gvisor-proxy`/`docker`) keep their plan
    translation pure/I-O-free by design (see `runner/gvisor_proxy_backend.py`'s
    "translate-vs-execute split") precisely so a runtime-policy-record's
    `mount_manifest` can carry symbolic or not-yet-materialized host paths —
    main's own launch_runtime test corpus relies on this for CI-safe unit tests.
    Hard-refusing (b) unconditionally would regress every such launch, so on an
    unverifiable plan `launch()` warns and falls through to the runtime backend
    with the original (unfiltered) manifest — the same behavior a launch without
    this preflight would have had. `_validate_contained_launch_plan()` itself
    stays fully strict for direct callers (this slice's own dedicated fast unit
    tests in `test_contained_launch_preflight.py` continue to exercise (b) as a
    hard raise), so the check is fully implemented and ready to be tightened
    once `mount_manifest` entries are guaranteed to reference real, resolved
    host paths by the time `launch()` runs.

    Previously, these cases could reach docker, fail at container-creation time,
    or produce an unresolvable launch-probe timeout with no actionable message;
    (a) now raises a hard pre-spawn refusal (``ContainedLaunchPreflightRefused``)
    before any runtime side effect, (b) now surfaces a named warning instead of
    silence.

    Out of scope for slice 1: the sentinel HUP race / kill-session exited event,
    the zero-digest emitted during onboard, live docker stderr forwarding when
    docker is still reached, and resolving `mount_manifest` entries against real
    host paths so (b) can become a hard refusal without conflicting with
    main's symbolic-plan test fixtures.

    - **Declared work class:** story
- **ce-491-optiona-slice1**: # ce-491-optiona-slice1

  - Added the dry-run-only CE-491 Option A brain intent materializer library with deterministic keying, intent rediscovery, live-tail proofing, mediated record construction, HELD/quarantine state, append-only daemon events, and a local brain-append lease wrapper.
  - Added the `brain_append_intent_xor_direct_ledger` hard gate for hybrid append-intent plus direct-ledger PRs.
  - Added focused unit coverage for key derivation, validation, record determinism, holds/quarantine, lease behavior, dry-run orchestration, and XOR gate behavior.
- **ce-492-smoke-uid-mismatch**: The daemon container smoke now makes the generated signing secret readable by the image uid under rootful Docker, while preserving best-effort behavior for rootless engines. Cleanup also emits captured per-pass smoke logs before deleting the temporary directory so timeout failures retain their diagnostic output.
- **ce-493-approval-marker-ttl-remint**: Queue daemon approval capability markers that expire during retry loops are now re-minted only when a trusted current-head approval is still present. Expired markers without a current authorized review continue to fail closed with explicit evidence.
- **ce-500-launcher-caps-s2**: ## ce-500-launcher-caps-s2

  - fix(contained-seat): add cgroup memory cap to DGX and VPS runsc launchers

    Adds `CE_DGX_MEMORY_LIMIT` (default `8g`) and `CE_VPS_MEMORY_LIMIT` (default `8g`)
    env-configurable docker `--memory` flags to the runsc seat launchers. Seats now OOM
    inside the container (pytest dies, work survives in the durable bind-mount worktree)
    rather than triggering a host OOM-kill that evaporates the gVisor sentry and all in-
    progress work. Disable by setting the env var to empty string.

  - fix(preflight): add governed TMPDIR + parallelism cap wrapper for host preflight runs

    Adds `tools/preflight-caps.sh`: a thin bash wrapper that exports TMPDIR to a disk-backed
    path (default `$HOME/tmp`), warns if the resolved TMPDIR is on tmpfs, caps `-n auto` to
    `-n 4` (configurable via CE_PREFLIGHT_MAX_WORKERS), forwards all argv to the wrapped
    command, and cleans up `pytest-of-*` tmpdirs post-run. Prevents host-tmpfs RAM
    competition with contained-seat sentry processes during concurrent preflight runs.

  **Declared work class: story**
- **ce-501-queue-canary**: ## ce-501-queue-canary

  - feat(queue-daemon): add CE_QUEUE_DAEMON_CANARY=1 mode to launch-queue-daemon.sh

    When CE_QUEUE_DAEMON_CANARY=1 is set: implies --dry-run, omits all
    --approval-wall-secret-* flags (wall resolves DORMANT legitimately), relaxes
    required-env to GH_TOKEN + CE_GATE_REPO + CE_GATE_AUTHORIZED_REVIEWERS,
    refuses if CE_DAEMON_STATE_ROOT conflicts with the live daemon default,
    and emits a visible CANARY MODE banner. Closes the queue canary launcher gap.

    - **Declared work class:** S
- **ce-502-standby-surface**: ## ce-502-standby-surface

  - fix(standby): provision dedicated main-tracking surface + mint-forge-token repair + drill gate

    Adds deploy/dgx-controller-runsc/provision-standby-surface.sh to provision the standby
    controller with its own main-tracking git worktree (default /home/cedev2/ce-standby-main),
    decoupling it from the shared mutable checkout. Fixes the D6 Drill #1 FAIL where the
    shared checkout on ce-release-0.3.1-rc2 lacked `ce takeover`.

    Adds tools/mint-forge-token.py replacing the traceback-producing helper with a
    guarded implementation that accepts --help and --dry-run without errors.

    Extends continuity_drill_runtime with a standby_liveness gate: drills missing a
    standby liveness proof degrade to WARNING status rather than silently passing.
    The gate only passes with a structured standby-emitted `ce takeover --dry-run
    --json` packet where `ring0_verify.ok=true` and
    `initial_state=AWAITING-OPERATOR`; raw boolean flags remain WARNING.

    - **Declared work class:** S
- **ce-504-broker-arming-blockers**: Host-ops broker target arming now rejects unowned container image prefixes, honors configured state-root prefixes, and avoids treating benign audit keys containing "value" as credential indicators. Focused unit coverage documents the new config resolution behavior and the audit false-positive guard.
- **ce-515-xdist-copytree-fix**: The release-finalize integration fixture now skips build outputs, distribution
  artifacts, and editable-install metadata while copying the repository under
  test. This keeps parallel test workers from racing against transient artifact
  trees during fixture setup.
- **ce-516-autoclose-s2**: Acceptance-Evidence autoclose handling now avoids duplicate warning comments, keeps directive issues open when warning delivery fails, and emits a best-effort governance alert when required token configuration is absent. Workflow comment refresh is deferred pending the next brain-ledger window.
- **ce-521a-worktree-venv-bootstrap**: ## ce-521a-worktree-venv-bootstrap

  - Added linked-worktree validator Python resolution that reuses the main checkout `.venv` instead of building duplicate per-worktree environments.
  - Updated local PR preflight defaults so contained worktrees can run validator and pytest commands through the shared main venv when `CE_VALIDATOR_PYTHON` is unset.
  - Added focused unit coverage for shared venv resolution, linked-worktree detection, explicit env precedence, and fail-closed repair guidance.
- **ce-materializer-cas-push**: # Materializer CAS Push Pre-Arming

  - Added deterministic materialization commit construction for merge-time brain append intents.
  - Added compare-and-swap push handling that abandons stale commits and rescans before rebuilding.
  - Preserved disabled arming by keeping push refusal behind the arming guard while allowing disarmed commit inspection.
  - Added focused unit coverage for deterministic construction, CAS push refusal, and rescan behavior.
- **ce-readme-review-minors**: Tighten README current-version detection so non-CE runtime version mentions do not raise stale-release drift errors, document the shipped `ce conveyor` queue repair command, and extend CLI reference reconciliation so public command groups dispatched before argparse stay covered by tests.
- **ce-solo-ceo-onboarding-fix**: Rewrote the Solo + CEO onboarding guide so default-mode users state intent and authorization in dialogue while the governed agent runs the mechanical pipeline. The guide now keeps command details in clearly labeled technical asides, replaces the removed decision-inbox command with the forge-based awaiting-decision flow, and keeps the CEO path centered on Goal, Done-when, Change-type, artifact review, and explicit shipping approval.
- **ce-docs-first-project**: New first-project tutorial for planning, reviewing, and delivering a small repository change.

### Task

- **ce-953-image-rebuild** (dgx contained Codex image preparation): Prepare the DGX contained-seat image recipe for a verified Codex 0.144.1 arm64 artifact, Python 3.14 validator tooling, shared seat UID/GID builds, and a controller-run canary rollout with rollback guidance.
- **ce-seat-preflight-parity** (validators): Adjusted the seat-ready preflight profile so the control-plane portability guard is skipped for seat validation because seat-image runtime characteristics produce proven false failures, while the scan remains enforced by the default-profile preflight at controller harvest. Added unit coverage proving a simulated scanner failure does not fail the seat-ready profile and that the default profile still enforces the guard.

### Validator

- **ce-453a-hash-pin-guard** (validate-pr): **signed artifact hash-pin validate-pr guard.**

  - Add a validate-pr guard for signed artifact hash-pinned source changes.
  - Cover pinned-file, paired pin update, unrelated, and pin-only diff cases.
  - Fail CLOSED (`VAL-SIGNED-ARTIFACT-PINS-INVALID`) on frontmatter corruption,
    a missing/malformed `artifact_manifest` section, or zero discoverable pins,
    instead of silently degrading protection to an empty pin set.
  - Protect the `install.sh` / `docs/install.sh` byte chain via the existing
    `sha256s_sha256` pin's SHA256SUMS alias, so editing the installer without a
    matching pin/SHA256SUMS change is caught.
  - Give whole-document pins (e.g. `content_sha256`) a distinct "whole-document
    re-sign required" notice instead of the generic missing-pinned-file wording.
  - Cover missing/unreadable signed doc, frontmatter-corruption, git-diff
    subprocess failure, synthetic-fixture-doc-changes-in-diff, and the
    install.sh-chain RED case.

## v0.3.4 — broker-lanes + takeover-core + memory-layer + continuity-drill (2026-07-08)

### What's new

- Start a project with a clearer guided path from installation through delivery.
- Get more reliable local setup, review preparation, and project-context support.
- See better help as you move between planning, building, and checking a change.

35 PRs since v0.3.3 (plus one post-ledger hygiene patch), spanning JIT credential minting, egress broker read lane, work-claims lifecycle, controller takeover and continuity drill, brain memory-layer slice 1, brain-init that teaches, SSHSIG signing deputy design, host-ops broker design, ephemeral controller seam design, and a sheaf of fixes and infrastructure hardening.

### Security

- **Harden adopted client SHA256SUMS verification.** Generated adopted-repo CI now verifies the signed CE install spec and out-of-band trust anchor before accepting the signed SHA256SUMS digest; regression coverage asserts the previous direct SHA256SUMS download path is no longer emitted. (PR #861)

### Fixed

- **Pin the 0.3.3 runtime and tenant seat image manifest-list digests.** Record `surfaces/manifest.yaml` CE runtime and seat image entries with their index digests; update the static test assertion to match the pinned 0.3.3 manifest entry. (PR #863)
- **Docs version currency: bump stale 0.3.0 references to 0.3.2.** Updates two current-version claims in README.md. (PR #862)
- **Wheel determinism test isolation.** Scrub gitignored `validators/build/` and `.egg-info/` before the wheel surface determinism assertion; regression coverage proves stale artifact directories no longer false-RED the test. (PR #869)
- **Honor declared reference protections during preserved-check verify.** Honor an explicit `github.protections: reference` declaration when a 403 is returned; keep undeclared 403 responses fail-closed as `protection_floor_unenforceable`. (PR #865)
- **Adoption workflow template merge\_group trigger parity.** Adds the merge queue `merge_group: checks_requested` trigger to the emitted adopted-repo CE validation workflow template. (PR #859)
- **Brain genesis is part of onboard apply.** `ce onboard --apply` now emits the genesis brain assertion ledger; `G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED` now names the exact recovery command `ce brain init`. (PR #881)
- **Close the onboard-workflow and brain-preflight follow-up batch.** Refuse `ce install --refresh-workflow --spec ...` instead of silently ignoring the spec path; surface trimmed write stderr in failure detail; pin PR preflight fail-closed behavior when the comparison base is unprovable. (PR #890)
- **Post-merge hygiene for resume-state hydration.** Select the newest resume-state file by lexicographic path order; keep seeded resume-state hydration byte-identical across mtime-only touches; reuse the already-computed resume-state digest when returning the hydration pointer. (PR #894)
- **DGX runsc hygiene tests and docs.** Add negative coverage for relative DGX and VPS host worktree roots; replace host-specific README examples with generic home-directory placeholders. (PRs #891 #893)

### Changed

- **G11 reviewer-authority in-launcher minting.** Adds `ce lane launch --mint-reviewer-authority` for distinct reviewer venues; binds minted envelopes to `capability: independent_review_venue`, short expiry, and single-use consumption; delays writing until all pre-spawn refusal gates pass. (PR #864)
- **Egress broker forge read lane.** Adds read-only broker verbs `get-issue`, `get-pr`, and `list-comments`; host enforces per-seat rate cap, mints short-lived read-only tokens at request time, injects only into trusted host `gh api` child environments, and emits audit lines for allow/refuse outcomes. (PR #872)
- **work\_claims lifecycle seed slice.** Added local claim lifecycle runtime, `ce claim transition`, and `ce claim list`; added claim lifecycle documentation and a merge-closeout workflow. (PR #868)
- **Takeover refusal and watcher re-arm.** Added raw controller launch refusal evidence and exact recovery command; added duty-manifest watcher/daemon re-arm dry-run planning; hardened takeover evidence with generated-at/host binding. (PR #873)
- **Harness promotion parity matrix.** Reworked harness matrix into provider/ring rows with explicit `code-support`, `launch-wired`, `live-proven`, and `promotion-approved` cells; added an unsigned harness promotion matrix gate wired into local `ce validate-pr` and CI. (PR #880)
- **next-step hints for journey verbs.** Added shared journey guidance constants; wired journey verb success outputs, bare `ce` usage, and `ce init` output to those constants; standardized the review venue default on `ce-review`. (PR #876)
- **PRD-aware shaping via `ce shape --from`.** Adds `ce shape --from <path>` as a PRD/requirements context-injection path into the Shape grill; the preview cites the source PRD, stays bounded to one Scope, and records nothing unless `--confirm` is supplied. (PR #878)
- **Brain ledger append serialization slice 1.** Added a local PR preflight guard that refuses `.ce/brain/assertions.yaml` deltas when the live base ledger tail has moved since the PR merge base. (PR #882)
- **Design Option A merge-time brain append intent materialization.** Design-only proposal for post-merge materialization of `brain-append-intents`; covers owning actor, authority bounds, lifecycle, failure/crash handling, and HELD cascade. (PR #889)
- **Runsc launcher durable staging and worktree roots.** Stage generated contained Codex configs under each seat's durable log root instead of host /tmp; bind durable host-backed worktree roots to the container /var/tmp worktree root for VPS and DGX launchers. (PR #891)
- **Memory-layer hydration contract slice 1.** Added mediated append support for first-class `brain-decision` and `brain-lesson` records; added `ce brain hydrate --json` for deterministic active decisions, lessons, and newest resume-state pointer output; wired `ce takeover --dry-run --json` to include brain hydration evidence. (PR #888)

### Added

- **Add current-version drift gate.** Added an explicit version-drift gate and direct CLI path for unsigned current-version docs and deploy surfaces; wired into local `ce validate-pr` and the validate workflow; updated stale deploy image defaults to 0.3.3. (PR #867)
- **Controller posture banner.** Added a deterministic read-only `ce posture` banner with text and JSON output for controller posture evidence. (PR #866)
- **Add `ce takeover` dry-run core.** Added the read-only `ce takeover` planner/evidence packet for Slice B; wired dry-run text and JSON output through launch Ring-0 preflight. (PR #871)
- **Slice D continuity drill harness.** Added `ce continuity-drill` read-only proof surface composing posture and takeover evidence into a scheduled benign gate-cycle drill record; documented weekly-until-two-clean-runs cadence. (PR #874)
- **JIT seat credential lane.** Contained seats can request broker-bookkept 300s credentials via `mint-seat-credential` / `revoke-seat-credential` verbs; credential classes v1: `model-api` and `forge-scoped`; host validates the per-seat class allowlist and returns the secret only in the authenticated Unix socket response. (PR #875)
- **Add Codex controller promotion evidence packet support.** Added Codex controller-promotion evidence packet read/write and validation helpers; `ce launch --harness codex` downgrades controller authority to read-only when the packet is absent or incomplete. (PR #879)
- **Design SSHSIG signing deputy for ce-root-v1 custody.** Design for moving `ce-root-v1` private-key custody behind a constrained SSHSIG-aware signing deputy with OpenBao as preferred backend; binds each signing act to canonical release hashes, install-spec content SHA, release id, and a short-lived single-use Operator co-sign artifact. (PR #870)
- **Canonical CE journey doc pair.** Added the canonical CE Quickstart and how-CE-builds-software concepts guide; updated guide navigation and product-facing vocabulary to point welcome packs at the canonical journey docs. (PR #877)
- **Codify forge housekeeping runbook.** Added the forge housekeeping runbook for standby/takeover controller harvest, review, gate, re-push, closeout, and board hygiene loops; wired the takeover hydration plan to surface the runbook. (PR #883)
- **Design host-ops broker v1.** Design-only document for a systemd-supervised host-ops broker replacing raw container-runtime socket reachability with fixed, convergent, audited repair and status verbs; defines v1 verb contracts, kill-switch and rate-limit behavior, and CE-owned namespace boundaries. (PR #884)
- **Recursion bottom-out policy design.** Design-only recursion bottom-out policy for autonomous repair incidents; defines hard repair-depth and same-failure thresholds, durable AWAITING-OPERATOR circuit state, and scheduled four-path drill. (PR #886)
- **Ephemeral controller provider seam design.** Design-only provider seam for event-spawned, self-retiring ephemeral controllers; names NanoClaw as the T0 reference implementation; specifies fail-closed rules keeping singleton gate custody, approval-wall authority, and SSHSIG signing custody outside ephemeral contexts. (PR #887)
- **Seat-side preflight design.** Design for seat-side pre-READY preflight that blocks stale generated references and malformed carriers before controller harvest; recommends `ce validate-pr --profile seat-ready` successor profile. (PR #892)
- **Worktree-debt classified sweep design.** Design-only classified sweep proposal for accumulated `.ce/wt-*` and `/var/tmp/ce-*` directories; defines deterministic classes, lifecycle ownership, dry-run/default safety invariants, and `ce worktree sweep` command shape. (PR #858)

## v0.3.3 — canary-C / Arad unblock: CLI-exposure fix + release-chain dispatch + tenant denylist (2026-07-06)

Minimal point release to unblock canary C and the Arad live tenant. Rolls up six changelog fragments merged to main since the 0.3.2 tag.

### Fixed

- **verify_cli predicate tolerates onboard→install verb rename.** `verify_cli()` grepped for the legacy `onboard` verb string which was renamed to `install` in 0.3.2; changed to top-level `--help` invocation and checks `usage: <command>` in stdout.
- **Release auto-tag explicitly dispatches publish chain in ordered sequence.** `release-auto-tag` now explicitly dispatches `publish-runtime-image`, `publish-seat-image` (gated on runtime success), and `release.yml` in order after pushing the annotated tag, bypassing `GITHUB_TOKEN` recursive-event suppression that silenced all downstream `push:tags:` triggers.
- **Docs version currency: bump stale 0.3.0 references to 0.3.2.** Updates two current-version claims in README.md.

### Changed

- **Arm dependency-unlock LIVE preconditions.** Rechecked LIVE apply targets against freshly read candidate state and blocker resolutions before removing dependency hold labels; added fail-closed evidence for missing GitHub credentials and missing `gh` paths; removed unused `workflow_dispatch.apply` input.
- **Tenant denylist matrix.** Added a data-driven tenant confidentiality denylist matrix loader; threaded it through the public confidentiality scan so CE forbidden patterns stay unconditional while tenant identifiers are blocked on CE public and cross-tenant surfaces; added focused coverage for denylist refs, bidirectional enforcement, CE-floor enforcement in tenant venues, tenant allowlist ratchets, and PR/issue/evidence scan surfaces.

### Added

- **Mediated brain-ledger append ADR.** ADR-0005 for `.ce/brain/assertions.yaml` append serialization, evaluating queue-daemon mediation, merge-queue-native chain recomputation, and a ledger-file lock primitive; recommends a separate brain-append daemon for the minimal Phase-1 slice; records fail-closed, containment, gate-singleton, and duplicate-ID/tombstone invariant requirements. Design only: no implementation, no ledger schema change.

## v0.3.2 — release-automation + brownfield-installer hardening (2026-07-05)

Folds forward the parked brownfield-enabled-default schema clarification and the rc2-branch surfaces-manifest/staging fixes, and rolls up the accumulated 146 changelog fragments merged to main since the 0.3.1 tag (release automation, onboarding/installer hardening, launch-runtime and triage-queue work, and CI/governance tooling).

### Added

- **ce-375-scope-impact-p0** (validator tooling): **Warning-only Scope impact propagation.**

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
- **ce-351-queue-daemon-relocation** (deploy/queue-daemon): **Durable queue daemon relocation package.**

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
- **ce-triage-autolabel** (ce-ops triage queue advisory labels): **Add advisory classification labels to the ce-ops triage queue.**

  - Apply-mode now synchronizes deterministic `wc:` and `triage:` issue labels from the existing advisory queue classification.
  - Dry-runs report the would-be managed label delta without writing labels.
  - Label errors are recorded per issue so the advisory queue can continue posting.
- **ce-166-doctrine-coverage** (knowledge-ssot doctrine coverage): **Add brain doctrine coverage ratchet.**

  - Add a deterministic doctrine coverage ratchet for governed contract docs.
  - Seed current uncovered doctrine files as explicit exceptions while requiring new doctrine to be asserted or acknowledged; the ratchet only shrinks.
- **ce-361-installer-mirror-policy** (release policy): **Codify installer mirror release policy.**

  - Added a draft release policy section for installer mirror immutability, emergency republish exceptions, audit evidence, and signed-release handling.
- **ce-388-conveyor-redesign-adr** (conveyor daemon security-redesign ADR): **conveyor daemon security-redesign ADR.**

  Added ADR-0004 proposing the conveyor daemon arm-safety-by-construction model.
  The ADR makes discovery payloads data-only, moves checkout and git/gh authority
  to daemon-owned working directories and pinned daemon config, treats imported
  bundle contents as untrusted validation input, and blocks G-N3 arming until an
  independent security review ratifies explicit arming criteria.
- **ce-398-controller-standup-docs** (controller playbooks): **Controller standup duty manifest and runbook.**

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
- **ce-294-press-merge-bundle** (forge evidence): **Press-merge evidence bundle v1.**

  - Added the read-only press-merge evidence bundle assembler, schema, hidden inert renderer, workflow artifact upload, and focused tests.
  - Captures the known validate-pr durability gap honestly with validation.available=false.
- **ce-410-alloc-core** (validator forge daemon allocation): **Daemon path allocation core.**

  - Added standalone daemon path allocation value objects, receipt verification, randomized runtime-root allocations, and cleanup mechanics for CE-410 slice 1.
- **ce-413-automerge-tier-b** (forge automerge): **Auto-merge Tier B brain supersede chores.**

  - Added the gated brain-ledger supersede automerge tier predicate and actuator re-verification.
  - Kept the tier flag default off and added focused policy and actuator coverage.
- **ce-422-tenant-record-schema** (validator tenant records): **Add tenant record schema and validator.**

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
- **ce-388-conveyor-harvest-daemon** (conveyor daemon): **Conveyor harvest daemon shadow-mode launcher and entrypoint.**

  - Added the shadow-mode conveyor harvest daemon entrypoint, launcher, service unit, container adapter wiring, and unit coverage.
- **ce-437-s4-runtime-image** (deploy/runtime-image): **Publish canonical multi-arch runtime image.**

  - Added the canonical runtime image Dockerfile, GHCR multi-arch publish workflow, consumer digest-pin contract, and focused static validation.
- **ce-443-stuck-lease-runbook** (playbooks/controller/runbooks): **Add conveyor daemon stuck-lease recovery runbook.**

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
- **ce-367-ce-native-init** (ce-init): **CE-native ce init project scaffolding.**

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
- **ce-410-s8b-sandbox-runner** (validation-sandbox): **slice 8b validation sandbox runner.**

  - Promotes the rootless Podman verification worker-container policy.
  - Adds a containerized validation sandbox runner with signed receipts and side-effect ledger recording.
  - Covers the runner with offline unit tests using injected launcher and ledger seams.
- **ce-410-s9-ledger-binding-seam** (conveyor-daemon): **slice 9 ledger binding seam.**

  - Requires the validation ledger binding seam for armed conveyor daemon construction.
  - Adds unit coverage for armed refusal and disarmed construction without the seam.
- **ce-437-portability-guard** (validators): Added a control-plane portability guard that blocks undeclared Linux runtime-plane
  assumptions in validator modules while preserving current debt through explicit
  runtime-plane declarations and dated baseline exemptions.

  Reworked command detection to catch wrapped or absolute-path runtime commands and
  added fail-closed manifest coverage for missing, malformed, and stale baseline
  entries.
- **ce-n5-worktree-prune** (validators): **Add fail-safe worktree prune tool.**

  - Added `ce worker worktree-prune` (dry-run by default; `--apply` required for destructive action).
  - Classification uses three-dot content diff vs origin/main (not ancestry alone); dirty/unpushed worktrees are report-only, never touched.
  - Fixes a self-delete defect found in internal review: apply_prune() previously only protected the primary worktree, not the actively-invoking linked worktree; now both are protected (see test_apply_never_removes_invocation_linked_worktree).
  - Hardened invocation-worktree protection to derive independently from the process cwd (symlink-safe, walked to its containing worktree root), not just from `--repo-root`, so a `--repo-root`-pointed worktree A never causes removal of the cwd's own worktree B.
  - Added `empty-tip-content` regression coverage (content-identical-but-diverged branch tip → prunable) and its inverse (diverged and non-empty tip content → `REPORT_ONLY`/`unpushed-commits`), proving the content check gates pruning, not ancestry.
  - Locked registered worktrees are now surfaced as their own `REPORT_ONLY`/`locked` verdict.
- **ce-434-contained-seat-profile** (governance): **validate-pr contained-seat profile for harvest-side carriers.**

  - Add `ce validate-pr --profile contained-seat`, a narrow profile that runs the normal preflight while tolerating only `path_manifest_carrier_required` because contained-seat carriers are generated harvest-side.
  - Choose a named profile instead of a general skip flag so validate-pr stays fail-closed: unknown profiles are refused and no broad check-skipping surface is introduced.
  - Keep the profile parseable but hidden from generated CLI help so the existing committed CLI reference remains unchanged.
  - Keep default `ce validate-pr` behavior byte-identical with no profile, and cover the profile, notice line, and refusal paths in validate-pr tests.
- **ce-453-preflight-skip-transparency** (validators): **preflight skipped-test transparency.**

  - Report skipped tests from the PR preflight baseline-diff test gate with file counts and pytest -rs reasons when available.
  - Keep skipped tests transparent rather than failing the preflight, and carry the skip count into the final PASS summary.
  - Cover default, zero-skip, and contained-seat profile behavior.

### Changed

- **ce-372-autoupdate-test-hygiene** (signed updater tests): **Auto-update startup notice test hygiene.**

  - **Declared work class:** tiny
  - Replaced the startup notice test's hardcoded cache path with pytest tmp_path.
  - Added cached notice_shown coverage so a fresh shown cache suppresses a second notice.
- **ce-374-prepitch-docs-slice** (ce-374-prepitch-docs-slice; public docs overview): **Rendered Creator Engine overview docs page.**

  - Add a styled public overview page for Creator Engine.
  - Link the rendered page from the existing docs section without removing existing markdown docs links.
  - Include a public-safe architecture-at-a-glance diagram for controller, seats, forge, and containment.
  - Update the docs navigation test so the docs section keeps required markdown links and explicitly permits this rendered overview page.
- **ce-380-dgx-launcher-image-guard** (validator surfaces manifest guard): **DGX launcher image manifest guard.**

  - Generalized the runsc image default guard across launcher scripts.
  - Added DGX launcher coverage for manifest-aligned and divergent defaults.
- **ce-dev4-surface-update** (deploy): **DGX seat image: openssh-client + PyNaCl; codex 0.142.4.**

  Fix contained DGX codex seat (missing ssh-keygen + PyNaCl); codex surface + tag 0.142.4; arm64 base-digest override pending on a tracked follow-up.
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
- **ce-339-libsodium-dockerfile** (deploy/dgx-runsc Dockerfile): **Add libsodium runtime package to DGX seat image.**

  - Adds Debian bookworm runtime package `libsodium23` to the DGX seat image runtime apt package list.
  - Uses the runtime library package rather than `libsodium-dev` because no headers are needed.
  - CE-TEST-COUPLING-EXEMPT: Dockerfile-only infrastructure change; no testable application logic changed.
  - Follow-on controller step: rebuild the DGX seat image and relaunch dev-4 after this Dockerfile change lands.
  - **Declared work class:** XS
- **ce-385-workclass-doc-vocab** (docs authoring): **docs: update work-class authoring vocabulary.**

  - Updated author-facing work-class references to the current XS/S/M/L taxonomy.
- **ce-395-bump-to-main** (release): **Add release-bump commit mode.**

  - Add release-bump commit mode that creates a fresh local branch, commits only canonical version sources, and generates PR carriers without pushing or opening a PR.
  - Delete the orphaned release_orchestrate module.
- **ce-407-pin-migration-s1** (brain assertion verification): **Migrate pr_preflight brain pins to probes.**

  - Migrates d1b-01, d1b-42, and d1b-43 from pr_preflight.py hash pins to focused probe verification.
  - Registers pr_preflight probe checks and updates the authoritative brain drift ratchet.
- **ce-407-pin-migration-s2** (brain assertion verification): **Migrate integrator belt brain pins to probes.**

  - Migrates d1b-10, d1b-11, and d1b-12 from integrator_belt.py hash pins to focused probe verification.
  - Registers integrator belt probe checks and updates the authoritative brain drift ratchet.
- **ce-410-authority-contexts-core** (validators): **Typed authority contexts for integrator credentials.**

  - Added typed authority contexts for transport, local git, and validation sandbox boundaries.
  - Removed process-global GH_TOKEN mutation from the integrator gh runner shim.
  - Wired queue-poll and live action construction through explicit context values.
- **ce-410-conveyor-phase-authority** (conveyor): **Type conveyor git runner phases and pass explicit subprocess envs.**

  - Added conveyor-local git phase typing until authority_contexts.py lands.
  - Routed local git and validation subprocesses through explicit, scrubbed env mappings.
- **ce-410-integrator-git-phase-split** (forge/integrator-belt): **Split integrator git authority by phase.**

  - Route local integrator git commands through LocalGitContext while fetch, push, and ls-remote retain transport credentials.
  - Add regression coverage that records every git subprocess environment and rejects credential-bearing local git envs.
- **ce-412-automerge-tier-a** (automerge): **Auto-merge Tier A carrier/changelog split-tier.**

  - Added a default-off carrier/changelog automerge tier flag and path predicate.
  - Recorded tier metadata and reviewer venue in automerge decisions and actuator audit records.
  - Wired workflow policy materialization and unit coverage for Tier A.
- **ce-410-s8c-armed-wiring** (conveyor validation): **Conveyor armed-mode validation via sandbox runner.**

  - Wired armed conveyor validation through the validation sandbox runner and recorded receipts.
  - Committed generated carriers before armed sandbox validation so receipts bind the prepared tree.
  - Added an 8c interim fail-closed pre-push assertion: if the landed branch tip tree does not match the validation receipt tree, the item fails before push/PR open.
  - Strengthened fail-closed behavior: absence of a successful validation record now fails the item before any tree-sha comparison (absent = strict), before push/PR open.
  - Documented the 8c interim: slice 9 must promote `validation_ledger_binding` into the armed required-seam list.
  - Design SSOT `/var/tmp/CE410_SLICE8_SPIKE_DESIGN_20260704.md` (sha256 `15db27aa632b1e9f67806665ce8e961e88913186446d14b638c164fb1e5d600f`) assigns full publish reverify to slice 10: re-derive `tree_sha` immediately before push/PR and confirm it equals the receipt-bound tree, with per-phase audit trail.
- **ce-440-s2-cev3-deprecation** (validator CLI): **cev3 deprecation notice and internal-groups lock-in.**

  - Adds a direct cev3 invocation deprecation notice while suppressing it for ce forwarding shims.
  - Locks ce v3 forwarding shims out of internal-only command groups.
- **ce-440-s3a-docs-sweep** (docs): **Docs sweep to the unified ce command surface.**

  Replaced user-facing cev3 command examples with the unified ce surface.
- **ce-440-s3b-systemd-exec-migration** (systemd gate daemons): **Migrate repo systemd units from cev3 to ce.**

  - Migrated the integrator and review pickup systemd units to invoke the unified `ce` CLI surface while preserving daemon arguments.
  - Updated the gate daemon systemd test prefix assertion to allow `ce` and bash launchers only.
- **ce-440-s3c-migration-doc-snippets** (operations docs): **docs: align dogfood-migration systemd snippets with the unified ce surface.**

  - Aligns the dogfood migration guide's checked-in systemd examples with the unified `ce` console-script surface.
- **ce-444-queue-daemon-startup-lease** (validators/creator_engine_validator/v3_cli.py): **Fail-closed queue daemon startup lease.**

  - Added a default-on singleton lease to the Python `ce queue-daemon` entrypoint
    before the first daemon pass, including clean held/stale refusal output.
  - Added queue-daemon lease heartbeat and release coverage, plus operator
    recovery notes for stale lease cleanup.
  - The daemon now recognizes when its own singleton lease is already held by a
    live, verified ancestor process (its own launcher supervisor) and proceeds
    straight into normal startup instead of refusing — fixing a startup
    deadlock under the canonical launcher while keeping every other refusal
    path (unrelated live holder, stale lease) unchanged and fail-closed.
- **ce-445-c2-daemon-container-plumbing** (deploy/daemons): **Daemon container launcher env-file, CA-cert, and tmpfs secret custody plumbing.**

  - Added guarded `CE_DAEMON_ENV_FILE` support, read-only OpenBao CA cert remapping,
    and tmpfs-backed container paths for daemon secret file custody.
  - Extended daemon container runner tests for env-file refusal, CA cert mapping,
    tmpfs args, and byte-identical queue-daemon default argv compatibility.
- **ce-a3-docs-envelope-automerge** (ce-a3-docs-envelope-tiers; automerge policy): **Extend automerge docs envelope tier.**

  - Extend automerge policy and actuator rechecks to cover the ratified docs envelope for docs, root markdown, changelog, and PR manifest paths.
  - Add regression coverage for the #771 docs-envelope AUTO path set and code/work-class refusal cases.
- **ce-l3-triage-apply-completion** (ce-ops triage queue automation): **L3 triage apply-mode completion.**

  - Create the triage queue sentinel comment in apply mode when absent, then patch it on later runs.
  - Flip scheduled triage queue runs to apply mode with CE_TRIAGE_APPLY_KILL_SWITCH as the rollback switch.
  - Add unit coverage for exactly-once sentinel creation, scheduled kill-switch wiring, and bounded apply mutations.
- **ce-414-installer-doc-egress** (installer docs): **installer docs: version-symbolic release paths and egress allowlist.**

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
- **ce-445-c5prep-daemon-smoke** (deploy/daemons): **Add daemon container stateful restart smoke coverage.**

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
- **ce-runner-helper-dedup** (runner docker gvisor translation): **Deduplicate Docker runner translation helpers.**

  - Hoist shared mount, policy-field, and launch-probe translation helpers into a public runner seam.
  - Route both plain Docker and gVisor proxy backends through the shared helpers without changing rendered argv semantics.

### Fixed

- **ce-l4-launch-hydration-fallback** (ce-L4; validator launch runtime): **Launch hydration deterministic fallback.**

  - Retry Controller launch recall hydration with the deterministic default store when vllm-openai is unavailable or dimension-mismatched.
  - Cover deterministic fallback and rebuild-stable keyword/graph recall invariants.
- **ce-351-launcher-argparity** (deploy / queue-daemon launcher (config/infra)): **Fix arg-parity gap in queue-daemon relocation launcher — wire missing `--approval-wall-secret-ref-policy-sha`.**

  - **`deploy/queue-daemon/launch-queue-daemon.sh`** — added `--approval-wall-secret-ref-policy-sha`
    arg (sourced from new required env var `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA`); added the
    var to `validate_required_env` and the usage/help block.  Without this arg the relocated VPS
    daemon would fail to fetch the approval-wall secret from OpenBao on cutover, silently blocking
    all auto-merges.
  - **`deploy/queue-daemon/RELOCATION.md`** — added `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA` to
    the required-keys section of the cutover runbook so operators populate it in the env file.

  No change to fail-closed logic, secret handling, or unrelated args.  The `--json` arg was
  already present in the launcher; confirmed not missing.
- **ce-373-subprocess-timeouts** (validator preflight): **Bound validate-pr network subprocess calls.**

  - Added a shared network subprocess timeout override for validate-pr and live onboard GH/git network calls.
  - Surfaced simulated subprocess timeouts as actionable preflight/onboard errors instead of hangs.
  - **Declared work class:** M
- **ce-337-selfpush-canary** (vps-runsc egress broker): **Self-push broker stable socket mount and canary.**

  - Fixes the VPS launcher to mount broker socket directories instead of restart-sensitive socket inodes.
  - Adds a contained self-push canary that fails on stale broker sockets, broker refusal, or non-no-op responses when requested.
  - Documents live diagnosis: dev-3 broker services were running, but the container-held push/review socket mounts returned ECONNREFUSED after daemon restarts.
- **ce-386-wheelhouse-xdist-group** (validator tests): **Serialize wheelhouse built-surface tests under xdist.**

  - Added the wheel-build xdist group to the built-surface wheelhouse tests and the packaging contract wheel parity test so shared source-tree wheel builds serialize under loadgroup.
- **ce-386-xdist-wheelbuild** (validator tests): **Serialize wheelhouse built-surface wheel builds under xdist.**

  - Mirrored the wheel-build xdist grouping style from test_wheel_bake.py on built-surface tests that invoke source wheel builds.
- **ce-387-holdlabel-symmetry** (forge controller inbox): **Hold-label symmetry for controller inbox.**

  - Reused the full shared issue-side blocking hold-label union for PR awaiting-operator classification.
  - Covered PR labels without body markers across the union: `wip`, `blocked`, `waiting`,
    `status:*` variants such as `status:checkpoint`, `do-not-claim`,
    `dependency-blocked`, existing awaiting-operator labels (`awaiting-operator`,
    `hold`, `awaiting-operator/hold`), and held/on-hold aliases including case variants.
- **ce-388-payload-data-only** (validators/conveyor-daemon): **Wire ADR-0004 payload schema into conveyor daemon discovery.**

  - Wired ConveyorDaemonItem.from_mapping() through the ADR-0004 data-only schema before raw discovery field access.
  - Legacy command, base, remote, and path-bearing discovery mappings now reject with value-free audit records.
  - Schema-rejected discovery items are isolated per item so one bad payload cannot drop the rest of the batch.
  - Added daemon and schema regressions for missing, typed, non-mapping, and legacy-control payload failures.
  - Superseded d1b-10, d1b-11, and d1b-12 brain assertions to re-pin integrator belt evidence for this branch.
- **ce-390-confidentiality-scanner-coverage** (public-repo confidentiality scanner): **Widen public-repo confidentiality scan to all tracked text files.**

  Widened the public-repo confidentiality scanner from a docs-only extension allowlist to full coverage of all git-tracked text files, closing a gap where confidential ce-ops#N ticket references or other forbidden patterns could leak through non-doc file types.

  - Full-coverage widening: scan now walks all tracked text files (binary-sentinel skipped) instead of a fixed docs-suffix allowlist.
  - Structural carrier exemption accepts both the bare `ce-ops#N` and the repo-qualified `creator-engine/ce-ops#N` forms in generated changelog frontmatter (`issue:` line) and PR-manifest headers only; the same ticket ref appearing in body prose still fails closed.
  - Scan errors (unreadable file, forbidden-pattern match failure) fail closed rather than being silently skipped.
  - Pre-existing tracked-text baseline hits are allowlisted via the existing debt-ratchet mechanism; remediation is tracked internally, not via a new external program.
  - Adds 3 new tests proving qualified-form frontmatter/header refs pass with an empty allowlist, plus 3 companion tests for the existing bare-form + qualified-body-prose-fails coverage.
- **ce-391-triage-advisory-text** (validator cli): **Surface commissioned unscheduled pickup triage advisory text.**

  - Added plain-text `ce pickup triage` output for commissioned unscheduled advisory count and issue details, matching the existing JSON payload signal.
- **ce-402-preflight-failclosed** (validator preflight): **Fail closed when baseline-diff pytest does not execute tests.**

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
- **ce-410-conveyor-alloc-wire** (conveyor daemon allocation provenance): **slice 2: conveyor daemon allocation receipts (armed-path provenance).**

  - Replaced the default-true `daemon_owned_paths_allocated` bit with `DaemonPathAllocator` receipts; raw discovery mappings via `from_mapping` stay data-only.
  - Armed conveyor construction now refuses without an injected allocator; armed runs allocate receipted paths for data-only items before prepare/land/push/PR and reject direct item paths lacking a valid receipt for the current allocator instance.
  - Retained confinement checks as defense-in-depth alongside allocator receipts.
  - Added secret-free allocation audit logging (allocation id, item key, root-relative paths, mode-check results, cleanup status).
- **ce-410-integrator-alloc-wire** (integrator belt live-repair workspace allocation): **slice 3: integrator workspace allocation via daemon receipts.**

  - Replaced predictable --work-root repair paths with daemon allocator-issued randomized workspaces (allocator.allocate_integrator_workspace receipts).
  - Added fail-closed --runtime-root queue-poll wiring and explicit --work-root refusal.
  - Cleanup now only proceeds by receipt (no rmtree of deterministic paths).
  - Added offline coverage for allocator-backed workspaces, receipt cleanup, and unsafe runtime roots.
  - Consumes the daemon path allocator module landed in the prior slice (#758) read-only.
- **ce-388-fastfollow-lease-ux** (conveyor daemon): **Fast-follow conveyor daemon lease UX and one-shot launcher flag.**

  - Added clean direct-entrypoint lease refusal handling with exit 73.
  - Renamed the launcher finite-pass flag to `--one-shot` and made `--dry-run` fail closed.
  - Documented stuck lease verification and recovery.
- **ce-415-brownfield-enabled-fix** (ce-415; installer brownfield inventory): Derive `brownfield.enabled` from real brownfield probe signals instead of
  defaulting empty probes to true. Empty non-git directories now report disabled
  brownfield adoption, while detected Git history, workflows, or test commands
  enable the brownfield inventory.
- **ce-417-pilot-runbook-gaps** (pilot documentation): **Document pilot brownfield apply prerequisites.**

  - Corrected the solo-pilot sudo guidance so the default os-native backend does not imply an unused privileged install.
  - Added pilot-facing brownfield apply prerequisites, clone/cd guidance, and the live-driver App-token permission nuance.
- **ce-428-client-workflow-template** (onboard apply emits a client-repo CE validation workflow): **client workflow template for adopted repos.**

  - Replaces the adopted-repo workflow with a signed-download wheel install and `ce check .ce/`.
  - Pins the temporary client-profile tolerate list to the four CE-resident checks pending the client-profile follow-up.
- **ce-429-repo-root-forward** (forge automerge): **Forward automerge repo root.**

  - Forwarded the parsed automerge decide --repo-root value into policy decision evaluation.
  - Added CLI coverage from a non-root working directory.
- **ce-445-daemon-container-test-gaps** (validators): **daemon container env-file/cacert refusal tests and conveyor invocation pin.**

  - Added daemon container launcher coverage for missing CE_DAEMON_ENV_FILE and CE_DAEMON_CACERT_FILE refusal paths, asserting clean stderr and no container engine invocation.
  - Added a byte-identical default conveyor-daemon invocation pin to preserve existing behavior when optional plumbing variables are unset.
- **ce-445-g10-image-daemon-deps** (deploy): **Bundle gate-daemon runtime dependencies in canonical images.**

  - Install GitHub CLI from the official signed apt repository in both canonical runtime Dockerfiles while preserving offline validator wheel builds.
  - Keep `git` installed and add static Dockerfile-content tests for the `gh` keyring/repository pins in `validators/tests/unit/test_runtime_image.py` and `validators/tests/unit/test_oci_image.py`.
- **ce-445-g9-adapter-uid-model** (deploy/daemons): **Daemon container adapter uid and state-root ownership model for Docker.**

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


- **ce-370-local-preflight-pr-body** (validators): **Local validate-pr honors PR body test-coupling exemptions.**

  - Local `ce validate-pr` now sources PR body text for the test-coupling gate when available, matching CI exemption handling while preserving strict fallback behavior.
- **ce-377-per-arch-base-digests** (surfaces): **per-arch base-image digests.**

  - Pin Rust and Debian base-image digests per target architecture for VPS amd64 and DGX arm64 builds.
  - Teach surface rendering to select the base-image digest for the requested target architecture while preserving existing digest-map output for non-base surfaces.
  - Add a surfaces manifest guard for dual-arch base images.

  Follow-up: live DGX codex-runsc image reconciliation is deferred to dev-4.
- **ce-379-workclass-choices-compat** (ce-379; validators): **Work-class validator choices accept canonical and legacy names.**

  - Accept canonical XS/S/M/L and legacy tiny/story/feature/epic work-class inputs in validator preflight parser paths.
  - Reuse the shared WORK_CLASS_INPUTS alias set and normalize through normalize_work_class.
- **ce-n1d-sshkeygen-preflight** (install): **ssh-keygen prereq actionable error in verify paths.**

  Fail-closed ssh-keygen remediation in install-spec, update, v3 verify paths.
- **ce-379-workclass-preflight-parity** (ce-379; validators): **Local PR preflight mirrors canonical work-class names.**

  - Keep `ce validate-pr` help and carrier errors aligned with `XS/S/M/L` while documenting legacy aliases.
  - Add regression coverage proving canonical carrier lines and legacy aliases normalize through the same floor behavior.
- **ce-381-automerge-decide-pathset** (ci): **Automerge decide uses PR-owned changed paths.**

  - Resolve pull_request changed paths from the GitHub PR files API before falling
    back to a fetched-base three-dot git diff.
  - Add workflow-level regression coverage for stale-base docs PR classification.
- **ce-382-brain-drift-falsered** (validators): **Brain drift validation ignores stale local runtime state.**

  - Prefer tracked `.ce/brain/assertions.yaml` for repo-local drift checks even
    when ignored `.ce/state/brain/assertions.yaml` exists.
  - Keep canonical artifact drift fail-closed while adding regression coverage for
    stale local state and genuine canonical divergence.
- **ce-370-prbody-local-parity** (validators): **Local validate-pr test-coupling PR body parity.**

  - Local `ce validate-pr` now passes explicit PR body files through to the test-coupling gate and falls back to the branch carrier when present, while staying strict when no local body source exists.
  - Moved shared git helpers out of `work_sizing_floor` private symbols for reuse by test-coupling.
- **ce-376-unscheduled-sweep** (forge-triage): **Surface commissioned unscheduled issues in forge triage.**

  - Add an advisory commissioned_unscheduled section to forge triage output.
  - Mark commissioned_unscheduled_status as arc_missing when the payload lacks the arc issue.
  - Keep dispatchable arc items unchanged and emit no mutations for the sweep section.
  - Cover default and configurable commissioned predicates with unit tests.
- **ce-382-brain-drift-local-reconcile** (validators): **Local brain drift reconcile.**

  - Add `ce brain sync` for idempotent local runtime reconciliation.
  - Auto-reconcile ignored `.ce/state/brain` drift during local validate-pr when tracked `.ce/brain` sources are unchanged.
  - Preserve canonical `.ce/brain` drift gating and add actionable remediation text.
- **ce-391b-has-milestone-scalar** (validators): **Fix forge triage milestone scalar classification.**

  - Tightened `_has_milestone` scalar fallback so false-y unknown milestone shapes remain unmilestoned while truthy scalar references count as milestones.
  - Added forge triage classification coverage for dict, list, `None`, empty string, bare string, and integer milestone payloads.
- **ce-403-scanner-hardening** (validators): **Harden public docs confidentiality scanner.**

  - Harden the confidentiality scanner so stale baseline entries, empty scans, stat failures, and tracked-file enumeration failures fail closed.
  - Add regression tests for duplicate generated carrier issue metadata and scanner failure paths.
- **ce-383-conveyor-argv-hardening** (validators): **Harden conveyor daemon argv ref handling.**

  - Add a git push option terminator before daemon remote/refspec positionals.
  - Reject unsafe base, remote, branch, landed branch, and PR base ref shapes before git/gh argv construction.
  - Keep PR title/body as unrestricted free text in fixed gh flag-value slots.
  - **Declared work class:** tiny
- **ce-410-s10-publish-reverify-audit** (conveyor): **slice 10: final publish re-verification + per-phase audit.**

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
- **ce-445-g8-dockerfile-offline-setuptools** (deploy): **Install offline setuptools before canonical wheel builds.**

  - Copy `validators/wheelhouse-dev` into both canonical-image wheel-builder stages and install `setuptools` with `--no-index` before building the validator wheel with unchanged `--no-deps --no-build-isolation` flags.
  - Fix `build-image.sh` staging: `stage_context()` and `print_stage_context_commands()` now include `wheelhouse-dev` in the staged context dir so `COPY validators/wheelhouse-dev` in the Dockerfile resolves correctly.
- **ce-portability-guard-hygiene** (validators/tests/unit/test_portability_plane.py): **Portability guard test hygiene.**

  - Isolate runtime-only subprocess command fixtures.
  - Add wrapper and absolute-path command fixtures.
  - Document fail-closed runtime-command prose behavior.
  - **Declared work class:** tiny
- **ce-401-doctrine-coverage-fastfollow** (knowledge-ssot doctrine coverage): **Harden doctrine coverage ratchet edge cases.**

  - Treat an absent authoritative brain assertion ledger as empty coverage instead of corrupt or unreadable.
  - Document the ratchet's linkage-only semantics and single-root live invocation decision.
  - Add regression tests for duplicate exception entries and stale exceptions outside governed trees.
- **ce-403-scanner-hardening-fastfollow** (validators): **Record public docs scanner hardening fast-follow.**

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
- **ce-446-base-resolve-robust** (governance): **robust moved-base comparison-base resolution in governance workflow.**

  - Resolve pull-request comparison bases through the GitHub compare API before local diff validation, avoiding shallow checkout parent traversal when the recorded PR base is behind origin/main.
  - Fetch only the server-resolved merge-base commit for local validation and report remaining graph/API failures as infrastructure failures.
  - Supersession-append the validate workflow brain assertion SHA pin for the edited workflow bytes.
  - Ratchet the brain-drift active assertion count because the validate-workflow assertion supersession intentionally adds one active ledger record.
- **ce-451-surfaces-checker-hardening** (validators): **Harden the surfaces manifest consistency checker.**

  - Treat literal `UNSET` digests as unpinned unless covered by the current CE seat image debt allowlist.
  - Ratchet the CE seat image placeholder so pinning the digest requires removing the allowlist entry.
  - Replace substring Dockerfile image matching with exact aliases and explicit image overrides.
- **ce-49-skew-guard-quickwin** (validators): **quick-win: refuse gate commands under stale-wheel version skew.**

  - Refuse gate-relevant `ce` commands when an installed package is older than the target creator-engine checkout.
  - Warn and proceed for non-gate commands, with an explicit override escape hatch.
- **ce-796-804-review-followups** (review-followups-796-804; validation): **Review follow-ups for stale-wheel and contained-seat guards.**

  - Add the silent no-skew stale-wheel guard test for matching source and installed validator versions.
  - Align non-gate stale-wheel warning escape wording with the gate refusal path and pin message ordering.
  - Document the exact-code coupling for the contained-seat path-manifest carrier bypass at both ends.

### Documentation

- **ce-docs-quickstart-step-numbering** (ce-docs-quickstart-step-numbering; quickstart guide): **Renumber quickstart steps.**

  - Renumbers the quickstart guide headings into a coherent user-facing 1 through 5 sequence.


- **ce-l2-spotcheck-openssh-note** (guide): **getting-started: openssh-client prerequisite note.**

  Note the ssh-keygen/openssh-client prerequisite for external installs.
- **ce-n15-docs-html** (site): **Render public docs to HTML.**

  - Render 6 public guide docs (understanding-ce, pilot-runbook, contributing-to-ce, solo-dev-onboarding, solo-ceo-onboarding, SECURITY_MODEL) from Markdown to styled HTML pages matching the docs/index.html dark theme.
  - Update docs/index.html #docs section links from .md to .html for all 6 rendered docs; llms-install.md remains raw .md (machine-fetched signed spec).
  - Update validators/tests/unit/test_site_index_docs_nav.py to expect .html links.
  - Cross-link strategy: published doc cross-links use rendered .html; unpublished docs inside docs/ use GitHub blob URL; paths escaping docs/ tree use repo-root blob URL.
  - Product-lens scrub: all 6 source docs and rendered HTML are clean of ce-ops# ticket refs and internal host identifiers.
- **ce-320-install-narration** (agent-native install first-touch UX): **Newcomer-clean narration for agent-native install verification.**

  Instruct the installing agent to run the §0 signature ceremony quietly and surface a single plain-language confirmation (fail-closed hard stop on any verification failure preserved); reword the homepage paste-prompt to lead with the provenance promise; re-sign llms-install.md canonical bytes with ce-root-v1 (namespace ce-spec-v1). Verification commands byte-identical.
- **ce-329-scrum-to-ce-guide** (ce-329; guide): **Draft Agile/SCRUM to CE SDLC onboarding guide.**

  - Replace the existing Agile/SCRUM guide with a public draft grounded in CE spec, plan, task, review, carrier, changelog, and ratification flow.
  - Anchor the SCRUM mapping to CE's Frame -> Shape -> Build -> Review -> Ship vocabulary and link readers to the welcome, understanding, contributing, and canonical vocabulary guides.
- **ce-393-command-deprecation-policy** (contracts): **Command deprecation policy.**

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
- **ce-410-s8a-shared-launcher** (validation-runtime): **slice 8a: shared container-launcher primitive.**

  - Add a shared Podman launcher primitive for detached and foreground ephemeral container runs.
  - Refactor worker allocation to consume the shared detached argv path without changing behavior.
- **ce-410-validation-env-scrub** (validation subprocess env-scrub sandbox seam (slice 7 rework)): **Add validation sandbox env-scrub subprocess seam.**

  - Added a typed validation-subprocess seam (`ValidationSandboxSpec` / `run_validation_sandbox`) that constructs its execution context via `ValidationSandboxContext.from_sandbox(...)` and revalidates the env allowlist against a widened credential-shaped-key filter before every invocation.
  - Routed `conveyor.py`'s `_default_validate_runner` through the sandbox seam while preserving the slice-6 validate command and scrubbed `PYTHONPATH`/`TMPDIR`/`PATH` environment (regression-pinned in `test_conveyor.py`).
  - Extended (not replaced) the slice-4 `forge/authority_contexts.py` module: widened `_FORBIDDEN_CREDENTIAL_KEYS`/added token-pattern matching, added `require_no_credential_env`/`is_credential_env_key` helpers; `TransportCredentialContext`, `LocalGitContext`, and `ValidationSandboxContext.from_sandbox` are unchanged.
- **ce-437-adr-two-plane** (two-plane OS architecture ADR): **Add ADR-0014 for the two-plane OS architecture.**

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

- **ce-l1-install-doc-fix** (install): **Install spec: openssh-client prereq + 0.3.1 alignment, re-signed.**

  Add openssh-client prerequisite note + align one-liner prose to 0.3.1, and re-sign the canonical spec with the offline ce-root-v1 trust root.

### Ci

- **ce-l7-injection-cleanup** (release): **Harden release workflow GitHub expression injection boundaries.**

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

- **ce-ci-runblock-injection-guard** (ci): **CI run block injection guard test.**

  - Add a parser-based unit guard for GitHub Actions expressions embedded in workflow `run:` blocks.

### Tiny

- **ce-451-zeros-digest-guard** (surfaces manifest placeholder digest guard): **Reject placeholder surface sha256 digests.**

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
