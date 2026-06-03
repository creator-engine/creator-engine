<!-- Curated / redacted copy of the CE v3 Product & Architecture Brief. Instance-specific
provenance (transient base-commit SHA, internal handoff/report SHAs, gitignored research-
directory path pointers, machine/account identifiers, legacy role aliases) has been removed;
the full unredacted source lives in the corresponding `.hermes/research/v3-product-architecture-brief-*/`
artifact (gitignored — full-fidelity, not in a fresh clone). The decisions and design
substance are preserved verbatim. -->

# Creator Engine v3 — Product & Architecture Brief (consolidated decisions)

- **Status:** decisions ratified-in-discussion between the Operator and the orchestrating CE Controller, 2026-06-02, following the read-only Architect's evolve-vs-greenfield report.
- **Purpose:** a single shareable artifact for the Operator, the build agents, and the eventual implementation-architect handoff. This records **decisions already made**; all *downstream* research/design must be **current-date-grounded actual research, not pre-training** (see §11).
- **Inputs:** the read-only evolve-vs-greenfield Architect report and the architecture-pivot (GitHub-native + container model) migration plan (both under the gitignored v3 research tree; see §12).

---

## 1. Product identity (DECIDED)
**CE v3 is a self-run, self-configuring, agent-native SDLC platform.** Explicitly:
- **NOT a toolkit-you-wire** (the target market has no devops to do the wiring).
- **NOT a SaaS-we-host** (target is trust-sensitive about a third party holding their code; it would load us with multi-tenant ops/security burden; and a multi-tenant control plane reintroduces the shared-mutable-state that caused the v2 deadlock).
- **IS an integrated, opinionated product the team installs and runs against their own GitHub, on runners they already pay GitHub for**, whose entire value proposition is that **CE owns the integration complexity so the user never touches it.**

Mental model of the first-run UX: point your agent (Claude Code / Codex / OpenClaw) at the CE repo/website, or click a GitHub-App "Install" → CE configures branch protection + CODEOWNERS, drops the required CI checks into the repo, provisions the container image + Actions workflow + egress policy, mints/rotates scoped tokens — and from then on the dev **ratifies a plan and a governed PR appears.** Semi-automation force-multiplier: one human approving, multiple governed agents executing, **no wiring.**

## 2. Target market + value prop (DECIDED)
Solo devs → small teams (6–10) with **no dedicated devops/IT** (incl., later, vibe-coders / AI-builders — see §5 modes). They cannot and will not invest in connecting tooling to SDLC machinery. CE's promise: **the path of least resistance to (semi-)automated SDLC.** A force multiplier that scales across the team.

## 3. The A/B/C scope model (DECIDED)
The v2 error was one bespoke local mechanism fusing coordination + scope + runtime-authority in shared mutable state. v3 separates the three concerns and **narrows CE's ownership**:
- **A — coordination / conflict-prevention / independent review / merge → RENT from a forge.** GitHub first, **behind a thin forge-adapter** so CE is not *defined* by one forge. Push = claim; non-fast-forward reject = conflict; required non-author review + dismiss-stale + CODEOWNERS = independent review; squash-only + required checks + require-up-to-date = merge discipline; a per-Controller **scoped GitHub-App installation token** = authority as a *credential fact*, not a hook fact (push to its branch, no merge).
- **B — scope containment (diff == ratified files) → required CI check on the PR diff.** Promote `path_manifest_fidelity` (the only enforcement that ever actually held) from running on `examples/` to gating the real PR diff. Post-hoc at the PR boundary.
- **C — runtime safety of an autonomous agent → container-per-Controller + a thin in-container policy layer + the human ratification gate.** Egress allowlist (primary anti-exfiltration control); scoped/time-boxed credentials; local command/secret policy (reusing the `hook_check.py` classifiers `is_secret_path` / `classify_mechanics`); pre-commit secret scan; per-container side-effect log.

**OD-04 ("GitHub is transport+mirror only; CE is authoritative") is to be formally SUPERSEDED** by a v3 decision that rents coordination. We are entitled to — this is a founding-architecture pivot, not a version bump. **Preserve OD-04's spirit as a design property:** keep coordination behind a `forge` adapter, and keep the runner abstraction loose (GitHub Actions = the *first* runner backend, not the architecture; preserve a self-hosted-runner / plain-container escape hatch).

