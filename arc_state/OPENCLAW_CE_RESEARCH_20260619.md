# OpenClaw Ecosystem -> CE v3.5 Relevance Distillation

Date: 2026-06-19 UTC  
Mode: read-only repository research. No CE code or PRs touched.  
Scope: closed manifest only. P1 repos received README plus architecture/key-module skim; P2 repos received README plus quick skim.  
Method: one explorer subagent per repository, run in waves capped at six concurrent explorers.

## Executive Takeaways

OpenClaw's strongest prior art is not any one codebase. It is the repeated pattern of putting autonomous agents behind durable job records, explicit state machines, deterministic apply gates, and operator-visible evidence. CE's v3.5 plan is directionally aligned, but OpenClaw exposes two urgent gaps: WS-2 needs a concrete throughput stack, and WS-5 should start with an evidence ledger before CE's first public release.

The highest-value mechanisms for CE to steal are:

1. WS-2: local GitHub/PR operational mirror plus durable cluster jobs, schema-validated agent decisions, deterministic mutation, and a fleet cockpit.
2. WS-5: release evidence ledger with two-stage preflight/publish, blocking vs advisory run classification, provenance checks, artifact metadata, and signed-release extensions.
3. WS-1/WS-3: disposable dev-seat lease lifecycle, warm pools, diff sync, doctor/sync-plan preflights, and explicit filesystem capability boundaries.
4. WS-4: org-authenticated read broker/token relay that keeps GitHub credentials outside agents, with route policy, cache partitioning, and identity rechecks.
5. WS-7 feeding CRIT: deterministic-first "grader outside the agent" benchmark and runtime-validation matrix that score harness+config+model, not LLM alone.

## Top 5 CE v3.5 Changes/Additions

1. Build a minimal WS-2 PR-throughput stack now.
   - Start with a GitHub operational mirror/cache (`gitcrawl`, `octopool`) for issues, PRs, checks, review threads, comments, and Actions state.
   - Add durable work records: cluster/job files, item snapshots, target `updated_at` and head-SHA replay guards (`clownfish`, `clawsweeper`).
   - Force agent outputs through schemas and separate "proposal" from "apply" (`clownfish` `schemas/codex-result.schema.json`, `clawsweeper` apply guards).
   - Add a PR-promotion record with changed-file whitelist, validation result, base SHA, branch/commit/PR URL (`clawpatch`).
   - Put it behind a cockpit with stable work IDs, session attach/share/stop controls, transcripts, and status lanes (`crabfleet`).

2. Put WS-5 evidence ledger into the first release milestone, not after releases exist.
   - OpenClaw's `releases` repo shows the right ordering: preflight -> validation -> publish -> normalized evidence.
   - CE should create a release ledger before v0.1 so the first release has an evidence record, not a retroactive note.
   - Extend OpenClaw's pattern with CE-specific requirements: Sigstore/SLSA/SBOM, signed containers/packages, tamper-evident ledger commits, and verifier docs.

3. Make WS-3 install/pilot readiness a two-phase envelope.
   - Phase 1: provision hardened host substrate, service user, firewall/Tailscale/Docker guardrails, directories, and idempotency checks (`openclaw-ansible`).
   - Phase 2: product CLI performs secrets/config/daemon onboarding.
   - Add `doctor`, `sync-plan`, hydration checks, and convergence tests (`crabbox`, `openclaw-ansible`).

4. Treat runtime access as capability objects and leases.
   - Disposable seats should have explicit lease state, TTL/idle cleanup, per-lease identity material, and warm-pool lifecycle (`crabbox`).
   - Filesystem access should cross one root-bound boundary primitive, not scattered path checks (`fs-safe`).
   - Terminal/session transport should be product-neutral with bounded replay/fanout while policy/auth remain outside (`libterminal`).

5. Tie the grader-outside-agent program to releases and runtime validation.
   - `clawbench` validates CE's grader north star: deterministic verifiers first, optional LLM judge second, full transcript/artifact grading outside the agent.
   - `Kova` adds the missing release-readiness piece: declarative surface x state x target x platform matrices and an evidence ledger that can fail a release.
   - CE should score harness+config+model+runtime, not just model selection.

## Top 3 Places OpenClaw Validates CE Direction

1. Governed automation beats autonomous mutation. `clownfish`, `clawsweeper`, and `clawpatch` repeatedly split agent reasoning from deterministic mutation and promotion. This validates CE's "grader outside the agent" and governed SDLC posture.

2. Containment and disposable seats are the right substrate. `crabbox`, `caclawphony`, `fs-safe`, and `libterminal` all converge on isolated workspaces/sessions, bounded transports, and explicit lifecycle. OpenClaw is less strict than CE on hostile containment, but the shape validates WS-1.

3. Release integrity needs a first-class evidence system. `releases`, `Kova`, `clawbench`, `crabpot`, and `plugin-inspector` all turn validation into durable artifacts. This validates CE's plan to put evidence and grading outside the agent and attach it to versioned releases.

