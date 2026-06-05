# Creator Engine v3 — Roadmap

Durable, in-repo roadmap for the Creator Engine **v3** evolution. This is the
shareable source for *where we are* and *what's next* — kept derivable from
`git log --oneline main` rather than from any one person's notes. Update the
status table whenever a gate's PR merges (see the maintenance note at the end).

## Orientation

CE v3 is a self-run, agent-native SDLC platform for solo / small teams, built by
**evolving this repository in place** (monorepo-first), not by greenfielding a
new one. The design is organised around three planes:

- **Plane A — coordination / review / merge:** rented to a forge (GitHub) behind
  a thin adapter, so the team never hand-builds coordination.
- **Plane B — scope containment:** enforced by CI via the `path_manifest_fidelity`
  PR-diff gate (every PR's diff must equal its declared closed manifest).
- **Plane C — runtime safety:** a declarative runtime-policy plus a container +
  thin-policy enforcer (gVisor + a capability-separation egress proxy now;
  OpenShell a fast-follow behind the same adapter).

The orchestrator that drives a run is deliberately **thin glue** (resolve a
backend, gate on an approved plan, provision → run → collect → teardown, collect
evidence); the **enforcement** lives in the policy + container + forge config.

## Design source-of-truth

Curated, **fresh-clone-resolvable** copies of the load-bearing design live in
`docs/architecture/` (start with `docs/architecture/README.md`, then the spec).
These are curated/redacted for sharing; the **full-fidelity** originals live under
the gitignored `.hermes/research/v3-*-architect-*/` tree (instance-local — these
links resolve only in the authoring instance, not a fresh clone).

| Committed copy (fresh-clone) | Full-fidelity original (gitignored) | What it decides |
| --- | --- | --- |
| `docs/architecture/v3-spec.md` | `.hermes/research/v3-spec-architect-20260602T091332Z/` | **The spec** — thin-orchestrator / thick-enforcer, the D0–D6 deletion plan, and the G-i/ii/iii → G-1 → G-2 → G-3 MVP gate map |
| `docs/architecture/v3-secure-runtime.md` | `.hermes/research/v3-secure-runtime-architect-20260602T114327Z/` | Plane C — gVisor + proxy, OpenShell, the tamper-evident evidence spine |
| `docs/architecture/v3-product-brief.md` | `.hermes/research/v3-product-architecture-brief-20260602T091332Z/` | The product brief that framed the above |
| _(not committed)_ | `.hermes/research/v3-evolve-vs-greenfield-architect-20260602T070354Z/` | Evolve this repo (don't greenfield) — the EVOLVE-dominant hybrid decision (its conclusion is captured in the brief §4 + the spec) |

Note: `specs/001-v0-1-governance-substrate/` is the **superseded v2 governance
substrate** — historical context, not the v3 roadmap.

## The MVP gate map

```
Kickoff   G-i  author-time advisory hook      G-ii  path_manifest_fidelity PR-diff gate
Plane A   G-iii GitHub-native coordination (configure_repo / install_required_checks / CODEOWNERS)
Plane C   G-1  runtime safety
            G-1.0 runtime-policy substrate      G-1.1 runner-backend adapter
            G-1.2 gVisor + proxy backend        G-1.3a hash-chained evidence spine
            G-1.3b classifier + audit overlay
G-2       thin orchestrator + ratification gate
            G-2.0 orchestrator + approved-plan gate    G-2.1 forge-native approval + no-self-approval
            G-2.2 mint_scoped_token (JIT least-privilege)   G-2.3 OpenShell backend (research-gated, deferred)
G-3       first working v3 — one real Dev-mode gate end-to-end
            G-3.0 forge-native open_change() + ChangeRef       G-3.1 orchestrator wiring (run_plan -> open_change)
            G-3.2 read-only change-status (review/checks/conflicts)   G-3.3 forge.merge() (review + checks + up-to-date)
            G-3.4 credential value-injection seam             G-3.5 evidence persistence sink
            G-3.6 preflight + offline end-to-end dry-run      G-3.7 live spike (first working v3)
```

## Gate status

Merged commits are short SHAs on `main`; re-derive with `git log --oneline main`.

| Gate | Scope | PR | Commit | Status |
| --- | --- | --- | --- | --- |
| G-i / G-ii | author-time advisory hook + `path_manifest_fidelity` PR-diff gate | #112 | `19bbff4` | MERGED |
| G-iii | GitHub-native coordination (carrier convention + `configure_repo`/`install_required_checks` + CODEOWNERS) | #113 | `6ecf9a5` | MERGED |
| G-1.0 | plane-C runtime-policy substrate (`runtime-policy.schema` + `ce_runtime_policy`) | #114 | `813c2dd` | MERGED |
| G-1.1 | runner-backend adapter (`RunnerBackend` ABC + registry + local-noop) | #115 | `d4df4bd` | MERGED |
| G-1.2 | gVisor + proxy backend (policy → runsc/egress-proxy translation, availability-gated) | #116 | `ae2315b` | MERGED |
| G-1.3a | hash-chained evidence-spine substrate (`runtime_evidence_spine` + `ce_runtime_evidence`) | #117 | `6fe06cd` | MERGED |
| G-1.3b | classifier + backend-agnostic audit overlay (`classify` + `AuditOverlayBackend`) | #118 | `fe0b54c` | MERGED |
| G-2.0 | thin orchestrator `run_plan` + approved-plan ratification gate | #119 | `77656e5` | MERGED |
| G-2.1 | forge-native `plan_approved()` + no-self-approval guardrail | #120 | `269c8f2` | MERGED |
| G-2.2 | `mint_scoped_token` — JIT least-privilege, time-boxed per-run credential | #122 | `b3caa5e` | MERGED |
| G-2.3 | OpenShell backend behind the runner adapter | — | — | deferred (research-gated) |
| G-3.0 | forge-native `open_change()` + `ChangeRef` (change-lifecycle "PR opened" primitive) | #124 | `65ec35d` | MERGED |
| G-3.1 | orchestrator wiring (`run_plan` → `open_change`; thread the run change-set + JIT-token `gh_runner`) | #126 | `9067034` | MERGED |
| G-3.2 | read-only forge change-status (`review_state` / `checks_state` / `change_conflicts`) | #128 | `3bee641` | MERGED |
| G-3.3 | `forge.merge()` — squash, gated on review + checks + `mergeable=="MERGEABLE"` | #130 | `25db4e5` | MERGED |
| G-3.4 | credential value-injection seam (`authenticated_gh_runner` — `ScopedToken.value` → child `gh` env only) | #132 | `4d4a65b` | MERGED |
| G-3.5 | evidence persistence sink (`file_evidence_sink` — `CollectedEvidence` → durable `runtime-evidence-chain` file; persist iff `verify_chain`+schema-valid, else refuse) | #134 | `e63ae0b` | MERGED |
| G-3.6 | preflight + offline end-to-end dry-run (the integration harness) | — | — | planned |
| G-3.7 | live spike — first working v3 (Operator-ratified outside the CI-purity envelope) | — | — | planned |

**G-1 (plane C / runtime safety) and G-2 (thin orchestrator + ratification
gate) are COMPLETE** (G-2.0 / G-2.1 / G-2.2 merged; G-2.3 OpenShell deferred —
research-gated). **G-3 (first working v3) is underway** — G-3.0
(change-lifecycle `open_change()` primitive), G-3.1 (orchestrator wiring —
`run_plan` `change_opener` seam → `open_change()`), G-3.2 (read-only forge
change-status — `review_state` / `checks_state` / `change_conflicts`), G-3.3
(`forge.merge()` — squash, gated on review + checks + `mergeable=="MERGEABLE"`),
G-3.4 (credential value-injection seam — `authenticated_gh_runner`:
`ScopedToken.value` → the child `gh` env only), and G-3.5 (evidence persistence
sink — `file_evidence_sink`: `CollectedEvidence` → a durable
`runtime-evidence-chain` file) merged (#124, #126, #128, #130, #132, #134);
G-3.6 next.

## What's next

1. **G-3.6** — preflight + offline end-to-end dry-run (the integration harness:
   assembles the minter-token → `gh_runner`-factory bridge + `change_opener` +
   `merge()` + the G-3.5 `evidence_sink` into `run_plan` against local-noop + a
   fake `GhRunner`), then the **G-3.7** live spike ("first working v3",
   Operator-ratified outside the CI-purity envelope).
2. **G-2.3** — the OpenShell backend, deferred (research-gated; re-opens on the
   recorded trigger conditions).

The authoritative live "next action" is always the current batch-strict prompt
chain (below), not this summary.

## Where the v3 code lives

The v3 stack is the installable package `validators/creator_engine_validator/`:

| Path | Gate | Role |
| --- | --- | --- |
| `orchestrator.py` | G-2.0 / G-2.1 / G-3.1 | thin `run_plan()` + the `ApprovedPlan` / `PlanNotRatified` ratification gate + the injected `change_opener` seam → `open_change()` |
| `runner/backend.py` | G-1.1 / G-3.1 | `RunnerBackend` ABC + registry (`get_backend` / `available_backends`) + the value-free `RunChangeSet` pointer type |
| `runner/noop_backend.py` | G-1.1 | inert `local-noop` backend (used in CI) |
| `runner/gvisor_proxy_backend.py` | G-1.2 | hardened gVisor + egress-proxy backend |
| `runner/audit_overlay.py` | G-1.3b | `classify()` + `AuditOverlayBackend` decorator |
| `runtime_evidence_spine.py` | G-1.3a | hash-chained evidence spine (`append` / `verify_chain`) |
| `forge/github_repo_config.py` | G-iii | `configure_repo` / `install_required_checks` |
| `forge/plan_approval.py` | G-2.1 | forge-native `plan_approved()` (merged in #120) |
| `forge/scoped_token.py` | G-2.2 | `mint_scoped_token` / `revoke_scoped_token` (JIT per-run credential) |
| `forge/change.py` | G-3.0 | forge-native `open_change()` + `ChangeRef` (change-lifecycle "PR opened" primitive) |
| `forge/change_status.py` | G-3.2 | read-only `review_state` / `checks_state` / `change_conflicts` over a `ChangeRef` (GraphQL via `GhRunner`) |
| `forge/merge.py` | G-3.3 | gated squash-merge `merge()` → `MergeResult` (review + checks + `mergeable=="MERGEABLE"`; plan-by-default; head-pinned squash `PUT` via `GhRunner`) |
| `forge/credential_runner.py` | G-3.4 | `authenticated_gh_runner()` — a `ScopedToken` → an authenticated `GhRunner` (the live token value into the child `gh` env only; never argv / log / disk / the task container) |
| `evidence_sink.py` | G-3.5 | `file_evidence_sink()` — a `CollectedEvidence` (AuditOverlay hash-chain) → a durable `runtime-evidence-chain` file matching `runtime-evidence.schema.yaml` (persist iff `verify_chain`+schema-valid, else `EvidencePersistRefused`) |
| `schemas/*.yaml` + `docs/contracts/*.md` | various | declarative + prose contracts |

The package also retains earlier v2 machinery (lane/PCO/tmux runtime, etc.)
earmarked for the spec report's D0–D6 deletion plan; the table above is the v3
surface.

## How this is governed

Work lands through **batch strict-mode**: each step is composed as a
SHA-pinned, Operator-ratified prompt, then executed as
`compose → ratify → execute → review → merge`. `main` is protected (required PR +
CODEOWNERS review + `enforce_admins`), and the independent reviewer identity is
distinct from the author. The work-of-record for each gate is its directory under
`.hermes/research/v3-*-planning-*/` (planning + execution + review + merge prompts,
evidence, and completion reports).

## Maintaining this doc

When a gate's PR merges: add its merge commit short SHA to the status table and
flip Status to MERGED; add new sub-gates as they are planned. Keep every row
derivable from `git log --oneline main`. This doc is a reference table, not a
substitute for the per-gate prompt chain.
