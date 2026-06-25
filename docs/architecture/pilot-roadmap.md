# CE v3 — Roadmap to Pilot (full-stack-first)

*Curated, redacted design reference (provenance: 2026-06-06 design session). **DESIGNED / pilot-target** — re-ground at the implementing gate (G-4…G-7). Execution status lives in the project README's **Current Status** section.*

## Decision
The developer test group will pilot CE on a real greenfield OSS project and will **wait** for a pilot-ready build. So CE is built **full-stack-first**: the designed-but-unbuilt stack (agent-interaction contract · tokenomics gate · coordination layer) + the product surface are built **before** a pilot is exposed (not fastest-usable-pilot-first).

## Two milestones
- **v3.0 "MVP-complete"** — the governed-run engine proven live end-to-end **incl. merge** (open→review→merge). End of G-3.7b/G-3.8.
- **v3.1 "pilot-ready"** — a developer can *use* it: full stack, cost-safe, installable, drivable. End of G-7.

## Gate map (build order = bottom-up dependency)
```
[MVP — inner loop]
 G-3.7   live spike — first live PR-open loop (CI-pure slices + one out-of-envelope live drive)
[pilot arc — full-stack-first]
 G-3.7b  CI-pure: merge-driving seam + live-merge-identity seam + pr_merged run-outcome model
 G-3.8   out-of-envelope LIVE merge spike + the final G-3.7 roadmap flip      ► v3.0 MVP-complete
 G-3.9   version coexistence / separation — v1/v3/shared taxonomy + version_boundary guard; v1 RETAINED (no deletion)
 G-4     Agent-interaction contract (per-run substrate)
 G-5     Tokenomics gate (spend envelope)                                     (closes the #1 pilot blocker)
 G-6     Coordination layer (outer loop: Scope + backlog)
 G-7     Product surface: v3 CLI (distinct entry alongside `ce`; v1 retained) + 2-mode install  ► v3.1 pilot-ready
```

## Cluster detail (sub-gates + acceptance)

### G-3.7b / G-3.8 — gated live merge → v3.0
- **G-3.7b (CI-pure):** the merge-driving seam + a distinct live-merge-identity seam (a credential seam — never the per-run token) + the `pr_merged` run-outcome (extend the outcomes enum + the evidence schema + spine constants — currently absent by design). RED→GREEN against fakes; no live merge here.
- **G-3.8 (out-of-envelope):** the one live drive that opens → independent-review → merges a real PR end-to-end using the G-3.7b seams; + the final G-3.7 roadmap flip.
- **Acceptance:** merge mechanics + `pr_merged` land CI-pure in G-3.7b; the live open→review→merge proven once in G-3.8 (merge identity ≠ run token). **= v3.0.**