## Specific Comparisons Requested

### A. Merge-throughput / triage stack vs CE WS-2

OpenClaw does not appear to have one monolithic "merger agent" repo. The usable prior art is a composable stack:

1. Read model/cache: `gitcrawl` mirrors GitHub issues/PRs/reviews/checks locally; `octopool` relays safe GitHub reads through a credential-containing cache.
2. Triage proposal: `clawsweeper` produces durable per-item review state, exact-head comments, labels, and dashboards.
3. Cluster execution: `clownfish` batches one cluster per job, hydrates context, gets schema-validated Codex JSON, and runs deterministic guarded apply scripts.
4. Patch promotion: `clawpatch` persists finding/patch attempts, validation results, changed-file allowlists, base SHA, and draft PR creation.
5. Mission control: `crabfleet` gives stable work IDs, session lineage, attach/share controls, transcripts, summaries, and operator visibility.

Minimal set CE should copy for WS-2:

- Local GitHub mirror/cache with stale-sync controls and review-thread/check-state coverage.
- Durable work item schema: source item, snapshot/head SHA, assigned controller, phase, attempts, evidence, and terminal reason.
- Proposal/apply split: agent proposes, deterministic code re-fetches live state and applies only if guards still hold.
- PR promotion contract: changed-file whitelist, validation gate, base SHA, branch/commit/PR URL, and draft-by-default path.
- Cockpit lanes: queued, running, waiting-human, validation-failed, ready-to-merge, merged, closed/not-planned.

Avoid copying a false conclusion: `clawpatch` explicitly does not implement landing/merge automation yet. CE still needs to design its own merger-agent/merge-queue around branch protection, reviewer eligibility, approvals, required checks, and evidence completeness.

### B. `releases` evidence ledger vs CE signed-release pipeline

OpenClaw's `releases` repo is directly relevant to WS-5. It keeps product source elsewhere and commits normalized release evidence into a separate ledger. The strongest mechanism is two-stage promotion: a preflight build/sign/notarize step, then real publish requiring explicit successful preflight and validation run IDs, artifact reuse, tag/SHA checks, and evidence generation.

CE should steal the ledger pattern but strengthen it:

- Keep release evidence separate from volatile CI logs.
- Record blocking vs advisory checks, source SHA, tag, package metadata, artifact names/sizes/expiry, validation run URLs, timing, and publish target state.
- Add CE-specific integrity: signed artifacts, SBOM, provenance attestations, container image digests, reproducible install transcript, and verifier instructions.
- Treat missing evidence as a release blocker.

### C. `clawbench` vs CE grader-outside-agent

`clawbench` strongly validates CE's north star. It does not just rank an LLM. It scores an agent stack: harness, configuration, model, tools, runtime behavior, trace, artifacts, and repeat reliability. Its deterministic-first scoring means an LLM judge cannot rescue a failed deterministic completion.

CE should copy:

- Deterministic verifier first, optional LLM judge sidecar second.
- Full transcript/artifact capture outside the agent.
- Failure taxonomy and reproducible task manifests.
- Multi-run reliability scores such as pass^k and worst-of-n.
- Partner trace schema that records harness/model/config/plugin provenance.

### D. `caclawphony` vs CE strangeLoop direction

`caclawphony` is relevant less as code and more as an orchestration contract. Its useful pattern is tracker-as-state-machine: workflow file defines active states, terminal states, gates, prompts, hooks, concurrency, and workspace lifecycle. It also uses deterministic per-issue workspaces and state-aware throttles.

CE should adopt the pattern, but not the trust posture. `caclawphony` currently uses high-trust settings such as `danger-full-access` and `approval_policy: never` in its documented workflow. CE's strangeLoop should instead bind that state-machine model to OpenShell/gVisor containment, CE identities, governed secrets, and external grading.

## Per-Repo Findings

### P1 Deep Repos

#### openclaw/crabfleet

1. What it actually does: Active mission-control app for OpenClaw/Codex `crabbox` sessions. Primary languages: TypeScript/JavaScript Worker + Preact UI, Go CLI/SSH gateway, smaller Swift prototype. Last commit: 2026-06-19 `49daebe`; not stale. It provides fleet roster, cards/boards, terminal grid, WebVNC affordances, sandbox/runtime-adapter lifecycle, GitHub Actions session registration/relay, logs/transcripts, sharing/control delegation, and OpenClaw room APIs. Key paths: `README.md`, `docs/architecture.md`, `docs/runs.md`, `docs/github-actions-sessions.md`, `src/worker/session-control-do.ts`, `src/worker/openclaw-supervision.ts`, `src/worker/routes/openclaw.ts`, `src/app/fleet.jsx`, `src/app/session-workspace.jsx`, `cmd/crabfleet/main.go`.
2. Reusable idea / pattern / seam: Treat multi-agent work as durable session identity plus control-plane evidence. Steal stable logical work IDs, parent/root session rooms, runner/viewer credential split, explicit control delegation, and transcript/summary APIs.
3. CE workstream: WS-2 primary.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify deployed Cloudflare environment, real Actions sessions, runtime adapter providers, or production auth settings.

