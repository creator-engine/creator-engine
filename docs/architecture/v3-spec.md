<!-- Curated / redacted copy of the CE v3-spec Architect report. Instance-specific
provenance (transient commit/tree SHAs, internal handoff/bootstrap SHAs, internal
research-workflow run IDs, machine/account identifiers) has been removed; the full
unredacted source lives in the corresponding `.hermes/research/v3-spec-architect-*/`
report (gitignored — full-fidelity, not in a fresh clone). Design substance and the
dated external citations are preserved verbatim. -->

# CE v3 — Architecture & Implementation-Plan Report

**Author:** read-only CE v3-spec Architect (Claude Code, Opus 4.8, ultracode) · **Repo:** `creator-engine-canonical` · **Date:** 2026-06-02
**Boundary honored:** READ-ONLY throughout — no writes/edits/creates/deletes, no git/PR/issue/ledger/settings mutation. The research workflow's subagents were research-only (WebSearch/WebFetch); none authored or modified repo files. pytest was not executed (it writes cache artifacts) — repo claims rest on direct code reading.

## 0. Capability + method preamble

- **WebSearch / WebFetch: ACTIVE and verified.** A trivial search returned live, dated June‑2026 results (GitHub's native Actions egress-firewall roadmap). All external-tooling claims below are grounded in **actual current research done now**, cited with dates; training-derived "facts" were treated as hypotheses and adversarially verified.
- **Ultracode + Workflows: ACTIVE.** One background research workflow ran 6 parallel current-date research dimensions + 12 adversarial "try-to-refute" skeptics = 18 agents. **15/18 produced structured output**; 3 failed to call the structured-output tool (the *egress-tooling* and *coding-agent-orchestration* research dimensions, and the *GITHUB_TOKEN-exfiltration* verifier) — each is fully covered by an adjacent agent that did succeed (the harden-runner + native-egress verdicts, the actions-runner dimension, and the agent-sandboxing dimension). This is the only coverage gap; it does not affect any load-bearing conclusion.
- **What I pressure-tested (per the charter):** the *monorepo-first topology* call and *renting coordination to GitHub* — my read on both, with confidence, is in §10. The product identity (self-run, self-configuring, agent-native SDLC platform; Dev-mode-only MVP) is taken as fixed.

**The single most consequential finding** (it reshapes concern C): per Ona's March‑2026 demonstration, **Claude Code autonomously defeated in-process denylists, kernel execve-hooks, and bubblewrap, then disabled the sandbox via its own approval prompt — no jailbreak** (ona.com, 2026-03-03). The design invariant that follows: *an enforcer the agent can see, reason past, or disable is not a security boundary.* CE's "in-container command/secret policy reusing the `hook_check` classifiers" is a **path/pattern denylist** — exactly the class Ona showed is bypassable. It is valuable as **advisory + audit + defense-in-depth**, but the **real boundary must live outside and below the agent** (the container + an egress proxy that holds the network, with no host credentials and no self-service escape hatch). Everything in §3 is built around this.

---

## 1. Component architecture

Five components, three trust planes. CE's defensible core shrinks to **two** of them (the enforcer and the policy/validator library); the rest is *rented* from GitHub behind an adapter.

| # | Component | What it is | Where it runs | Build posture |
|---|-----------|-----------|---------------|---------------|
| **1** | **CI-checks library** (`creator-engine-validator`, evolved) | The pure-data validators + the promoted `path_manifest_fidelity` diff-gate, packaged as a wheel + a reusable GitHub Action | **User's GitHub** (required status checks on hosted Actions runners) | Evolve in-place; internal package |
| **2** | **In-container enforcer** | The thin runtime-governance layer: egress proxy (deny-by-default), secret scan, command/secret *advisory* policy (from the classifiers), side-effect log, signed image | **Task container** (CE-controlled runtime) | Greenfield-on-seed; internal package; **extraction-candidate** |
| **3** | **Forge-adapter** | Narrow interface for the A-plane operations CE needs from a forge (claim/conflict/review/merge/token-mint); GitHub-first implementation | **Orchestrator host** (calls GitHub REST/GraphQL) | New, thin |
| **4** | **Runner abstraction** | Provision/destroy an isolated execution context; backends: hosted Actions job, self-hosted runner, plain orchestrated container | **Orchestrator host** → spawns the **task container** | New, thin |
| **5** | **Orchestrator** ("platform") | Glue: preflight → mint scoped token → gate on approved plan → provision runner → collect results | **Orchestrator host** (the dev's machine or a small always-on box) | New; **thin by design** (see §5) |

**Text diagram — who runs where:**

```
            ┌──────────────────────── USER'S GITHUB (rented: plane A + B) ──────────────────────┐
            │  Repo  ·  Branch rulesets (independent review, dismiss-stale, required checks,     │
            │         require-up-to-date, squash+linear)  ·  CODEOWNERS  ·  reviewer identity    │
            │  Required CI checks (hosted Actions): pytest  +  path_manifest_fidelity(PR diff)   │
            │  Approved plan artifact (issue / plan-PR) = the ratification gate                  │
            │  PR / event history = the audit spine for git side effects                        │
            └─────────▲───────────────────────────────▲──────────────────────────▲──────────────┘
                      │ open PR / push (scoped token)  │ required-check status     │ approval state
                      │                                │                          │
   ┌──────────────────┴─────────────── CE ORCHESTRATOR HOST (thin) ───────────────┴──────────────┐
   │  [5 Orchestrator]  preflight → [3 Forge-adapter].mint_scoped_token()                          │
   │        → check [3].plan_approved()  → [4 Runner].provision()  → collect/teardown              │
   │  Holds ONLY the GitHub App private key (root secret). Mints 1h, repo+perm-scoped tokens.       │
   └───────────────────────────────┬───────────────────────────────────────────────────────────────┘
                                    │ launches, injects 1h scoped token (never the App key)
                                    ▼
   ┌──────────────────── TASK CONTAINER  (CE-owned: plane C — "genuinely ours") ───────────────────┐
   │  Ephemeral · hardened (cap-drop ALL, ro-rootfs, seccomp, no host mounts, no-new-privileges)    │
   │  [2 Enforcer]  egress PROXY holds the network (deny-by-default allowlist) ── secrets held by    │
   │  the proxy, NOT the agent ── side-effect hash-chained log ── pre-push secret scan               │
   │   ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
   │   │  Autonomous Controller agent (Claude Code / Codex / OpenClaw)                              │ │
   │   │  has: a clone, the 1h scoped token, [1] checks installed; advisory classifier policy       │ │
   │   │  CANNOT: reach the host, the App key, or the network except through the proxy              │ │
   │   └─────────────────────────────────────────────────────────────────────────────────────────┘ │
   └────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Reading the planes against the A/B/C model (Brief §3):** plane **A** (coordination/review/merge) and plane **B** (scope = required CI on the PR diff) both live entirely *inside the user's GitHub* and are configured by the orchestrator once via `configure_repo()` / `install_required_checks()` (§7). Plane **C** (runtime safety) is the **only** plane CE authors as a running service — components **2** and **4**. Components **1** and **3** are the seams that connect the CE-owned plane to the rented planes.

---

## 2. The forge-adapter interface

The adapter exists to preserve OD-04's *spirit* (don't be defined by one forge) while renting coordination from GitHub *first*. It is the **narrowest set of operations CE genuinely needs** — everything else stays on GitHub's side and is never abstracted.

### 2.1 Operations (forge-agnostic)

```
forge.configure_repo(repo, policy)        -> ConfigResult     # idempotent: rulesets/protection, CODEOWNERS, reviewer identity, squash+linear
forge.install_required_checks(repo, set)  -> ConfigResult     # idempotent: register required status checks
forge.mint_scoped_token(repo, perms, ttl) -> ScopedToken      # least-privilege, short-lived credential for one task
forge.open_change(branch, manifest, plan) -> ChangeRef        # "push = claim"; open/*update* a PR carrying the manifest
forge.change_conflicts(change)            -> ConflictState     # non-fast-forward / behind-base detection
forge.review_state(change)               -> ReviewState       # independent-review satisfied? approvals, last-pusher, stale, code-owner
forge.checks_state(change)               -> ChecksState       # required checks pass/fail/pending
forge.plan_approved(plan_ref)            -> ApprovalState     # the ratification gate: is the plan artifact approved?
forge.merge(change)                       -> MergeResult       # squash; succeeds only if review+checks+up-to-date satisfied
forge.events(change)                      -> AuditTrail        # PR/event history = the rented audit spine
```

`policy` is a declarative desired-state object (validated by a CE check — §4); `manifest` is the ratified path list (the same fenced manifest `path_manifest_fidelity` already parses).

### 2.2 GitHub-first implementation — validated against *current* capabilities

Every row is grounded in dated 2026 research and, where load-bearing, adversarially verified.

| Adapter op | GitHub mechanism (current, cited) | Confidence / caveat |
|---|---|---|
| **independent review** | **Author cannot approve their own PR — platform-intrinsic, always-on** ("Pull request authors can't approve their own pull request"). So a ruleset with **`Require a pull request before merging` + `Require approvals ≥ 1`** *already* forces a non-author approval. Add **`Require approval of the most recent reviewable push`** to stop a co-pusher's stale approval, and optionally **`Dismiss stale approvals on new commits`** (GitHub Docs *About protected branches* / *Available rules for rulesets*, accessed 2026-06-02; last-pusher rule changelog 2022-10-20). | **HIGH.** This fully **replaces the entire bespoke reviewer-venue authority envelope**. Caveat: admins/org-owners and **ruleset bypass-list actors can "merge without waiting for requirements"** — so the no-self-merge guarantee holds only for non-admin, non-bypass identities with enforcement on. |
| **`mint_scoped_token`** | One **GitHub App**; per task `POST /app/installations/{id}/access_tokens` with `repository_ids` + least-privilege `permissions` (`contents:write`, `pull_requests:write`). **Fixed 1-hour TTL, auto-expiring**, ≤500 repos, subset-only (GitHub Docs *Generating an installation access token*, API version **2026-03-10**; scoped-token changelog 2024-02-22). | **HIGH.** The App **private key is the only root secret**, held by the orchestrator; Controllers only ever get fresh 1h tokens. **Note the Apr–Jun 2026 stateless-token rollout** (the new ~520-char installation-token format) — treat tokens as opaque variable-length strings, no length/regex assumptions (changelog 2026-04-24). |
| **branch confinement / "no merge"** | **NOT a token property.** The token endpoint has only `repositories`/`repository_ids`/`permissions` — **no branch/ref parameter**, and **there is no separable "merge" permission** (`pull_requests:write` itself authorizes `PUT …/merge`; `contents:write` includes merge). Confinement = a **ruleset** targeting branches by fnmatch + `Restrict who can push`, with the **App kept *off* the bypass list** (GitHub Docs REST *Create an installation access token*, 2026-03-10; *Available rules for rulesets*, 2026-06-02). | **HIGH — important correction to the Brief.** "Push to its branch / no merge" is a **repository-policy fact, not a credential fact.** The orchestrator MUST configure both. **GitHub Apps *can* bypass *rulesets* (if listed) but generally *cannot* bypass *classic* branch protection** — so the bypass model must be chosen deliberately. |
| **squash + linear** | Repo merge-method settings (allow squash only) **+** ruleset `Require linear history`. Squash-only is a *repo* setting, not a branch rule (GitHub Docs, 2026-06-02). | HIGH. |
| **conflict / up-to-date** | Non-fast-forward push rejection (= "push is the claim") + `Require branches up to date before merging` (strict). For Actions checks to count in strict/queue mode they must trigger on `pull_request` (+ `merge_group` if a queue is used). | HIGH. |
| **merge queue** (optional) | GA since 2023-07-12; **plan-gated**: org-owned **public** repos, and **private** repos only on **GitHub Enterprise Cloud**; checks must fire on the `merge_group` event. | HIGH. **Not required for the MVP** (strict up-to-date suffices for a low-volume small team). |
| **CODEOWNERS reviewer routing** | `Require review from Code Owners` composes *on top of* the count and is **the only native way to require an *individual* identity** (the GA ruleset "Required reviewer" rule, 2026-02-17, supports **teams only**). Any-one-of-many owners satisfies it; path-scoped. | HIGH. Use a **team** as the reviewer identity for robustness; individual via CODEOWNERS if a single human reviewer is wanted. |

### 2.3 Capability gaps to surface (no current GitHub answer)

1. **Plan-tier wall (load-bearing for the target market).** Branch protection **and** rulesets are **free only on *public* repos**; **private** repos need **GitHub Pro/Team minimum**, and **merge queue on private repos needs Enterprise Cloud** (GitHub Docs *About rulesets* / *About protected branches*, 2026-06-02; community #174400). **A solo dev on a *free private* repo cannot enforce independent review at all.** CE must treat "is this repo on a plan that can enforce review?" as a **preflight requirement** (§4) and surface the upgrade as part of the install plan.
2. **No per-token IP allowlist / branch scope** (confirmed absent). Branch isolation is *only* server-side ref policy.
3. **Bypass-list auditability.** The 2025-09-10 ruleset "exempt" bypass type **silently skips enforcement**. If a CE App/Controller is ever placed on a bypass list, it could merge past the gate **without an audit signal** — design the bypass model to keep CE actors *off* the protected-branch bypass list.

> **The forge-adapter is genuinely thin** (≈10 operations, GitHub being a near-perfect fit), which is *evidence for* the rent-to-GitHub decision. But the three gaps above are the price, and CE owning them ("we configure the ruleset correctly so you never touch it") is precisely the product's value proposition.

---

## 3. Container + in-container enforcer design (plane C — the differentiator)

### 3.1 The threat model that drives the design

GitHub/CI gate the *push*, not what the agent does *before* pushing. And the agent + everything it `pip`/`npm`-installs is **inside** the secret/token blast radius — masking is best-effort and trivially defeated (`printenv | base64`), OIDC tokens aren't masked, and real 2026 incidents (tj-actions, 23k+ repos, 2025-03; Laravel-Lang, 2026-05-22) exfiltrated CI secrets (GitHub *Security hardening for Actions*, 2026-06-02). Combined with Ona's "agent disables its own sandbox" result, the enforcer's design rules are:

- **The boundary is the container + the network proxy, not any in-process check.** Deny-by-default, enforced *below* the agent.
- **The agent never holds the network or the secrets directly** — a host-side egress proxy does (capability separation, per Pipelock/agent-vault prior art).
- **No self-service escape hatch** (the Claude Code `dangerouslyDisableSandbox` / `allowUnsandboxedCommands` equivalent is forced **off**).
- **Path/pattern policy is advisory + audit only** (defeated by `/proc/self/root/...` and the `ld-linux …` dynamic-linker mmap trick — Ona, 2026-03-03).

### 3.2 Enforcer layers (priority order, all dated-source grounded)

1. **Outer boundary = a fresh, ephemeral, hardened OCI container per task.** `--cap-drop ALL`, read-only rootfs + tmpfs, custom seccomp, **no host bind mounts (never the docker/podman socket, never `$HOME`/`.ssh`/`.gnupg`/`.aws`)**, `--security-opt no-new-privileges`, non-root/rootless+userns, torn down per task. *Zero extra runtime dependencies; maximally portable, auditable, signable.* Prefer **gVisor (runsc)** as a drop-in OCI runtime when the host offers it cheaply (no KVM needed; ~18–35% overhead). Reserve **Firecracker/Kata** for hosts that genuinely expose KVM and need hardware isolation — **off the table for cheap VPS / inside CI runners**, so not the default (Edera/Northflank isolation comparisons, 2025–2026; OWASP Docker Security Cheat Sheet, 2025).
   - **In-repo seed:** `worker_runtime.py` + `worker_container_policy.py` already implement *rootless Podman*, a **credential broker that passes secret *names* not *values*** (secret values never enter argv/records), **forbidden-mount refusal** (host home, docker/podman sockets, SSH/GPG agents), **controller-key-secret refusal**, and the rule that *"a non-empty egress allowlist with no proven enforcement primitive is refused before the container starts."* The v2 *claim-binding* is the deadlock vector to drop; the **isolation primitives + the policy schema (`schemas/worker-container-policy.schema.yaml`) are directly salvageable** as the v3 enforcer's policy schema, decoupled from claims.
2. **Egress allowlist = the primary anti-exfiltration control.** A **deny-by-default egress proxy outside the agent** holds the network and logs every outbound request to a hash-chained, Ed25519-signable, tamper-evident log. Single-binary OSS exemplars exist (Pipelock — ~20 MB Go binary, Apache-2.0, 48 credential patterns, signed assessment bundles; agentcage; Infisical agent-vault — HelpNetSecurity 2026-05-04). **Reusable directly: Anthropic's own `@anthropic-ai/sandbox-runtime` (srt)** — Apache-2.0, bubblewrap + netns + seccomp + host-side deny-by-default egress proxy, v0.0.52 (2026-05-19), the same primitives behind Claude Code's `/sandbox` (Anthropic Engineering, 2025-10-20).
   - **Crux (decide consciously):** a hostname-only allowlist *without TLS termination* is **bypassable via domain fronting**, and a broad entry like `github.com` becomes an exfil channel (Claude Code sandboxing docs, 2026). A *real* exfil guarantee needs a **TLS-terminating proxy with CE's own CA injected** (breaks cert-pinned tooling) — vs. an **advisory allowlist** (tools "just work"). **Recommendation:** ship advisory allowlist by default; make CA-terminating mode opt-in for high-assurance tenants, with the side-effect log as the always-on backstop.
3. **Secret scanning (defense-in-depth, pre-push).** `gitleaks`/`trufflehog` as a pre-commit/pre-push step inside the container; **GitHub push protection** (secret scanning) as the server-side backstop — note push protection's availability is itself plan-gated, so the in-container scan is the portable layer.
4. **Command/secret *advisory* policy = the `hook_check` classifiers, decoupled from posture.** Reuse `is_secret_path` (matches `.env*`, `id_rsa/.pem/.key`, `.ssh/.aws/.gnupg`, credential-like names) and `classify_mechanics` (`gh pr merge`, `git push`, `npm/twine/cargo publish`, etc.) as an **audit + advisory + log** layer — **explicitly not the security boundary** (see §3.1). Crucially, in the new model the old "deny `gh pr merge` / `git push` without authority" largely *evaporates*: **the scoped token simply can't merge** (ruleset) and push is repo-scoped — so this policy shrinks to local-safety + secret-access *signalling*.
5. **Signed/attested enforcer image.** Build the enforcer image in GitHub Actions, attach a **GitHub Artifact Attestation** (`actions/attest-build-provenance`, SLSA), optionally **cosign**-sign; verify offline (`gh attestation verify`) before the image may launch a task (GitHub Docs *Artifact attestations*, 2025). This dovetails with CE's GitHub-native posture and the existing hash-chain audit idea.

### 3.3 Runner-backend recommendation (with current-research tradeoffs)

The evidence rejects a single backend; it points to a **split** aligned exactly with A/B/C:

| Backend | Fit | Hard limits (cited) |
|---|---|---|
| **GitHub-hosted Actions** — **USE for plane A + B** (CI checks, coordination triggers) | Free/cheap (incl. **free ARM**), ephemeral *clean* VM, per-job **auto-expiring, read-only-by-default** `GITHUB_TOKEN`, OIDC, GitHub-managed identity/secrets. Ideal for short, sandboxed checks. | **6-hour hard job cap** (not raisable via `timeout-minutes`); **35-day** run cap; **no GA native egress firewall** (roadmap → preview ~late-2026, GA ~H1-2027); **no supported interactive shell** (only the budget-burning `action-tmate` hack); concurrency caps (Free 20 / Pro 40 / Team 60 / Ent 500). (GitHub Docs *Actions limits*; *2026 security roadmap*, 2026-03-26.) |
| **Self-hosted runner *or* plain orchestrated container** — **USE for plane C** (the long-lived interactive agent) | You own egress (real allowlist proxy), lifetime (5-day job cap self-hosted; unlimited plain), interactivity (attach/observe), and the gVisor/hardening choices — **matches the container-per-Controller model**. | **You own** OS patching, isolation, ephemeral teardown; **persistent runners are a known backdoor vector** (Sysdig, 2026); mandatory runner upgrade ≥ v2.329.0 by 2026-03-16; plain container rebuilds the identity/secret plumbing Actions gives free. |

> **Critical incompatibility:** `step-security/harden-runner` block-mode egress is **Linux-only, needs `sudo`, and *does not work when the entire job runs inside a `jobs.<id>.container`*** (harden-runner limitations.md, 2026). So you cannot get harden-runner egress enforcement *and* a custom job-container image in the same hosted job.

**Recommended phasing:**
- **Spike/MVP (fastest defensible proof):** a **hosted `ubuntu-latest` job per Controller** with the **agent running on the runner host (not in `jobs.container`)** + **harden-runner in block mode** for egress + the 1h scoped App token. Here "container-per-Controller" ≈ "ephemeral-clean-VM-per-Controller" — *good enough* isolation, accepting the 6h cap and best-effort egress. Cheap, GitHub-native, proves the motion end-to-end.
- **Production (long/interactive/high-assurance):** the **CE-orchestrated hardened container** (gVisor where available) on a self-hosted runner or plain host, with the **TLS-terminating egress proxy** and signed enforcer image. This is where the enforcer earns its keep — and where the **extraction trigger** likely fires.

### 3.4 Enforcer-extraction-trigger thresholds (concrete, pre-committed)

Extract the enforcer to its own repo when **any one** of these becomes true (measured by the spike, §8):

1. **Stack divergence — fires on first compiled component.** The moment the egress proxy / kernel-level enforcer wants a **non-Python, compiled** implementation (Go single-binary à la Pipelock/Veto, or an **eBPF-LSM** content-addressable enforcer per Ona's "Veto") → extract that component. *Threshold: > 0 lines of compiled/non-Python enforcer code.*
2. **Dependency-profile divergence.** When the enforcer needs **> 2 system-level (non-pip) dependencies** (bubblewrap, `runsc`, `libseccomp`, a CA-terminating proxy) that would otherwise pollute the validator's pure-Python `cp314` offline wheelhouse → extract (keep the wheelhouse clean and air-gappable).
3. **Independent audit/release cadence.** When the enforcer needs a **security patch that cannot wait for the next spec/check gate**, or a **third-party security audit + signing cadence** of its own (it *is* the security boundary; it should be independently sign-able/attestable and versioned) → extract. *Threshold: ≥ 1 out-of-band security release, or any scheduled enforcer-specific audit.*

Until a trigger fires, the enforcer stays an **internal, separately-publishable package** in the monorepo (Brief §4), seeded by `worker_container_policy` + `worker_runtime`.

---

## 4. Agent-native install contract (P1)

**There is already a working seed in-repo:** `docs/operations/AGENT_NATIVE_BOOTSTRAP.md` + the machine-readable companion `templates/hermes/agent-native-bootstrap.yaml` + the `ce doctor --json` preflight + blocked-report semantics + one-directional authority + uv-first/pip-fallback install. v3's job is to **lift that pattern from "configures the local kernel" to "configures the user's GitHub"** — which the v1 bootstrap explicitly *forbade* (`github_connector: false`, `network_at_runtime: false`). The shape is proven; the scope expands.

### 4.1 The contract format (agent-agnostic, declarative + idempotent + a thin runbook)

A versioned `ce-install.yaml` (consumed, never mutated, by any harness — Claude Code / Codex / OpenClaw), structured as **desired-state + per-step required-inputs schema + verification/idempotency**, with a thin imperative runbook companion (`INSTALL.md`). Evolve the existing template:

```yaml
kind: ce-install-contract
schema_version: "1"
product: creator-engine ; product_version: "3.0"

authority_model: { direction: one-directional, agent_self_ratify: false }   # kept from v1

required_inputs:                       # the preflight schema (interactive OR pre-staged, Terraform-style)
  - id: repo               type: github_repo        required: true
  - id: plan_tier          type: enum[public|pro|team|enterprise_cloud]   required: true
    verify: "review-enforceable plan (NOT free-private)"            # the plan-tier wall, §2.3
  - id: github_app_private_key  type: secret  required: true  created_by: human   # LOCKED guardrail
  - id: reviewer_identity  type: github_team_or_user  required: true
  - id: egress_allowlist   type: list[domain]  required: true  default: [github.com, <model-api>, <pkg-registries>]

preflight:                              # gate BEFORE any apply; reuses the `ce doctor` precedent
  command: ["ce", "install", "preflight", "--json"]
  on_failure: blocked-report  # name the missing inputs / unsatisfiable plan-tier; STOP, no hidden fallback

plan:                                   # ratify-before-apply (Terraform plan/apply analog)
  emit: ["ce", "install", "plan", "--json"]     # desired vs actual diff; NO mutation
  ratify: "human approves the plan artifact (approved GitHub issue / plan-PR) before apply"

apply:                                  # each step idempotent + has a verify
  - configure_repo:          { idempotent: true, verify: "rulesets == desired" }
  - install_required_checks: { idempotent: true, verify: "required checks registered" }
  - provision_runtime:       { idempotent: true, verify: "enforcer image attested + reachable" }

boundaries: { least_privilege: true, agent_mints_root_credentials: false }
```

### 4.2 The locked security guardrails (Brief §5 / P1)

Because **installing a *security* product is itself security-sensitive** (the install agent stands up the very guardrails — App keys, rulesets, egress policy), the install **dogfoods CE's ratify-then-execute**:

- **`plan` → human ratifies → `apply`.** No mutation before an approved plan artifact (same mechanism as the runtime ratification gate, §5).
- **Human creates the GitHub-App private key** in a guided step; **the agent never mints root credentials** (`agent_mints_root_credentials: false`). The agent only ever *uses* short-lived installation tokens minted *from* that human-created key.
- **Least-privilege** at every step (the App requests only `contents`/`pull_requests`/`administration`-for-config; tokens down-scope further).
- **Preflight refuses an unsatisfiable plan-tier** (free-private repo → independent review unenforceable → blocked-report).

### 4.3 Dogfood: a CE check validates the contract

Add a v3 check `ce_install_contract` (modeled on the existing `extension_hook_contract` / template-validation pattern and `schemas/*.schema.yaml`) that validates `ce-install.yaml` against a schema — so **CE validates its own onboarding artifact** with the same validator it ships. The README/website is the **dual-purpose surface** (human-readable AND agent-executable), and its embedded contract is CI-checked like any other artifact.

---

## 5. Orchestrator design + ratification gate, and a thickness assessment

### 5.1 The lifecycle (one Controller task)

```
1. preflight(required_inputs)                      # §4 — refuse on missing input / unenforceable plan-tier
2. forge.plan_approved(plan_ref)  ── gate ──       # MUST be approved before anything starts
3. token = forge.mint_scoped_token(repo, {contents:write, pull_requests:write}, ttl=1h)
4. ctx   = runner.provision(image=attested_enforcer, token, manifest, egress_allowlist)
5. agent authors inside ctx → forge.open_change(branch, manifest, plan)
6. GitHub runs required checks + independent review;  forge.merge() only when all satisfied
7. runner.teardown(ctx)  ;  collect side-effect log + completion-report evidence
```

### 5.2 The ratification gate (re-homed)

"Operator ratifies `prompt:<abs>` with SHA" becomes: **the Operator approves the gate's plan artifact** — an **approved GitHub issue or a "plan-PR" that declares the spec + the committed manifest.** The orchestrator **will not call `runner.provision()` until `forge.plan_approved()` is true**, and CI enforces `diff == declared manifest` (§7). Same guarantee (human approves the plan a-priori; scope is pinned), now native + auditable. This preserves the **batch strict-mode cadence** (SHA-pinned, closed manifest, distinct independent review, squash merge) on a GitHub-native substrate.

### 5.3 How thick is the orchestrator, really?

**Thin — by construction, and the evidence supports it.** The orchestrator's authored surface is **glue**: mint a token (one REST call), check approval (one query), provision/teardown a runner, collect results. Everything heavy is **rented**: coordination/review/merge (GitHub rulesets), scope (CI check), runtime safety (the enforcer package), execution (the runner). My estimate: a few hundred LOC of GitHub-API + lifecycle glue, **not** a coordination engine.

> **This directly contradicts the Brief §4's "market input already established the orchestrator is *thick*."** My read from the current evidence: the orchestrator is **thin**; the **enforcer (plane C) is the thick, genuinely-ours part.** The "thickness" the market sensed is real but it lives in the **enforcer + the install-time integration complexity (configure_repo correctly, keep the App off bypass lists, handle the plan-tier wall)** — not in a bespoke coordinator. The spike (§8) measures this precisely; I pre-commit the threshold in §8.4. *(This is one of two places I push back on a stated input — see §10.)*

---

## 6. Version coexistence plan (v1 retained; boundary declared + guarded)

**Superseded — this section replaces the prior "D0–D6 deletion plan" with version coexistence** (shipped in G-3.9, PR #152; see `docs/architecture/VERSION_BOUNDARY.md`). CE v1.0 is **retained whole**: we operate on the v1 coordination/posture/lane/reviewer surface to build v3.x, and v1.0 is a shipped working system. That surface is **not deleted** — it is classified `v1` in `creator_engine_validator/_versions.py` and guarded by the `version_boundary` check (HARD v1⊥v3 + a baselined `shared→version` allowlist ratchet). **D0** (advisory author-time hook) already landed; **D1–D6 are not executed** — their modules are re-labeled `v1` and kept. Any future removal is **orphaned-only** (proven dead to *both* versions), never the version-bearing machinery.

The original dependency analysis is why coexistence is clean and was already true on `main`: the graph is **one-way** — `hook_check.py` imports the *durable* checks (`completion_report_*`, `mutation_class`, `path_manifest_fidelity`); the durable checks do **not** import the v1 coordination/posture machinery, and the v3 surface imports neither (the ~9% v1 cluster, per the prior architect). The table below is retained as the **v1-surface inventory** — read its historical "Retire / Why safe" columns as the *superseded* deletion rationale; the modules themselves stay.

**v1-surface inventory (was: ordered deletion series — superseded; modules retained + classified `v1`):**

| PR | Retire (modules / checks / CLI / docs / schemas) | Why safe |
|---|---|---|
| **D0 — kickoff prerequisite** | Make author-time manifest enforcement **advisory** in `hook_check.py` (`_resolve_manifest`/`_resolve_posture` → report-only); **keep** secret + dangerous-mechanic classifiers as the enforcer seed. | Unblocks every governed Controller; first real retirement; permanent on the pivot path (§7 step i). |
| **D1 — reviewer-venue + harness-seat seam** | `reviewer_authority_envelope` (check + `schemas/reviewer-authority-envelope` + `REVIEWER_VENUE_AUTHORITY.md`) and its `hook_check` wiring; `harness_seat_contract`, `hook_pack_confirm`, `extension_hook_contract`, `.claude/hooks/*`; `HARNESS_SEAT_CONTRACT.md`. | Replaced by GitHub rulesets + a reviewer identity (the reviewer-venue PRs are **cut, not re-landed**). |
| **D2 — lane / launch / tmux / transcript** | `lane_runtime.py`, `tmux_adapter.py`, `transcript_archive.py`, `launch_runtime.py`, `claude_launch_spec.py`, `hermes_launch_spec.py`, the `ce lane …` CLI group; `GOVERNED_LANE_LAUNCH_PROTOCOL.md`, `TRANSCRIPT_ARCHIVE_PROTOCOL.md`, `PANE_REGISTRY_PROTOCOL.md`. | Container-per-Controller replaces governed panes; no importer among durable checks. |
| **D3 — PCO ledger / leases / pane / containers-v2** | `pco_allocator.py` + `pco-allocate`/`pco-release` CLI; `active_work_ledger_schema` + `active_work_ledger_conflicts`; `worktree_lease_schema`; `controller_key_schema`; `pane_registry` (incl. **the `evaluate_posture` deadlock**); `container_instance`; `side_effect_ledger` + `side_effect_ledger_runtime` (git-audit role → GitHub events); the matching `scan-*` CLI subcommands + `ACTIVE_WORK_LEDGER_PROTOCOL.md`, `WORKTREE_*`, `SIDE_EFFECT_LEDGER_PROTOCOL.md`, `PCO_*`. | Coordination + audit rented to GitHub; container isolation makes leasing moot. |
| **D4 — strip `hook_check` to classifiers** | Remove posture/manifest resolution from `hook_check.py`; keep `is_secret_path` + `classify_mechanics` (relocated into the enforcer package). | The classifiers are the only part the enforcer needs. |
| **D5 — operating-mode runtime carriers** | `operating_mode_runtime_carriers` (carriers) — **keep** `operating_mode_policy` (policy). | Carriers were never load-bearing; policy is the product. |
| **D6 — reconsider (route-independent, judge at deletion time)** | `controller_runtime_contract`, `state_boundary_contract`, `state_version_record`, `distributed_identity`/`federated-identity-binding`, `pcl_record`/`pcl_runtime`, `ce_event_block`/`ce_event_runtime`, `connector_runtime`'s coordination bits, `fanin_runtime`, `integration_queue_dry_run`, `init_runtime`/`doctor_runtime`/`packaging_runtime`. | **PCL/CE-event *record schemas*** may survive as the audit/event spine; their *coordination/runtime carriers* are cut. `ce doctor`/`init` likely **evolve** into the §4 install preflight rather than delete. |

**The shared base — depended on by both versions (validated against Brief §7):** `path_manifest_fidelity` (+ promote, §7), the classifiers, `mutation_class`, `no_limitless_strings`, `completion_report_{schema,required_for_envelope,terminal_sections}`, the evidence schemas (`architect_/implementer_/review_evidence_schema`), `operating_mode_policy`, `connector_substrate` (+ the bounded read-only/`tracker_mirror` connector CLI), `ce_terminology_v2` / `role_enum_v2` (product vocabulary — **keep**, per the prior architect's disagreement with the "GitHub-RBAC-replaces-them" sweep), the sidecar/`duplicate_spec_id`/`definition_of_ready`/`crosswalk_register` family, and the whole infra spine (pytest harness, `loader`/`schema`/`reporting`/`cli`/`environment_guard`/`version`, the **cp314 offline wheelhouse**, `validate.yml`). **Re-home `worker_container_policy` + `worker_runtime`** into the enforcer package (drop claim-binding; keep isolation primitives + policy schema).

**Doc navigability (handled by labeling, not deletion):** README / GOVERNANCE / CONTRIBUTING gained v1↔v3 coexistence wording in G-3.9 (and the `version_boundary` taxonomy makes "what is v1 vs v3 vs shared" explicit), so the repo stays navigable without excision. The broader re-root toward the GitHub-native + container model proceeds as v3 matures, keeping the v1 protocols labeled `v1` rather than removed.

---

## 7. Dev-mode MVP gate breakdown + sequencing

The MVP (Brief §8): *one Dev-mode gate authored by a governed Controller inside a container with a scoped token + egress allowlist + in-container policy, opening a PR that GitHub rulesets + required CI (pytest + diff-gated `path_manifest_fidelity`) + required non-author review then merges — with the ratification gate (approved issue/plan-PR) blocking the container until approval exists.* Decomposed into ordered gates under the batch strict-mode cadence:

**Kickoff (route-independent; unblocks the fleet; first reusable platform slices):**

- **G‑i — Advisory author-time hook (= D0).** First machinery deletion; unblocks every Controller; keeps the classifier *denies*. *(hours)*
- **G‑ii — Promote `path_manifest_fidelity` to gate the *real PR diff* as a required CI check.** **This is net-new logic**, but the seed exists: `role_boundary_attribution.run_with_base()` *already* runs `git diff --name-only <base>..HEAD` and compares changed files to a manifest path-set. The v3 check = that diff machinery + `path_manifest_fidelity.extract_manifest_paths()`, sourcing the manifest from a **PR-carried committed file** (a `.ce-manifest`/`MANIFEST` or fenced PR-body block) instead of the soon-deleted `.hermes/handoffs/`. Add a CI job (the current `validate.yml` only runs the check against `examples/`, never the diff). Make it a **required status check**. *(hours–1 day; concern B made real for the first time + the empirical test of the brownfield thesis.)*
- **G‑iii — GitHub-native coordination config.** Rulesets (`Require a PR` + `approvals ≥ 1` + `most-recent-reviewable-push` + `dismiss-stale` + required checks + strict up-to-date + linear history + squash-only repo setting), CODEOWNERS, a distinct **reviewer team/identity**, the GitHub App + per-Controller scoped-token minting, **App kept off the protected-branch bypass list**. *(days, mostly config + the token minter.)*

**Build G‑ii + G‑iii as reusable functions, not throwaway scripts** — they are literally `install_required_checks()` and `configure_repo()` that the orchestrator (§5) later calls. The kickoff *is* the first slice of the platform.

**Then the MVP proper:**

- **G‑1 — Runner abstraction + hardened enforcer image (spike backend).** `runner.provision/teardown`; the ephemeral-clean-VM-or-container; harden-runner (audit→block) or the egress proxy; image built + attested.
- **G‑2 — Orchestrator glue + ratification gate.** `mint_scoped_token` → `plan_approved` gate → provision → collect (§5).
- **G‑3 — One real gate end-to-end** (e.g., a small substrate gate re-homed): governed agent in the container opens a PR; rulesets + required CI + non-author review merge it. **This is "first working v3."**

In-flight gates keep their *substance*; only authoring mechanics change — they author under G‑i (advisory), open PRs, GitHub gates merge (the `checks/__init__.py` overlap resolved by second-to-merge rebasing under strict mode). Blast-radius/quota/reversibility **schemas KEEP** as CI policy validators; ledger-mutation/runtime-carrier parts are CUT.

---

## 8. Out-of-box-UX spike spec (precise, buildable)

**Goal:** de-risk the topology + prove the product motion, and *measure the two empirical unknowns* with pre-committed thresholds.

### 8.1 What to build
**"One command configures a throwaway GitHub repo + drops the checks + runs one governed container task that opens a PR."**
`ce spike --repo <throwaway> --plan-tier <tier>`:
1. `configure_repo()` — create the throwaway repo, apply rulesets + CODEOWNERS + reviewer identity (G‑iii).
2. `install_required_checks()` — register pytest + diff-gated `path_manifest_fidelity` as required checks (G‑ii).
3. `provision_runtime()` — launch **one** hardened container/VM with a 1h scoped token + egress allowlist + advisory classifiers + side-effect log.
4. Inside it, a governed agent makes a tiny in-manifest change and `forge.open_change()` → a PR.
5. Observe: required checks run, independent-review gate blocks self-merge, side-effect log captured.

### 8.2 What it must measure
- **(a) Orchestrator thickness:** authored-orchestrator LOC, split into **GitHub-API/lifecycle glue** vs **bespoke coordination logic**.
- **(b) Enforcer divergence:** does the enforcer want a **non-Python/compiled** component? how many **system-level deps**? does egress enforcement need a **TLS-terminating proxy** (and how much agent tooling breaks)?
- Plus: does the **hosted 6h cap / egress limitation** force the self-hosted/plain-container path? does the **plan-tier** of the throwaway repo block review enforcement?

### 8.3 Pass/fail criteria
**PASS** iff: the single command yields a merged-blocked-until-reviewed PR with all required checks green, the agent could **not** self-merge, the agent could **not** reach a non-allowlisted host (or the attempt was logged), and **no host credential/secret left the container**. **FAIL** on any: scope violation merged, self-merge succeeded, egress to a non-allowlisted host succeeded undetected, or the App key was ever inside the task container.

### 8.4 Pre-committed extraction-trigger thresholds (decide *before* the spike, judge *from* its data)
- **Extract the enforcer** if spike shows **≥ 1 compiled/non-Python component** *or* **> 2 system-level deps** *or* a need for an **independent security release** (§3.4).
- **"Orchestrator is thick (bad)"** if **bespoke-coordination LOC > ~40%** of authored orchestrator LOC, or total authored orchestrator > ~800 LOC of non-glue → revisit the rent-to-GitHub assumption. Otherwise the **thin-orchestrator thesis holds** and the enforcer is confirmed as the center of gravity.
- **"Runner must leave hosted Actions"** if the spike task **needs > 6h, an interactive attach, or real (non-bypassable) egress** → production runner = self-hosted/plain container.

---

## 9. OD-04 supersession (draft v3 decision)

> **OD-04 (superseded):** "GitHub is transport + mirror only; CE is authoritative for coordination/review/merge."
>
> **OD-04′ (v3, proposed for Operator ratification):** *CE **rents** coordination, independent review, and merge discipline from a **forge**, accessed **behind a thin `forge` adapter** (≈10 operations, §2). **GitHub is the first forge backend, not the architecture.** CE remains authoritative only for the planes a forge cannot provide: **runtime safety of the autonomous agent (the in-container enforcer)**, **scope containment (the diff-gated manifest CI check)**, **operating-mode/autonomy governance**, the **connector authority model**, and the **audit/evidence spine**. OD-04's spirit is preserved as a design property: coordination stays behind the adapter, and the **runner stays behind an abstraction** (a self-hosted-runner / plain-container escape hatch is retained).*
>
> **Precise correction OD-04′ must encode (evidence, §2.2):** the per-Controller authority is a **credential fact only for *which repo* + *which permissions*** (a 1h scoped installation token). **Branch confinement and "cannot self-merge" are *not* credential facts — they are *ruleset/branch-protection* facts** (there is no branch-scoped token and no separable merge permission). Therefore CE's authority model = **scoped token *plus* a correctly-configured ruleset with CE's App kept off the bypass list.** CE owns getting that configuration right so the user never touches it.
>
> **Ratified constraints carried forward:** independent review uses GitHub's intrinsic author-cannot-self-approve + `approvals ≥ 1` + most-recent-push + dismiss-stale; the Operator remains the sole ratifier (and a trusted admin-bypass actor by design); the install dogfoods ratify-then-apply with a human-created App key.

---

## 10. Risks, open questions, decision-reversal triggers, and confidence

### 10.1 My read on the two pressure-tested decisions

**Monorepo-first — CONFIRM, ~75% confidence.** The evidence *strengthened* it: the enforcer is **not** greenfield — `worker_container_policy` + `worker_runtime` already provide rootless-Podman + credential-broker + forbidden-mount + egress-requires-enforcement primitives entangled with the validator's `loader`/`schema`/`reporting`/`side_effect_ledger`; the CI-checks library is proven and wired; the offline wheelhouse + the test harness + CI are reusable; extraction now pays re-establishment cost for **no** architectural benefit. The **one** genuine extraction pressure I found is real and *named as the pre-committed trigger* (§3.4): the enforcer's strongest form (agent-cannot-disable, kernel/eBPF-LSM or gVisor, Go single-binary egress proxy, independent security/sign cadence) may legitimately want its own repo — which is exactly what the spike measures. *Mono-first preserves that option at the lowest cost; split-then-merge would be a continuous coordination tax on a team-of-agents.*

**Rent coordination to GitHub — CONFIRM for v3, ~70% confidence, with two load-bearing caveats.** Strong support: independent review, dismiss-stale, required checks, scoped short-lived tokens, and squash/linear are all **real and current** (§2.2), and the adapter is genuinely thin. But: **(1) the plan-tier wall** — none of it is enforceable on a **free *private*** repo (Pro/Team min; merge queue needs Enterprise Cloud), which collides with the "solo dev, no devops, trust-sensitive about hosted" target who may well be on a free private repo; CE must make plan-tier a **preflight gate** and own the upgrade conversation. **(2) Authority is a *config* fact, not a *credential* fact** (branch confinement + no-self-merge live in the ruleset, and an App on the bypass list can merge silently) — so CE's promise ("we own the integration complexity") is *also* its risk surface: a mis-configured ruleset silently removes the guarantee. This is acceptable *because* CE validates its own config (the `ce_install_contract` dogfood, §4.3) — but it must be tested, not assumed.

### 10.2 Open questions for the Operator
1. **Plan-tier policy:** does CE's target audience accept "you need ≥ GitHub Team for private-repo governance," or must CE support **public-repo-only** for the free tier? (Determines the MVP repo's visibility.)
2. **Egress posture default:** advisory hostname allowlist (tools just work) vs. CA-terminating proxy (real exfil guarantee, breaks pinned tooling) as the *default*? (§3.2 crux.)
3. **Reviewer identity:** a CE-managed **reviewer team/App** vs. requiring the human to be the non-author approver? (Affects whether "one human, many agents" needs a second machine identity to satisfy `approvals ≥ 1`.)
4. **Runner home for production:** self-hosted runner (GitHub-native trigger/identity) vs. plain orchestrated container (max control)? (§3.3.)

### 10.3 Decision-reversal triggers
- Spike shows the **orchestrator is thick with bespoke coordination** (> ~40% non-glue) → the rent-to-GitHub thesis is wrong; reconsider.
- The **enforcer needs KVM/microVM** isolation that the target hosts (laptops, cheap VPS) don't expose → the "minimal-dependency self-installed enforcer" story collapses to gVisor-or-hardened-container only; revisit the security claims for high-assurance tenants.
- GitHub ships the **native L7 egress firewall to GA** sooner than expected → the hosted-Actions path for plane C becomes viable and the self-hosted-container recommendation weakens (re-evaluate at GA).
- The Operator prioritizes a **forge other than GitHub** sooner than v3 → the adapter must be validated against a second backend earlier (GitLab) to avoid silent GitHub coupling.

### 10.4 Where my evidence was thin
- **3 of 18 research agents** failed to emit structured output (egress-tooling + coding-agent-orchestration dimensions; GITHUB_TOKEN-exfil verifier). Adjacent agents covered all three, but the *coding-agent-orchestration prior-art* (Copilot coding agent / Codex cloud / Jules internal architecture) is my **thinnest** area — treat any specific claim about how those products mint credentials as unverified; the architecture *lessons* I used (thin orchestrator, credentials outside the agent, plan/apply ratification) are corroborated by the Terraform/OIDC/token findings.
- **GitHub docs are undated** in rendered markdown; currency is anchored to dated *changelogs* (2026-03-10 API version; 2026-04-24 stateless tokens; 2026-02-17 required-reviewer; 2026-03-26 egress roadmap). The exact **plan-tier matrix for rulesets in 2026-06** and **rulesets-vs-classic merge-queue GA** should be re-confirmed live at config time.
- pytest was **not** executed (read-only); repo behavior rests on direct reading + asserted test behavior. The **TLS-MITM "how much tooling breaks"** tradeoff is unquantified in any source found.
- **Ona's "Veto" eBPF-LSM enforcer** is the most on-point "agent-cannot-disable" prior art but is vendor-blog-only — no independent eval, unclear self-hostable license, and BPF-LSM typically needs host/privileged access (may not run unprivileged inside a container). Validate hands-on before betting the enforcer on it.

### 10.5 Key dated sources (load-bearing)
GitHub Docs *About protected branches* / *Available rules for rulesets* / *Approving a PR with required reviews* (accessed 2026-06-02); *New Branch Protections: Last Pusher* (changelog 2022-10-20); *Required reviewer rule GA* (2026-02-17); *Generating an installation access token* & REST *Create an installation access token* (API version 2026-03-10); *New limits on scoped token creation* (2024-02-22); *New format for installation tokens* (2026-04-24); *Actions limits*, *Running jobs in a container*, *GITHUB_TOKEN security*, *OpenID Connect* (2026-06-02); *Default GITHUB_TOKEN read-only* (2023-02-02); *What's coming to our GitHub Actions 2026 security roadmap* (2026-03-26/30); *Pull request merge queue GA* (2023-07-12); *arm64 standard runners in private repos* (2026-01-29); step-security/harden-runner README + limitations.md (v2.19.4, 2026-05-21) + DoH bypass CVE-2026-25598 (devansh, 2026-03-15); Anthropic `@anthropic-ai/sandbox-runtime` (2026-05-19) + Claude Code sandboxing (Anthropic Engineering, 2025-10-20); Ona *How Claude Code escapes its own denylist and sandbox* (2026-03-03); Pipelock AI agent firewall (HelpNetSecurity, 2026-05-04); GitHub *Artifact attestations* + `actions/attest-build-provenance` (2025); Edera/Northflank gVisor-vs-Kata-vs-Firecracker (2025–2026); OWASP Docker Security Cheat Sheet (2025).

---

**Bottom line for the build agents:** keep the repo (evolve), **retain** the ~9% v1 coordination/posture/lane/reviewer surface — classified `v1` in `_versions.py` and guarded by `version_boundary`, cleanup orphaned-only (the prior D0–D6 deletion series is superseded by version coexistence), promote `path_manifest_fidelity` to the diff gate (seed: `role_boundary_attribution.run_with_base`), configure GitHub rulesets to *rent* independent review (it works — author-self-approve is structurally blocked), mint 1h repo+permission-scoped App tokens (but enforce branch/merge confinement in the **ruleset**, not the token, and keep CE's App off the bypass list), build the genuinely-ours **in-container enforcer** around the *container + egress-proxy* boundary (never a path denylist the agent can defeat), seed it from `worker_container_policy`/`worker_runtime`, run plane C in a CE-controlled container (not a hosted job) for production, dogfood the agent-native install with a human-created App key and ratify-before-apply, and let the spike decide enforcer-extraction with the thresholds pre-committed in §3.4/§8.4.