## 4. Repo topology (DECIDED)
**Monorepo-first — evolve THIS repo as a hard in-place reset.** The platform/orchestrator is the new center of gravity (greenfield on top). Demote the salvageable core to **two clean internal, separately-publishable packages**:
1. the **CI-checks library** (installed into the *user's* repo / task container) and
2. the **in-container enforcer** (shipped in the container image; minimal-dependency, auditable, sign-able).

**Extract either to its own repo ONLY on a pre-committed trigger:** the enforcer wants a different/compiled stack or an independent security-audit/release cadence; or release-cadence genuinely diverges.

**Rationale (decided on overhead, not sentiment — history/"work already done" explicitly discounted):**
- For the dead v2 machinery, "delete it" (evolve) ≈ "don't port it" (greenfield) — those costs cancel. Both routes equally pay the doc/spec rewrite. The only *non-cancelling* differential is greenfield's re-establishment-from-zero of CI/packaging/test-harness/wheelhouse boilerplate that buys **no** architectural benefit, while evolve keeps the two load-bearing assets (`path_manifest_fidelity` + the classifiers) wired and proven.
- **Asymmetry of regret:** mono-then-split = a bounded one-time extraction; split-then-merge = a continuous coordination tax (bad for a small team-of-agents). Mono-first preserves the option at lower cost.
- The two empirical unknowns that could flip this (how *thick* the orchestrator really is; whether the enforcer *diverges* enough to warrant its own repo) are answered by the out-of-box-UX spike (§9), not from the armchair. NOTE: the market input already established the orchestrator is **thick** (it must absorb all plumbing) — so we are genuinely greenfielding a real product on an evolved core; the package is demoted to a consumed library. *(The v3-spec Architect report subsequently pushes back on this "thick" assumption — see that report's §5.3/§10.)*

## 5. Two product principles (DECIDED)
**P1 — Agent-native, IaC-style self-install.** CE's own install/deploy is agent-native: the user's agent reads an **agent-agnostic, declarative, versioned install contract** (desired-state + a per-step required-inputs schema + verification/health checks + idempotency; plus a thin imperative runbook). The agent runs a **preflight requirements check before starting**; if inputs are missing it alerts the human, who chooses **(A)** proceed and provide info interactively, or **(B)** pre-stage all inputs so the rest applies fully unattended end-to-end (Terraform-like).
- **Security guardrail (LOCKED):** installing a *security* product is itself security-sensitive (the install agent stands up GitHub-App keys, branch protection, egress policy — the very guardrails). So the install **dogfoods CE's ratify-then-execute**: produce a **plan the human ratifies before apply**; run **least-privilege**; the **human creates the GitHub-App private key** in a guided step (the agent never mints root credentials).
- The README/website is a **dual-purpose product surface** (human-readable AND agent-executable). The install contract is **validated by a CE check** (dogfood the validator on our own onboarding).

**P2 — Two lifecycle modes; v3 MVP is Dev mode only.**
- **Dev mode (v3 MVP):** experienced dev with an existing PRD/roadmap + set-up GitHub → CE integrates at the **governed-execution layer.** Crisp inputs. This is the entire v3 MVP.
- **CEO mode (DEFERRED to v3.5 / v4):** adds the upstream Agile inception (concept → PRD → roadmap) for non-devs; those generated artifacts *become* the ratifiable plan artifacts. **Explore the BMAD Method (open-source) when we reach this — research it current, don't assume.** NOT in the v3 MVP.

## 6. Three orthogonal mode-axes (keep independent; don't conflate)
1. **Lifecycle ownership:** CEO vs Dev (how far upstream CE starts). *v3 = Dev only.*
2. **Per-action autonomy:** the v2 operating-mode substrate `strict` / `auto` / `transcendence` + autonomy classes + Operator-only privileged floor. **Revalidated as genuine, keep-worthy product.**
3. **Install mode:** interactive (P1-A) vs unattended-IaC (P1-B).

## 7. What survives / what's cut (per the Architect report §7.4 — validate at deletion time)
**KEEP (becomes v3 substrate):** `path_manifest_fidelity` (+ protocol) → promote to gate the PR diff; the secret/dangerous-mechanic **classifiers** in `hook_check.py` → become the in-container local policy; pure-data product schemas (operating-mode policy, connector authority, completion-report/evidence schemas, `mutation_class`, `no_limitless_strings`, sidecar/duplicate-spec/definition-of-ready); the pytest harness + CI workflow + validator plumbing (`loader`/`schema`/`reporting`/`cli`/`environment_guard`). The validator/schema core is **reaffirmed and expanded** — v3 uses it to validate the install contract, PRD/plan artifacts, and gate manifests (all machine-native).
**CUT (v2-only coordination/posture/lane/reviewer machinery):** Active-Work Ledger + `active_work_ledger_conflicts`; `pco_allocator` + `pco-allocate/release`; worktree-lease; `pane_registry` + `evaluate_posture`; `side_effect_ledger` (audit role → GitHub events/Action logs); `controller_key`; `lane_runtime` + `ce lane launch` + `tmux_adapter` + `transcript_archive`; `reviewer_authority_envelope` + its hook wiring → GitHub branch protection + a reviewer identity; `harness_seat_contract` + `hook_pack_confirm` + `.claude/hooks/*` + the launch-spec posture machinery; the posture+manifest enforcement path in `hook_check.py` (keep the classifiers, drop posture/manifest resolution).
**RECONSIDER (route-independent):** PCL/CE-event *record schemas* (audit/event role may survive; coordination role is rented); operating-mode runtime *carriers* (cut) vs *policy* (keep). The dependency graph is one-way (`hook_check.py` imports the durable checks, not vice-versa), so deletion is a localized excision.

## 8. v3 MVP definition ("first working v3")
One Dev-mode gate authored by a governed Controller **inside a container** with a scoped token + egress allowlist + the in-container policy, **opening a PR** that GitHub branch-protection + required CI (full pytest + diff-gated `path_manifest_fidelity`) + required **non-author** review then merges — with the **ratification gate** (approved GitHub issue / plan-PR declaring the manifest) blocking the container from starting until approval exists.

## 9. Kickoff (route-independent; unblocks the fleet; first slices of the platform)
1. **Step (iii):** make author-time manifest enforcement **advisory/report-only** in `hook_check.py` (keep the secret + dangerous-mechanic **denies** — those are the in-container policy seed). Unblocks every governed Controller; first real v2-machinery retirement; not throwaway.
2. **Promote `path_manifest_fidelity` to gate the real PR diff** as a required CI check. Concern B made real for the first time; doubles as the empirical test of the brownfield thesis.
3. **GitHub-native coordination config:** branch protection (required non-author review + dismiss-stale + required checks + squash-only + require-up-to-date), CODEOWNERS, a distinct reviewer identity.

Build (1)+(2) as **reusable functions** the orchestrator will later call (`configure_repo()` / `install_required_checks()`), NOT throwaway scripts.

**Out-of-box-UX spike** (de-risks topology + proves the product motion): "one command configures a throwaway GitHub repo + drops the checks + runs one governed container task that opens a PR." Instrumented to measure the two unknowns — (a) authored-orchestrator LOC vs rented Actions/GitHub config, (b) does the in-container enforcer want a different stack/dependency-profile — with **pre-committed extraction-trigger thresholds.** (This spike is to be *specified by the v3-spec Architect* with current research — see §10/§11 — not hand-specced from priors.)

## 10. Open questions for the v3-spec Architect to resolve (with CURRENT research)
- The `forge` adapter interface (operations + the GitHub-first implementation) and exactly which GitHub features (require-non-author-review, dismiss-stale, merge queue, App installation tokens) are real/available now.
- The runner backend decision (GitHub Actions vs self-hosted runner vs plain container) and its ergonomics constraints for long-running interactive agents.
- The container + in-container **enforcer** design (egress-allowlist mechanism, secret scanning, command/secret policy from the classifiers) and the **enforcer-extraction trigger thresholds**.
- The **agent-native install-contract format** (agent-agnostic, declarative + runbook; the required-inputs schema; the ratify-before-apply plan; least-privilege; the human-creates-App-key step).
- The orchestrator design + how thick it really is (provision Action, mint tokens, gate on approval, collect results); the ratification-gate mechanism.
- The deletion plan/order for the v2 machinery and which CI checks survive.
- The detailed out-of-box-UX **spike spec** (what to build, what to measure, the trigger thresholds).

## 11. Working principles (DECIDED — apply to all downstream work)
- **Current-date research, not pre-training.** Every research/design/planning task checks today's date and grounds findings in actual current research (web + live repo/tools), citing sources and flagging thin evidence. Training-derived "facts" about external tools are hypotheses to verify.
- **Ultracode by per-task approval only** (token-heavy). Approved for the v3-spec Architect. Confirm the exact invocation before launch.

## 12. Pointers
- Evolve-vs-greenfield Architect report and the GitHub-native + container-model migration plan live under the gitignored v3 research tree (`.hermes/research/v3-evolve-vs-greenfield-architect-*/` and the architecture-pivot directory). They are the full-fidelity provenance for the decisions recorded here.
- Cadence: batch strict-mode (Operator is sole ratifier; SHA-pinned prompts; closed manifests; distinct independent review; head-pinned squash merge + closeout).