#### openclaw/clownfish

1. What it actually does: Active Node.js/JavaScript maintainer automation for one-cluster OpenClaw issue/PR cleanup. It hydrates GitHub cluster state, asks Codex for structured JSON decisions, validates them, then deterministic scripts apply guarded close/repair/merge actions. Primary language: JavaScript ESM. Last commit: 2026-06-19 `b1b9904a`; not stale. Key paths: `README.md`, `docs/INTERNAL_FEATURES.md`, `docs/OPERATIONS.md`, `scripts/plan-cluster.mjs`, `scripts/run-worker.mjs`, `scripts/review-results.mjs`, `scripts/apply-result.mjs`, `scripts/execute-fix-artifact.mjs`, `scripts/comment-router*.mjs`, `.github/workflows/cluster-worker.yml`.
2. Reusable idea / pattern / seam: Durable job + hydrated context artifact + schema-validated model result + deterministic executor. Especially useful: one cluster per job file, concurrency groups, `target_updated_at` and head-SHA replay guards, idempotent comment routing, repair caps, no GitHub token in Codex env, and credited replacement PRs.
3. CE workstream: WS-2 primary; WS-4 and WS-7 secondary.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify live Actions artifacts/secrets, App permissions, or production success rates.

#### openclaw/clawsweeper

1. What it actually does: Active TypeScript maintenance bot for OpenClaw repos. It reviews issues/PRs, writes durable state records, syncs one marker-backed public review comment, applies guarded close decisions, routes maintainer commands, runs bounded repair/automerge loops, and publishes dashboards. Last commit: 2026-06-19 `471bf80`; not stale. Key paths: `README.md`, `src/clawsweeper.ts`, `.github/workflows/sweep.yml`, `.github/workflows/repair-comment-router.yml`, `docs/scheduler.md`, `docs/pr-review-comments.md`, `docs/triage-dashboard.md`, `docs/pr-proof-triage-dashboard.md`, `instructions/closure-policy.md`, `instructions/dedupe.md`, `instructions/low-signal-prs.md`.
2. Reusable idea / pattern / seam: Split AI review/proposal from deterministic apply. Store item snapshot metadata, emit one mutable marker-backed comment, then re-fetch live GitHub state and enforce protected labels, authorship, linked PRs, age gates, and snapshot drift before mutation.
3. CE workstream: WS-2 primary; WS-6 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live production behavior, generated state repo, dashboard runtime data, GitHub App install, or current scheduled Action health.

#### openclaw/clawpatch

1. What it actually does: Active TypeScript/Node CLI for agentic code review and repair. It maps repos into feature records, runs provider-backed review, persists findings/patch attempts under `.clawpatch/`, runs finding-scoped fixes, validates them, and can open GitHub PRs. Last commit: 2026-06-18 `0f0b645`; not stale. Key paths: `README.md`, `src/review.ts`, `src/fix.ts`, `src/open-pr.ts`, `src/state.ts`, `src/types.ts`, `docs/code-review.md`, `docs/patching.md`, `docs/safety.md`, `docs/spec.md`.
2. Reusable idea / pattern / seam: Durable promotion pipeline: feature slice -> validated finding -> patch attempt -> explicit PR. Patch-attempt records carry changed files, validation results, base SHA, branch/commit/PR URL. `open-pr` stages only recorded files and refuses failed validation unless forced.
3. CE workstream: WS-2 primary; WS-1 and WS-5 secondary.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify real reviewer interaction, branch protection, CI integration, or merge/land policy. `clawpatch land` appears post-v0/spec-only rather than implemented.

#### openclaw/caclawphony

1. What it actually does: Elixir/OTP maintainer tool for OpenClaw PR intake, triage, review, prepare, merge, and closure through Linear-state-driven Codex agents. Last commit: 2026-05-28 `bc7adb6`; not stale. Key paths: `WORKFLOW.md`, `elixir/README.md`, `elixir/mix.exs`, `elixir/lib/mix/tasks/caclawphony.review.ex`, `elixir/lib/mix/tasks/caclawphony.triage.ex`, `elixir/lib/symphony_elixir/orchestrator.ex`, `elixir/lib/symphony_elixir/workspace.ex`, `elixir/lib/symphony_elixir/agent_runner.ex`, `elixir/lib/symphony_elixir/codex/app_server.ex`, `elixir/lib/symphony_elixir/codex/dynamic_tool.ex`.
2. Reusable idea / pattern / seam: Tracker-as-state-machine contract: active states, terminal states, human gates, prompts, hooks, concurrency, sandbox posture, deterministic per-issue workspaces, and phase-specific throttles.
3. CE workstream: WS-1 and WS-2 primary; WS-7 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live Linear/GitHub/Codex execution, external maintainer skills, production reliability, or runtime enforcement. Do not copy its documented `danger-full-access`/`approval_policy: never` posture.