### G-3.9 — version coexistence / separation
- **Shipped (PR #152).** Replaces the prior "D1–D6 deletion" with **version coexistence**: declare the v1/v3/shared taxonomy (`_versions.py`) and guard the **v1⊥v3** boundary with the `version_boundary` check — HARD runtime⊥runtime + a baselined `shared→version` allowlist ratchet + integrity guards. The surface the deletion series targeted (reviewer-venue seam · PCO ledger/leases/panes · hook · op-mode carriers · lane/launch/tmux) is **classified `v1` and retained**, not removed.
- **Launcher guard is moot:** v1 is retained, so there is no D2 deletion to condition on a replacement — the build never cuts the substrate it runs on.
- The worker-runtime container-isolation primitives are **retained** (a future enforcer may *reuse* them; nothing is blind-deleted).
- **Acceptance:** suite green; **v1 deleted = ∅**; the boundary holds (0 v1↔v3 edges) and is now machine-enforced. Any future removal is orphaned-only (proven dead to both versions).

### G-4 — Agent-interaction contract (per-run substrate)
- A typed `AgentActionEvent` (op × mutation_class × fidelity) + a `runtime_agent_action` hash-chained record (builds on the existing `mutation_class` taxonomy + the evidence spine).
- A `decide()` control-point (deterministic, in-process, zero-token; **observe-all, gate-mutations-selectively**) + runtime-policy action-class allowlists + a gate-mode ladder (builds on the existing `classify()`).
- The first transport emitter = Claude-Code hooks / stream-json (the OAuth/subscription-first-class tier). *(ACP/Tier-A deferred — see backlog.)* **As-built note (post-G-3.9):** the `hook_check` runtime is **v1** and `runner.*` is **v3**, so the Tier-B adapter (`runner.cc_hook_adapter`) reuses the **shared** `checks.mutation_class` taxonomy, NOT the v1 `hook_check` runtime — a direct import would break `version_boundary`. Heuristic parity with `hook_check` is a ratified follow-on (shared extraction or scoped re-derivation). The live hook/stream-json tap is a deferred event source; G-4 lands the pure derivation seam.
- Borrowed hardening: late-credential-minting + snapshot-hash recheck-before-mutate on secret/vcs ops. *(Deferred to a named G-4 follow-on — not in the CI-pure substrate.)*
- **Acceptance:** every action recorded fidelity-tagged; mutating/high-blast actions gated preventively before they run; reads default allow+observe. This is the substrate G-5 + G-6 plug into.

### G-5 — Tokenomics gate (spend envelope)
- Spend as a deny-by-default blast-radius axis in runtime-policy (spend cap / max-concurrent-runs / per-fleet budget).
- A deny-by-default admission gate + nested global→fleet→run envelopes.
- A post-action circuit-breaker that **reuses the G-4 action-gate's escalation + evidence machinery** (the reason G-5 follows G-4); the appetite→cap join.
- A two-regime metric: fleet = API-$; subscription = single-seat %-meter (not fleet-poolable). *(Folds in the harness-overhead benchmark — ground the gate cost empirically.)*
- **Acceptance:** a run cannot exceed its envelope; breaches deny/escalate with evidence. **Cost-runaway protection exists** (the #1 pilot blocker closed).

### G-6 — Coordination layer (outer loop)
- The **Scope** object (intent/spec · acceptance-criteria · appetite · mutation_class · ratification · execution · state-as-projection) + a backlog + a task-source seam (builds on definition-of-ready + the plan-approval gate + ratified-gate-as-backlog-item).
- DoR-wiring (no dispatch until intent+AC+appetite+class valid) + constrained-BDFL ratification ("betting table") + the appetite→tokenomics-cap join.
- A crosswalk extension (PRD→epic→story→task→PR optional traceability over the existing crosswalk register).
- A finding-schema + discard-on-drift gate + the dispatch path: a ratified Scope → one isolated run governed by G-4/G-5.
- *(Durable Skill axis deferred — see backlog.)*
- **Acceptance:** file a Scope → DoR-gated → ratified → dispatched as a governed run → PR; traceable. The idea→governed-delivery spine (Scope-only).

### G-7 — Product surface → v3.1
- **7.0** the v3 work-driving CLI (file/ratify/drive/status) + the v3 seat-launch entry point — a **distinct** entry alongside the retained v1 launcher (added, not a replacement).
- **7.1** v3 install/provisioning — **two operator-typeless modes**: a **one-liner** (mirroring the OpenClaw `curl … | bash` → `onboard` installer pattern); and an **agent-native** mode where the operator points their agent at the CE site, which fetches a **signed install spec, verifies it against a pinned CE public key before executing**, and assists the interactive GitHub-App step. Both provision the runtime backend + the GitHub App + PEM-on-tmpfs custody + the policy bundle. **Dependency resolution = detect-don't-assume, fix-with-permission** (check git / Python / runsc / proxy / uv; offer to install missing ones gated on the operator's sudo approval; batched ask; graceful decline; idempotent; trusted/pinned sources) — NOT fail-on-missing. **Human contract:** the operator types nothing; approves only **sudo** (privileged installs) + the **GitHub-App authorization click**. **Hard constraint:** the installer is served + signed (hash/signature published); the agent-native spec MUST be signed + verified-before-execute. **Product-story symmetry:** CE's own governance model applied to its own install — the human ratifies the privileged step, the rest runs under a verifiable spec ("the grader lives outside the agent," at install time). *(Distinct from a runtime guard: the installer FIXES with permission; the runtime `doctor` guard stays fail-closed.)*
- **7.2** pilot onboarding runbook + greenfield-OSS-repo setup.
- **7.3** — n/a: there is **no D2 teardown**. v1's lane/launch/tmux is retained (classified `v1`, guarded by `version_boundary`); 7.0 **adds** the v3 launcher alongside it.
- **Acceptance:** a developer installs CE, provisions repo+App, files work, gets governed cost-safe PRs+merges end-to-end; the v1 launcher is **retained**, with the v3 entry point added alongside it. **= v3.1 pilot-ready.**

## Adopted assumptions (re-confirm at the gate)
- Version coexistence (G-3.9): v1 retained + the v1⊥v3 boundary declared & guarded by `version_boundary`; **no deletion** (the prior D1–D6 deletion plan is superseded; any cleanup is orphaned-only, proven dead to both versions).
- Deferred to post-first-pilot: the cockpit UI · the ACP/Tier-A transport (pilot on CC-hooks/subprocess) · the durable Skill axis (pilot Scope-only).

## Build-order rationale
Contract (G-4) is the per-run substrate the spend gate (G-5, which reuses the action-gate machinery) and coordination (G-6, which dispatches a ratified Scope into one G-4/G-5-governed run) both sit on; version coexistence (G-3.9) precedes the stack so the v1⊥v3 boundary is declared and machine-guarded before new v3 code is built (v1 retained throughout — the build never cuts the substrate it runs on); the product surface (G-7) wraps a finished stack + **adds** the v3 launcher as a distinct entry alongside the retained v1 one. This is the only ordering with no designed-in rework and no self-cut.

## Deferred post-first-pilot backlog
Cockpit UI · ACP/Tier-A transport · durable Skill axis · MCP-server install tool (agent-native-install upgrade) · OpenShell backend · CEO-mode/BMAD.

## Evidence / caveats
The stack design is grounded + captured (the contract, tokenomics, coordination-hierarchy, and substrate decisions). The methodology evidence is thin and treated honestly — the one rigorous RCT (METR, Jul-2025) found experienced devs ~19% **slower** with AI on then-current tooling while believing they were faster; DORA-2025 shows throughput gains conditioned on mature engineering practice plus a persistent stability cost; Martin Fowler (Feb 2026) called it "too early" for a new methodology manifesto. This is **informed design, not a proven methodology**; each gate re-grounds against then-current `main` before composing.

## Companions
[`pilot-deployment-transport.md`](./pilot-deployment-transport.md) (transport selection + deployment invariants) · [`pilot-uiux-model.md`](./pilot-uiux-model.md) (the pilot UI/UX) · [`v3-spec.md`](./v3-spec.md), [`v3-secure-runtime.md`](./v3-secure-runtime.md), [`v3-product-brief.md`](./v3-product-brief.md) (the MVP design) · the project README's **Current Status** section (execution status).