#### openclaw/crabbox

1. What it actually does: Go-first remote execution CLI/control plane for short-lived developer/test runners: lease a box, sync dirty checkout, run commands/tests, stream logs, record results, and release or reuse. Primary languages: Go and TypeScript. Last commit: 2026-06-20 +0800 `135d306`; not stale. Key paths: `README.md`, `SECURITY.md`, `docs/architecture.md`, `docs/orchestrator.md`, `docs/provider-backends.md`, `docs/features/sync.md`, `docs/features/doctor.md`, `docs/features/test-results.md`, `docs/spec/broker.md`, `docs/commands/prewarm.md`, `internal/cli/run.go`, `internal/cli/provider_backend.go`, `internal/cli/ready_pool.go`, `worker/src/fleet.ts`.
2. Reusable idea / pattern / seam: CLI-owned data plane, broker-owned control plane. Steal provider seams, diff sync with git manifests/fingerprints, mass-deletion guard, prewarmed ready pools, lease TTL/idle cleanup, non-mutating `doctor`, sync previews, and structured test results.
3. CE workstream: WS-3 primary; WS-1 secondary.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify live provider smokes, broker deployments, warm-pool latency, or isolation beyond documented trusted-team model.

#### openclaw/octopool

1. What it actually does: Active TypeScript Cloudflare Worker plus Go CLI. It is a self-hosted GitHub read relay/cache; CLI shim sends safe read-shaped `gh` requests to `POST /v1/github/request` and falls back to real `gh` for mutations. Last commit: 2026-06-19 `38193b6`; not stale. Key paths: `README.md`, `docs/relay.md`, `src/relay.ts`, `src/provisioning.ts`, `src/auth.ts`, `cmd/octopool/login.go`, `cmd/octopool/gh.go`, `cmd/octopool/gh_api.go`, `cmd/octopool/gh_fallback.go`, `src/github-auth.ts`, `src/policy.ts`, `src/public-repos.ts`, `src/github-sanitize.ts`, `src/route-manifest.ts`, `src/cache.ts`, `src/cache-coalesce.ts`, `src/pool-coordinator.ts`, `migrations/0001_init.sql`, `migrations/0002_github_cache.sql`, `migrations/0011_cache_stale_retention.sql`.
2. Reusable idea / pattern / seam: Org-authenticated read broker: users hold one relay token while GitHub PAT/App credentials stay server-side. Split caller auth, route policy, public/private proofing, identity selection, cache publication, sanitization, and cache-miss coalescing.
3. CE workstream: WS-4 and WS-2.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify live deployment, production secrets/App scopes, cache hit rates, or test suite. Caveat: public-repo-only; CE needs tenant/repo-scoped authorization for private repos.

#### openclaw/releases

1. What it actually does: Release automation and evidence ledger for OpenClaw, separate from product source. Primary file types/languages: JSON/Markdown evidence, Node.js JavaScript scripts, GitHub Actions YAML. Last commit: 2026-06-13 `7a6332b`; not stale. Key paths: `README.md`, `.github/workflows/openclaw-macos-publish.yml`, `.github/workflows/openclaw-macos-validate.yml`, `.github/workflows/openclaw-npm-dist-tags.yml`, `.github/workflows/openclaw-release-evidence.yml`, `.github/workflows/openclaw-release-evidence-from-full-validation.yml`, `scripts/openclaw-release-evidence.mjs`, `scripts/openclaw-release-evidence-from-full-validation.mjs`, `evidence/<release-id>/release-evidence.json`.
2. Reusable idea / pattern / seam: Separate release-evidence ledger with two-stage promotion. Preflight builds/signs/notarizes; publish requires explicit successful preflight + validation run IDs, reuses artifacts, checks tag/SHA provenance, and records normalized evidence.
3. CE workstream: WS-5 primary; WS-3 secondary.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify live secret config, branch protection, Apple cert/notarization validity, release asset bytes, or artifact availability. No repo-native Sigstore/SLSA/SBOM attestation found.

#### openclaw/clawbench

1. What it actually does: Active Python 3.11+ benchmark/CLI for evaluating OpenClaw agents. It runs a 19-task public Core v1 suite with YAML task specs, deterministic verifiers, background services, simulated user turns, and optional LLM judge rubrics. Last commit: 2026-06-10 `8834e7d`; not stale. Key paths: `tasks-public/MANIFEST.yaml`, `tasks-public/README.md`, `tasks-public/tier3/t3-web-research-and-cite.yaml`, `tasks-public/assets/t3_web_research_and_cite/verify_explainer.py`, `tasks-public/tier4/t4-delegation-repair.yaml`, `tasks-public/tier4/t4-memory-recall-continuation.yaml`, `tasks-public/tier5/t5-hallucination-resistant-evidence.yaml`, `clawbench/environment.py`, `clawbench/trajectory.py`, `clawbench/schemas.py`, `clawbench/judge.py`, `clawbench/scorer.py`, `clawbench/stats.py`, `clawbench/harness.py`, `clawbench/canonical/schema.py`, `clawbench/adapters/base.py`, `PARTNER_TRACE_SPEC.md`.
2. Reusable idea / pattern / seam: Grader outside agent: agent emits artifacts/transcript; deterministic verifiers and trace analysis run outside; optional LLM judge is sidecar and gated behind deterministic success. Also steal task fingerprints, partner trace schema, pass^k/worst-of-n reliability, and isolated per-run state.
3. CE workstream: WS-7 primary; WS-5 and WS-1 secondary; minor WS-2.
4. Verdict: steal-specific-mechanism.
5. Confidence: high for architecture, medium for empirical benchmark claims. Could not verify private task pool, sweep archives, gateway behavior, Docker runtime, judge quality, hidden releases, or non-OpenClaw adapters.

### P2 Light Repos

#### openclaw/gitcrawl

1. What it actually does: Local-first GitHub issue/PR crawler and maintainer triage tool. It syncs GitHub metadata into SQLite, supports FTS/search, PR-detail hydration, clustering/governance, JSON automation surfaces, and Bubble Tea TUI. Primary language: Go. Last commit: 2026-06-19 `0ac64c1`; not stale, but README labels it early bootstrap. Key paths: `README.md`, `SPEC.md`, `cmd/gitcrawl/main.go`, `internal/cli/app.go`, `internal/cli/tui.go`, `internal/store/schema.go`, `internal/syncer/syncer.go`, `internal/github/review_threads.go`.
2. Reusable idea / pattern / seam: Local operational mirror for expensive/live GitHub reads, with `--sync-if-stale` and durable PR files/commits/checks/review-thread state.
3. CE workstream: WS-2 primary; WS-7 secondary; minor WS-3/WS-6.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not run Go tests, verify live OAuth, remote Worker archive, or real sync behavior.

#### openclaw/crawlkit

1. What it actually does: Go module for provider-neutral local-first crawler archive mechanics: SQLite/store helpers, snapshot/import/export, git mirrors, encrypted backups, embeddings/vector search, remote archive contracts, release checks, app metadata/status, scheduler, and shared TUI. Last commit: 2026-06-19 `797628a`; not stale. Key paths: `README.md`, `docs/boundary.md`, `cmd/crawlctl/main.go`, `scheduler/run.go`, `snapshot/snapshot.go`, `remote/contract.go`, `control/control.go`, `docs/publishing.md`, `.github/workflows/ci.yml`.
2. Reusable idea / pattern / seam: Provider-neutral mechanics, app-owned semantics. Define stable manifests/contracts/status DTOs while downstream apps own auth, schemas, privacy, ranking, and compatibility.
3. CE workstream: WS-7 primary; WS-3/WS-5 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not run Go tests or verify downstream adoption.

#### openclaw/clawhub

1. What it actually does: Public OpenClaw registry/catalog for versioned `SKILL.md` skills and code/bundle plugins. Includes web UI, Convex backend/API, shared schema package, and CLI for login/search/install/publish. Primary languages: TypeScript/TSX. Last commit: 2026-06-19 `7760696`; not stale. Key paths: `README.md`, `docs/how-it-works.md`, `package.json`, `convex/schema.ts`, `convex/httpApiV1.ts`, `packages/clawhub/src/cli.ts`, `packages/schema/src/routes.ts`, `packages/schema/src/schemas.ts`, `packages/schema/src/openclawContract.ts`.
2. Reusable idea / pattern / seam: Registry artifacts as immutable, versioned records with provenance, compatibility metadata, moderation/scan status, and CLI/API/UI parity around one model.
3. CE workstream: WS-7, WS-5, WS-6.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live production behavior, deployed data quality, or documented flow health.

#### openclaw/agent-skills

1. What it actually does: Canonical shared agent workflow skills repo. Distributes `SKILL.md` workflows for transcript redaction, autoreview, remote validation, handoff prompts, and session viewing, with install/validation tooling. Primary languages by LOC: TypeScript, Markdown, JavaScript, Python, Ruby. Last commit: 2026-06-19 `283f069`; not stale. Key paths: `README.md`, `skills/*/SKILL.md`, `skills.sh.json`, `scripts/install-skills`, `scripts/validate-skills`, `.github/workflows/validate.yml`, `skills/agent-transcript/scripts/agent-transcript`, `skills/autoreview/scripts/autoreview`, `skills/session-viewer/scripts/core/detect.ts`.
2. Reusable idea / pattern / seam: Versioned, installable agent workflow packages with canonical `skills/<name>/SKILL.md`, optional helper scripts, symlink/copy install modes, frontmatter validation, and generated downstream snapshots.
3. CE workstream: WS-2, WS-3, WS-6, WS-7.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live Crabbox/Testbox access, reviewer CLIs/models, publishing behavior, or vendored snapshot drift.

#### openclaw/lobster

1. What it actually does: TypeScript-first Node package for OpenClaw-native workflow shell/runtime: JSON pipelines, workflow files, approval/input gates, resumable state, CLI/tool envelopes, SDK embedding, and recipes such as GitHub PR monitoring. Last commit: 2026-06-18 `d759d5c`; not stale. Key paths: `README.md`, `package.json`, `src/cli.ts`, `src/runtime.ts`, `src/workflows/file.ts`, `src/core/tool_runtime.ts`, `src/commands/registry.ts`, `src/commands/stdlib/openclaw_invoke.ts`, `src/commands/stdlib/openclaw_agent.ts`, `src/pipeline_resume_state.ts`, `src/state/store.ts`, `src/commands/stdlib/approve.ts`, `src/recipes/github/pr-monitor.ts`, `src/workflows/github_pr_monitor.ts`.
2. Reusable idea / pattern / seam: Agent-chosen, deterministic workflow execution as a thin layer. The agent decides intent; workflow runtime executes typed steps, hard-stops on approvals/input, persists state, and delegates auth/tool identity to existing surfaces.
3. CE workstream: WS-2 primary; WS-7 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live gateway behavior, authenticated `gh` recipe execution, npm health, or runtime tests.

#### openclaw/openclaw-ansible

1. What it actually does: Ansible installer/collection for Debian/Ubuntu OpenClaw hosts. Primary languages: YAML/Ansible, Shell, Jinja2. It provisions system tools, optional Tailscale, Docker, UFW/fail2ban, Node.js/pnpm, a dedicated `openclaw` user, and installs OpenClaw via npm release mode or git-build development mode. Last commit: 2026-06-15 `88614ea`; not stale. Key paths: `install.sh`, `playbook.yml`, `playbooks/install.yml`, `roles/openclaw/tasks/main.yml`, `roles/openclaw/tasks/user.yml`, `roles/openclaw/tasks/firewall-linux.yml`, `roles/openclaw/tasks/openclaw.yml`, `roles/openclaw/tasks/openclaw-release.yml`, `roles/openclaw/tasks/openclaw-development.yml`, `docs/security.md`, `docs/architecture.md`, `tests/README.md`.
2. Reusable idea / pattern / seam: Two-phase pilot installer: hardened host envelope first, then app secrets/config/daemon setup through product CLI. Include dedicated user, scoped sudo, sensitive directory skeleton, firewall/runtime guardrails, verification checklist, and `ci_test` idempotency mode.
3. CE workstream: WS-3 primary; WS-1 and WS-4 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live Debian/Ubuntu convergence, firewall/Tailscale behavior, npm installability, or CLI onboarding/daemon behavior.

#### openclaw/crabpot

1. What it actually does: Node.js 22 / JavaScript ES-module compatibility testbed for OpenClaw plugin contracts. It maintains curated real plugin fixtures, validates expected seams, and publishes generated compatibility reports. Last commit: 2026-06-17 `d3700b9`; not stale. Key paths: `README.md`, `crabpot.config.json`, `crabpot.schema.json`, `crabpot.ci-policy.json`, `scripts/run-static-suite.mjs`, `scripts/cold-import-readiness.mjs`, `scripts/synthetic-probes.mjs`, `.github/workflows/check.yml`, `.github/workflows/openclaw-ref-compat.yml`, `reports/`.
2. Reusable idea / pattern / seam: Manifest-driven compatibility trap: pin representative external integrations, tag them by contract seam, generate JSON/Markdown reports, and gate drift with explicit policy exceptions.
3. CE workstream: WS-7 primary; WS-5 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live CI, fixture runtime behavior, or report reproducibility.

#### openclaw/plugin-inspector

1. What it actually does: Node.js 22+ ESM CLI/library for offline OpenClaw plugin compatibility checks. It inspects plugin roots/fixtures for package metadata, plugin manifests, hooks, registrations, SDK imports, deprecations, and expected seams, then emits JSON/Markdown/SARIF/JUnit/CI policy artifacts. Last commit: 2026-06-17 `84b6ffc`; not stale. Key paths: `README.md`, `package.json`, `src/cli.js`, `src/inspector.js`, `src/report.js`, `src/ci-summary.js`, `src/ci-policy.js`, `src/api.js`, `src/mock-sdk-capture-runner.js`, `src/sdk-mock.js`.
2. Reusable idea / pattern / seam: Static-first, credential-free compatibility inspection with stable report schema, severity/classification model, CI artifact fanout, and hard execution boundary for untrusted plugin code.
3. CE workstream: WS-7 primary; WS-5 and WS-3 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify CI status, npm package state, external corpus behavior, or Crabpot follow-through.

#### openclaw/kitchen-sink

1. What it actually does: Credential-free OpenClaw plugin fixture/boilerplate that exercises plugin API surfaces: commands, hooks, channels, providers, context engine, detached tasks, gateway/service/CLI, and deterministic media/search/fetch/memory scenarios. Primary language: JavaScript/Node ESM. Last commit: 2026-06-16 `715573b`; not stale. Key paths: `README.md`, `package.json`, `openclaw.plugin.json`, `src/index.js`, `src/kitchen-runtime.js`, `src/scenarios.js`, `src/runtime/providers.js`, `src/personality.js`, `scripts/sync-surface.mjs`, `scripts/openclaw-surface.mjs`, `.github/workflows/check.yml`, `.github/workflows/update-openclaw-sdk.yml`, `.github/workflows/release.yml`.
2. Reusable idea / pattern / seam: Contract canary plugin: deterministic, no-credentials fixture that registers every supported integration seam, splits conformance from adversarial diagnostics, and regenerates SDK-surface coverage from installed declarations.
3. CE workstream: WS-7 primary; WS-3 and WS-5 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify live npm/ClawHub availability, Actions results, or runtime behavior inside live OpenClaw.

#### openclaw/acpx

1. What it actually does: Active TypeScript/Node headless Agent Client Protocol client that talks structured JSON-RPC/NDJSON over stdio to coding-agent adapters instead of scraping PTYs. It provides agent command resolution, persistent cwd/named sessions, local queue-owner IPC, permission mediation, flow orchestration, and draft ACP conformance tests. Last commit: 2026-06-19 `ce0f657`; not stale. Key paths: `README.md`, `src/acp/client.ts`, `src/agent-registry.ts`, `docs/sessions.md`, `src/session/persistence.ts`, `src/cli/session/queue-owner-runtime.ts`, `src/cli/queue/*`, `docs/permissions.md`, `src/permissions.ts`, `docs/flows.md`, `src/flows/runtime.ts`, `conformance/README.md`, `conformance/runner/run.ts`, `conformance/cases/*.json`.
2. Reusable idea / pattern / seam: Protocol client as coordination substrate: normalize agent access through ACP, separate live connection ownership from session records, and let later invocations enqueue through local owner lease. Split workflows into deterministic runtime nodes and agent-owned ACP turns.
3. CE workstream: WS-7 primary; WS-2 secondary.
4. Verdict: steal-specific-mechanism.
5. Confidence: high. Could not verify CI, npm artifact contents, real adapter behavior, or CE overlap.

#### openclaw/libterminal

1. What it actually does: Active TypeScript npm package for shared terminal primitives across browser, Node.js, and Cloudflare Workers. It provides protocol v2 codecs/vectors, bounded replay/fanout/batching, Ghostty browser integration, optional `node-pty` helpers, Worker WebSocket bridging, pinned Ghostty assets, and test doubles. Last commit: 2026-06-19 `0da07a0`; not stale. Key paths: `README.md`, `package.json`, `src/protocol.ts`, `protocol/terminal-v2.json`, `src/stream.ts`, `src/browser.ts`, `src/node.ts`, `src/worker.ts`, `scripts/check-pack.mjs`, `.github/workflows/release.yml`.
2. Reusable idea / pattern / seam: Keep terminal transport product-neutral: byte framing, validation, ordering, bounded buffers, replay, adapters, and deterministic test doubles in the library; auth, sessions, URLs, transcripts, listeners, and policy in the product.
3. CE workstream: WS-1 primary; WS-7 secondary; minor WS-5.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify npm package contents or live Actions without installing/running checks.

#### openclaw/rfcs

1. What it actually does: Markdown RFC repository for OpenClaw design proposals and technical decisions. Primary language: Markdown. Last commit: 2026-06-17 `e7555fd`; not stale. Key paths: `README.md`, `rfcs/0000-template.md`, `rfcs/0001-lts-release-policy.md`, `rfcs/0007-e2e-qa-lab-scorecard-consolidation.md`, `rfcs/0007/implementation-plan.md`, `rfcs/0007/example-scorecard-checklist.md`, `rfcs/0008-context-engine-runtime-settings.md`.
2. Reusable idea / pattern / seam: Lightweight RFC governance with YAML frontmatter, lifecycle/status/issue/PR, fixed proposal sections, sidecar folders, implementation plans, diagrams, inventories, and scorecard mappings.
3. CE workstream: WS-6 and WS-5; WS-7 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify linked implementation state or discussion threads; no CI enforces lifecycle metadata.

#### openclaw/Kova

1. What it actually does: Node.js ESM CLI/runtime validation lab for OpenClaw, with JSON registries and Astro/TypeScript report site. It plans/runs OCM-backed OpenClaw scenario matrices, gates releases, records evidence, and renders reports. Last commit: 2026-05-28 `fe1fb10`; not stale. Key paths: `README.md`, `package.json`, `bin/kova.mjs`, `src/main.mjs`, `src/run/engine.mjs`, `src/matrix/gate.mjs`, `src/evidence-ledger.mjs`, `src/registries/context.mjs`, `src/registries/scenarios.mjs`, `docs/REPORT_SCHEMA.md`, `profiles/release.json`, `scenarios/`, `surfaces/`, `states/`, `profiles/`, `process-roles/`, `channel-capabilities/`, `support/channel-conformance/`, `web/package.json`.
2. Reusable idea / pattern / seam: Declarative surface x state x target x platform validation matrix plus evidence ledger that prevents green builds when proof is missing. Data contracts drive runtime coverage instead of hardcoded smoke tests.
3. CE workstream: WS-5 primary; WS-3 and WS-1 secondary; WS-7 also relevant.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify actual OCM/OpenClaw execution, live report correctness, credential handling, or gate calibration.

#### openclaw/fs-safe

1. What it actually does: Node/TypeScript filesystem-safety npm package. It exposes a capability-style `root()` handle for bounded reads/writes/moves/removes, atomic writes, JSON/file stores, secret-file helpers, archive extraction, temp workspaces, locks, and path utilities. Last commit: 2026-06-17 `644a27c`; not stale. Key paths: `README.md`, `package.json`, `src/root-impl.ts`, `src/root-context.ts`, `src/path-policy.ts`, `src/pinned-python.ts`, `src/archive.ts`, `src/output.ts`, `CHANGELOG.md`, `test/read-boundary-bypass.test.ts`, `test/write-boundary-bypass.test.ts`, `test/adversarial-boundary-payloads.test.ts`.
2. Reusable idea / pattern / seam: Filesystem access as explicit capability object. Route untrusted relative paths through one root-bound API, pin identity at use time, stage external outputs before commit, and back safety with adversarial path corpora/regression tests.
3. CE workstream: WS-1 primary; WS-4 secondary.
4. Verdict: adopt-pattern.
5. Confidence: high. Could not verify npm provenance, CE adoption, or runtime security under real cross-process races/Windows edge cases.

## Cross-Workstream Map

| Workstream | Strongest OpenClaw references | CE implication |
| --- | --- | --- |
| WS-1 Containment & runtime substrate | `crabbox`, `caclawphony`, `fs-safe`, `libterminal`, `clawbench`, `Kova` | Keep OpenShell/gVisor as stronger substrate, but steal leases, root-bound FS capability, terminal transport boundaries, and per-run workspaces. |
| WS-2 Team-mode PR throughput & coordination | `crabfleet`, `clownfish`, `clawsweeper`, `clawpatch`, `gitcrawl`, `lobster`, `acpx`, `octopool` | This is the biggest plan gap. Build a composed throughput stack with mirror, job records, deterministic apply, PR promotion, and cockpit. |
| WS-3 Install & pilot-readiness | `openclaw-ansible`, `crabbox`, `agent-skills`, `kitchen-sink`, `plugin-inspector`, `Kova` | Ship hardened host envelope plus product onboarding; add `doctor`, sync previews, and install/runtime canaries. |
| WS-4 Secret & identity | `octopool`, `clownfish`, `openclaw-ansible`, `fs-safe` | Keep credentials out of agents; use token relay, secret refs, route allowlists, org/repo rechecks, and per-seat identity. |
| WS-5 Release integrity & versioning | `releases`, `Kova`, `clawbench`, `crabpot`, `plugin-inspector`, `clawhub`, `rfcs` | Start evidence ledger now; combine release, benchmark, compatibility, and RFC evidence into versioned release gates. |
| WS-6 Documentation & product surface | `rfcs`, `agent-skills`, `clawhub`, `clawsweeper` | Add RFC-to-evidence docs and user-facing queue/dashboard/comment surfaces. |
| WS-7 Integrations & research | `clawbench`, `acpx`, `crawlkit`, `crabpot`, `plugin-inspector`, `kitchen-sink`, `clawhub` | Keep deferred unless feeding CRIT, but use it to validate WS-1/WS-2/WS-5 release and benchmark gates. |

## Avoid / Cautions

- Do not copy OpenClaw's weaker trust assumptions. Several tools are trusted-team or public-repo oriented; CE's governed SDLC target needs hostile containment, private-repo tenancy, identity isolation, and explicit secret custody.
- Do not infer that OpenClaw has solved the whole merge queue. The pieces exist, but CE still needs a first-class merger-agent/merge-queue design.
- Do not copy the language stack. The transferable assets are state machines, ledgers, schemas, gates, and cockpit patterns; CE can keep Python.
- Do not let WS-7 sprawl. Only pull benchmarks, ACP, compatibility, and registry work into v3.5 when they harden WS-1, WS-2, WS-3, WS-5, or WS-6.

## Residual Unknowns

- Live production behavior was not verified for any repo.
- CI status, deployed secrets, GitHub App scopes, Cloudflare deployments, Apple notarization credentials, npm package contents, and real cache hit rates were not verified.
- Most repos were not tested locally; many would require external services, Go/Node/Python toolchains, GitHub auth, or OpenClaw-specific runtime.
- Security claims are static-source confidence only, not an adversarial audit.
