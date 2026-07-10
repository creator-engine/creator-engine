# CE as Contractor — Client-Tenant Deployments: Design Doc

**Status:** Draft for ratification (architect_research output; controller to file as ce-ops ticket)
**Author role:** `architect_research` (read-only worker) — findings only, no mutation performed
**Date:** 2026-07-03
**Grounding:** Live evidence from `/home/cedev2/creator-engine` (branch `ce-release-0.3.1-rc2`) cited by file/line where verified. Claims sourced from operator-supplied framing (not independently verifiable in this repo) are marked **[context]**.

---

## 0. Scope and method

This doc evaluates the operator-ratified framing (five planes, three deployment models, two-lane App-auth doctrine, known gap tickets, sequencing doctrine, authority doctrine) against what actually exists in the repo today, and produces the nine required design sections. Where the repo already contains a mechanism that generalizes cleanly to multi-tenant, the doc says so explicitly and cites it; where the repo shows a **single-tenant assumption baked in**, the doc names the exact place that assumption lives so a future implementer does not have to rediscover it.

Headline finding: **CE's governance, forge-driver, and credential-broker code is already object-parameterized per repo/App/installation** (nothing in the core drivers hardcodes "CE's own repo"), but **the deployment substrate around it (fleet containers, broker configs, OpenBao path layout, confidentiality guard) is hardcoded to one tenant (CE itself) with Mythos handled as a hand-run exception**, not a second tenant of a generalized mechanism. The gap is almost entirely in the *substrate/config* layer, not the *governance/driver* layer. This is good news for sequencing: Phase 1–2 (below) is mostly wiring existing primitives to a second identity set, not inventing new governance.

---

## 1. Tenant model

### 1.1 What a tenant is, grounded against existing record-kind patterns

The repo has no `tenant-record` schema or kind today (verified: no hits for `tenant` under tracked root paths outside review worktrees; `Grep pattern="tenant"` across `/home/cedev2/creator-engine` root returns nothing outside `.ce/wt-*-review/` copies). This is a real gap (§7, G1), but CE already has a mature pattern for "a governed record kind that names an isolation posture, is Source-ratified, and is bound by SHA into runtime instances" — the **Worker-Container Policy record** (`schemas/worker-container-policy.schema.yaml`, contract at `docs/operations/WORKER_CONTAINER_PROTOCOL.md:35-69`). A tenant record should follow the same shape discipline: required fields, `additionalProperties: false`, a `policy_sha`-style binding, and a forbidden-mount/forbidden-secret predicate class (mirroring `PCO-045`, `docs/operations/WORKER_CONTAINER_PROTOCOL.md:205-228`).

A tenant, as a first-class object, needs to name:

- **Identity set** — the tenant's App(s), each with a `custody_lane` (`shared` vs `own` per the operator's two-lane doctrine — **[context]**, not yet documented in this repo), a role tag, and secret pointers only (never PEM/token by value — this is the existing invariant from `schemas/install-answers.schema.yaml:590-597` `secret_ref` def, which already forbids raw secrets by construction and should be reused verbatim for tenant App PEMs).
- **OpenBao mount** — today CE uses one shared `ce-kv` mount with path-prefixing per dev/App (`docs/devops/openbao/openbao-secret-path-map.tsv:2-8`, `docs/devops/openbao/ce-dev-policy.hcl.tmpl:16-22`: `path "ce-kv/data/devs/__CE_DEV_ID__/runtime/*"`). A tenant record needs an explicit `openbao_mount` field because — per §2 below — path-prefix-in-shared-mount is a weaker isolation wall than a dedicated mount, and a tenant boundary should get the stronger primitive.
- **Denylist/confidentiality SSOT** — today this is `validators/creator_engine_validator/public_docs_confidentiality.py`, a single, unidirectional (CE-internal → CE-public) wall. A tenant record needs a pointer to its own denylist fragment (§5).
- **Issue venue** — today hardcoded to `ce-ops` for CE's own work; Mythos work is filed as a first-value Scope directly against the client repo (`docs/guide/first-value-mythos.md:1-18`), which is already the right per-tenant pattern — it just isn't named as a tenant field anywhere.
- **Fleet allocation** — today zero: no fleet seat is bound to Mythos (confirmed by `deploy/dgx-runsc/` and `tools/egress-broker/apps.example.json:4` naming only `creator-engine/creator-engine` as the broker's repo, and seat ids `dev-1..4` as CE's own seats, not tenant-scoped seats).
- **Governance config** — the branch-protection reference posture is already schema-driven and reusable per repo (`schemas/install-answers.schema.yaml:324-374`, `x-ce-reference-posture`), so "governance config" per tenant is largely "which repo, and does this tenant's answer weaken or strengthen the CE floor" — the existing `ratification_binding` def (`schemas/install-answers.schema.yaml:601-625`) already encodes "an agent can configure anything except a weaker grader," which is exactly the client-as-Operator authority shape needed (§6).

### 1.2 Tenant manifest sketch (proposed — not a ratified schema; NEW-TICKET-NEEDED, see G1)

```yaml
# PROPOSED SHAPE — not yet a schema/validator in this repo (§7 G1).
# Registry-style: one file per tenant, secrets as pointers only, never by value.
kind: tenant-record            # proposed discriminator, mirrors worker-container-policy-record
tenant_id: mythos
display_name: "Mythos (Arad)"
status: active                 # active | onboarding | suspended | offboarded
deployment_model: C            # A | B | C — see §3
created_at: "2026-06-01"

identity:
  apps:
    - app_name: mythos-ce
      role: infra-adoption          # matches operator context: infra/adoption App
      custody_lane: own             # own | shared — see §3/§6; Mythos today is de facto "own"
      app_id_ref: "openbao://ce-kv-tenant-mythos/forge/github-apps/mythos-ce/app-id"
      client_id_ref: "openbao://ce-kv-tenant-mythos/forge/github-apps/mythos-ce/client-id"
      private_key_ref: "openbao://ce-kv-tenant-mythos/forge/github-apps/mythos-ce/private-key"
      installation_id: 141552951    # verified: playbooks/controller/runbooks/arad-pilot.md:28
    - app_name: mythos-arad
      role: user-seat                # kind:own, client-controlled — [context]
      custody_lane: own
    - app_name: mythos-agents
      role: fleet-seats-reserved      # third org App reserved for fleet seats — [context], not live
      custody_lane: shared

credential:
  openbao_mount: ce-kv-tenant-mythos   # dedicated mount, NOT a path-prefix in shared ce-kv (§2)
  policy_ref: "policy-ref:ce-tenant-mythos-runtime"

confidentiality:
  denylist_ref: "governance/tenants/mythos/denylist.yaml"   # proposed path; extends public_docs_confidentiality.py (§5)
  cross_tenant_isolation: enforced

issue_venue:
  kind: client-repo              # today's Mythos pattern — file Scopes directly on the client repo
  repo: chmod735-dor/mythos

fleet_allocation:
  seats: []                       # empty today; Phase 2 adds the first fleet seat (§8)
  reviewer_identity: ubuntuaws745-cmyk   # verified distinct-reviewer login: arad-pilot.md:128
  merging_bot: "mythos-ce[bot]"

governance:
  repo: chmod735-dor/mythos
  protections: reference          # the x-ce-reference-posture floor (schemas/install-answers.schema.yaml:329-344)
  autonomy_tiers:                 # tenant-side ratification target — see §6
    docs_class_automerge: false
    tier_a: false
    tier_b: false
  ratified_by: arad
  ratification_ref: "<64-hex approver_ref>"   # same shape as ratification_binding, schemas/install-answers.schema.yaml:601-625
```

---

## 2. Credential topology

### 2.1 What exists and generalizes cleanly

- **The forge driver itself is already tenant-shaped.** `LiveForgeConfig` (`validators/creator_engine_validator/onboard_apply_live.py:419-469`) takes `repo`, `installation_id`, `app_client_id`, and an optional `signer`/`token_minter` per call — nothing in the driver assumes "CE's own repo." The same class instantiated with Mythos's `repo`/`installation_id`/App identity is exactly how `scripts/first-value.sh` already drives Mythos (`docs/guide/first-value-mythos.md`, `playbooks/controller/runbooks/arad-pilot.md`). **This means the core governance/forge plane needs no redesign for multi-tenancy — only the surrounding config/credential plumbing does.**
- **The mint-broker's binding check is already the right multi-tenant security primitive.** `tools/mint-broker/mint_broker/binding.py:1-26` calls `GET /user/installations` **with the caller's own token** and asserts the claimed `installation_id` is in that user's list before minting anything — this is precisely the "prove you control this tenant's installation before I mint you a token for it" check a multi-tenant broker needs, and it is already built and tested (per the module docstring, "the SECURITY CRUX").
- **The OpenBao per-identity path convention already exists** for CE's own devs and Apps: `docs/devops/openbao/openbao-secret-path-map.tsv:4-8` shows `ce-kv/forge/github-apps/<app-name>/private-key` and `.../config` as the live-intended layout, and `docs/devops/openbao/ce-dev-policy.hcl.tmpl:16-22` shows the per-identity least-privilege policy template (`path "ce-kv/data/devs/__CE_DEV_ID__/runtime/*" { capabilities = ["read"] }`). This is a direct, provable template for a per-tenant policy — swap `devs/__CE_DEV_ID__` for `tenants/__CE_TENANT_ID__`.

### 2.2 What must change: single-controller-holds-all-keys is the current live reality

Today, for the one real client tenant (Mythos), the App PEM and env file live **on the CE controller/orchestrator host**, not in any per-tenant wall: `playbooks/controller/runbooks/arad-pilot.md:82-95` places the App PEM at `/dev/shm/mythos-ce-app.pem` (tmpfs, controller-host-local) and sources `~/.ce-keys/mythos-ce-app.env` from the controller's own key directory — the same directory pattern CE uses for its own dev App PEMs (`tools/egress-broker/apps.example.json:35,45,63`: `/dev/shm/ce-dev1/...pem`, etc.). **There is no wall between "CE's own App keys" and "Mythos's App key" other than filename convention on one shared host.** Any process with controller-host access today can read every tenant's App key. This is the exact gap the operator's framing names ("today's single-controller-holds-all-keys reality").

The mint-broker config format makes the same assumption structurally, not just operationally: `tools/mint-broker/mint_broker/config.py:45-56` defines `MintBrokerConfig` with **one** `app_client_id` / `pem_path` per loaded config — there is no `tenants: {...}` map, no per-installation-to-App routing. `handle_token_request` (`tools/mint-broker/mint_broker/service.py:130-238`) mints against exactly the one App the process was configured with. **This is the concrete, in-repo shape of the "#419 one-App-per-config" gap** [context ticket number, verified structural gap]: to serve two tenants' Apps from one standing broker, the config and the request-routing both need a `tenant_id`/`app_selector` dimension before the existing ceiling/binding/mint pipeline runs.

Similarly, `tools/egress-broker/apps.example.json:4-6` hardcodes `"repo": "creator-engine/creator-engine"` and `"installation_owner": "creator-engine"` **at the top level of the config**, with `seats{}` mapping only to CE's own `dev-1..4` identities. The self-push/self-review brokers (`tools/egress-broker/README.md`) are single-repo by construction today. A tenant-scoped seat pushing to `chmod735-dor/mythos` needs either a second broker config file (workable short-term) or a `repo` field per seat/tenant (the real fix, G8 in §7).

### 2.3 What "seats resolve only their tenant's mount" requires

No runtime code today resolves a mount by tenant — the closest analog is the Worker-Container Policy `mount_manifest` default-deny list (`docs/operations/WORKER_CONTAINER_PROTOCOL.md:56,205-228`), which is role-scoped, not tenant-scoped. For a tenant-scoped worker container, the policy/instance pair (`schemas/worker-container-policy.schema.yaml` / `schemas/container-instance.schema.yaml`) would need either (a) a `tenant_id` field threaded through `mount_manifest` and `secret_grants` so a container can only ever be handed the OpenBao AppRole token for its own tenant's mount, or (b) tenant isolation enforced one level up, by never launching a cross-tenant worker from the same policy record at all (simpler, and consistent with "policy records are Source-ratified" — a tenant's policy record would itself live under a tenant-scoped governance path, mirroring the `governance/policies/worker-container/` arming-gate pattern already used for `PCO-042` (`docs/operations/WORKER_CONTAINER_PROTOCOL.md:165-174`)).

**Recommendation (default):** one OpenBao mount per tenant (`ce-kv-tenant-<id>`), not a path prefix inside the shared `ce-kv` mount that CE's own devs use. This is a deliberate strengthening over the existing per-dev pattern: a mount boundary is enforced by OpenBao's own ACL engine at the mount root, so a policy-authoring bug that leaks a broader path glob cannot cross a mount the way it could cross a path prefix in a shared mount. Flagged as **Open Question 3** in §9.

---

## 3. Three deployment models

The operator's A/B/C framing is sound and matches what little live evidence exists. Grounding and sharpening each:

### Model A — CE-hosted fleet, client repo via App installation

**Trust boundary (text diagram):**
```
[Client repo, GitHub-hosted] <--App installation-scoped JIT token--> [CE-hosted fleet: controller + worker containers]
                                                                              |
                                                                    [CE's OpenBao, per-tenant mount]
```
- **What runs where:** everything (controller, worker containers, credential broker, OpenBao) runs on CE infrastructure; the client's only footprint is the repo + the installed App + their own review/ratification.
- **Data residency:** client source code and CI artifacts transit and are cached on CE infra (worktrees, `.ce/state/`, container mounts).
- **Operational split:** CE owns 100% of the runtime; client owns ratification/review only.
- **Status today:** **not built.** No broker, container recipe, or OpenBao layout in this repo supports more than one tenant's App per standing service (§2.2). Model A is the model that most needs #419 (broker multi-tenancy) and #420 (per-tenant OpenBao mounts) [context tickets] before it is safe to sell.
- **When to choose it:** clients who want zero infra footprint and are comfortable with CE holding their App's JIT credentials and source bytes transiently. Best fit for small clients without their own DevOps capacity.

### Model B — client-hosted fleet, clean `ce` installs on client machines

**Trust boundary:**
```
[Client repo] <--App installation--> [Client-hosted CE fleet: clean `ce` install, client's own OpenBao/host]
```
- **What runs where:** everything on client infrastructure; CE ships only the installer artifacts (`docs/install.sh`, the signed `llms-install.md` spec — `docs/contracts/installer.md:48-83`) and playbooks.
- **Data residency:** 100% client-side. No client bytes or credentials ever reach CE infra.
- **Operational split:** client owns runtime + ops; CE owns product/governance-definition updates only (and must "govern rented-surface updates" — the update mechanism itself needs to be one governed path per the existing CE doctrine of not letting seats self-update toolchain).
- **Status today:** **the closest to already-working**, because the installer/onboard engine (`docs/contracts/installer.md`, `docs/operations/ONBOARD_APPLY_PROTOCOL.md`) is designed to run standalone on any host with no CE-infra dependency — it is literally what a solo pilot does today (`docs/guide/pilot-runbook.md`). The gap is fleet-seat tooling (`deploy/dgx-runsc/*`) being written *for CE's own DGX/VPS topology*, not packaged for a client host.
- **When to choose it:** regulated/security-sensitive clients who cannot let their code or App credentials leave their own perimeter, or clients large enough to run their own ops.

### Model C — hybrid (client humans + CE fleet capacity, distinct identities)

**Trust boundary:**
```
[Client repo] <--client's own App install (client controls click)-->
      |                                                    \
[Client human, own machine: install+onboard, review]   [CE controller host: drives client's App via
                                                          separately-custodied PEM/env, distinct
                                                          reviewer+bot identities]
```
- **What runs where:** the client self-serves install/onboard on their own machine (visible governance, Phase 1–2 of `playbooks/controller/runbooks/arad-pilot.md:36-68`); CE's controller then co-drives the *same repo's gate* using its own tenant-scoped App identity (Phase 3, `arad-pilot.md:70-142`).
- **Data residency:** split — client sees/holds the repo and their own machine's state; CE's controller host transiently holds the client's App PEM (today: `/dev/shm/mythos-ce-app.pem`, tmpfs) and drives PRs against the same repo.
- **Operational split:** client owns ratification (the "one irreducible Operator gesture," `arad-pilot.md:112-126`: a fresh `approver_ref`); CE owns the governed dispatch/review/merge mechanics.
- **Status today:** **this is exactly what Mythos is, verified live** (`docs/guide/first-value-mythos.md`, `playbooks/controller/runbooks/arad-pilot.md`) — [context: operator states "Mythos today = C," and the repo evidence fully corroborates it]. The distinct identities are real: reviewer `ubuntuaws745-cmyk` ≠ merging bot `mythos-ce[bot]` ≠ CE's own dev identities (`arad-pilot.md:128-131`).
- **When to choose it:** **recommended default for early clients.** It gets the client visible governance and ratification authority immediately (product credibility, matches "authority attaches to form" doctrine) while letting CE's existing fleet/dispatch machinery do the heavy lifting, without waiting on broker multi-tenancy (§7 G2/G3). This is also the cheapest model to instrument for the invoice-grade evidence bundle (§6), since CE's own controller already watches every run.

**Recommended default (Open Question 1, §9):** Model C for the first several clients; Model A only after #419/#420 close; Model B offered opt-in for clients that require it contractually, using the existing installer engine as-is.

---

## 4. `ce tenant` profile spec sketch

### 4.1 What already exists that a `ce tenant new` command would reuse verbatim

The install-answers schema already encodes almost the entire bootstrap sequence as data, minus the tenant-specific wrapping:

1. **Identities** — `github.app.kind: shared|own`, `app_id`/`client_id`/`pem` (SecretRef, tmpfs custody) already exist per-repo (`schemas/install-answers.schema.yaml:270-323`). Missing: a tenant-level wrapper that can hold *multiple* Apps (infra/adoption + user-seat + fleet-seats, per the operator's context) rather than the schema's current single `github.app` object.
2. **Mount** — no schema field today; new (§7 G1).
3. **Denylist** — no schema field today; new (§7 G7).
4. **Adoption** — the entire brownfield join-PR flow (`docs/contracts/brownfield-adoption.md`) already IS the "take an existing client repo under CE governance" mechanism, including the two-token read/write model (`docs/operations/ONBOARD_APPLY_PROTOCOL.md:74-80`) and the affirmatively-fail-closed secrets scrub (`docs/contracts/brownfield-adoption.md:144-168`) — this is production-grade and reusable as-is for onboarding a client's *existing* repo.
5. **Seats** — no tenant-scoped seat allocation exists; `deploy/dgx-runsc/*` and `tools/egress-broker/*` are CE's-own-fleet-shaped today (§2.2, §7 G8).
6. **Governance activation** — branch-protection reconciliation already exists and is idempotent/convergent (`docs/contracts/installer.md:169-176`, `docs/contracts/plain-join.md:47-58`).
7. **Run-mode ratification BY CLIENT** — the `ratification_binding` shape (`schemas/install-answers.schema.yaml:601-625`) is exactly the mechanism: `{ratified_prompt_sha, approver_ref, educate_acknowledged: true}`, already proven live for Mythos's own `MYTHOS_CE_APPROVER_REF` gesture (`playbooks/controller/runbooks/arad-pilot.md:118-126`). What's missing is applying this binding to CE's own *autonomy tiers* (docs-class automerge, Tier A/B) on the client's behalf, not just to the cost-opt-out/branch-protection-weakening cases it currently covers (§6).

### 4.2 Proposed bootstrap sequence for `ce tenant new`

```
identities → mount → denylist → adoption → seats → governance activation → run-mode ratification (CLIENT)
```

| Step | Automatable now? | Blocked on |
|---|---|---|
| identities (App registration, custody lane selection) | Partially — App registration is a manual GitHub click today for every model (`docs/contracts/installer.md:158-168`); custody-lane bookkeeping is new | G1 (tenant schema) |
| mount (OpenBao per-tenant mount + policy) | No live automation; template exists (`docs/devops/openbao/ce-dev-policy.hcl.tmpl`) | G3 (#420 [context]) |
| denylist (bidirectional per-tenant) | No — `public_docs_confidentiality.py` is CE-internal-only today | G7 |
| adoption (join-PR onto existing client repo) | **Yes, largely** — `docs/contracts/brownfield-adoption.md` is production-grade, gated behind `CE_FORGE_LIVE_FORGE=1` + `CE_FORGE_ADOPTION_WRITE=1` (`docs/operations/ONBOARD_APPLY_PROTOCOL.md:59-64`) | Nothing tenant-specific; works today for any target repo |
| seats (fleet allocation to the tenant) | No — broker/container config is single-repo (§2.2) | G8, G2 |
| governance activation (branch protection reconcile) | **Yes** — already convergent/idempotent | Nothing |
| run-mode ratification by client | Partially — the `ratification_binding` mechanism exists; it is not yet wired to CE's autonomy-tier defaults (§6) | New wiring, not a new primitive |

---

## 5. Confidentiality: bidirectional per-tenant denylist

### 5.1 What the fleet-guard SSOT actually does today

`validators/creator_engine_validator/public_docs_confidentiality.py` is real, tested, and structurally exactly the right *pattern* to generalize — but it currently enforces **one direction, for one tenant (CE itself)**:

- It forbids `ce-ops#\d+`, the private `ce-ops` repo URL, internal seat-login markers (`ce-dev-\d+`), internal tailnet/VPS/hosting identifiers, and the codename `skynet` from appearing in CE's own **public** `docs/**` + `README.md` (`public_docs_confidentiality.py:50-59`).
- It uses a **debt-ratchet allowlist** (`KNOWN_PENDING`, lines 78-109) that may only shrink — new leaks are blocked immediately, and it separately guards two internal-but-currently-public trees (`docs/operations/**`, `docs/delivery/**`) against **net-new files** via an exception ratchet (lines 111-198) — a strong, provable pattern for "this boundary can only get stricter over time."
- Two callers reuse the one rule (CI test + local `ce validate-pr` fast path) — the "ONE place the rule lives" design goal (module docstring, lines 14-20) is exactly right and should be preserved as the multi-tenant version is built.

**What it does not do:** there is no notion of "tenant A's confidential references must never appear in tenant B's docs, PR bodies, issue venue, or worker context, nor in CE's own public docs." Today CE has exactly one confidentiality direction (internal→public) and zero tenant-to-tenant walls.

### 5.2 Proposed generalization (NEW-TICKET-NEEDED, G7)

Extend the existing single-rule-module pattern to a **matrix**, not a rewrite:

- Keep `FORBIDDEN_PATTERNS` as CE's own permanent internal-to-public rule (unconditional, applies everywhere).
- Add a per-tenant `denylist_ref` (pointed to from the tenant manifest, §1.2) that supplies **additional forbidden patterns** scoped to: (a) that tenant's own docs/PR-venue (never leak *other* tenants' identifiers into it), and (b) CE's own surfaces (never leak *this* tenant's identifiers — repo name, App ids, reviewer login, internal client codenames — into CE's public docs or another tenant's venue).
- Reuse the debt-ratchet-allowlist mechanism verbatim per tenant (a tenant's own historical docs may need a shrink-only allowlist exactly like `KNOWN_PENDING`).
- The scan surface must expand beyond `README.md` + `docs/**` (which is CE-repo-specific) to whatever surface a given tenant's worker context can leak into: PR bodies, issue text, evidence bundles (§6), and worker prompt/scratch files if those are ever cross-tenant-visible (they should not be, per §2.3's mount-isolation recommendation, but the guard should not rely solely on that).

This is squarely a **new check**, not an extension of the existing one, because the existing one is keyed to CE's own fixed pattern list; a tenant-scoped version needs the pattern list itself to be **data** (per-tenant), which is a real design/schema change.

---

## 6. Authority & commercial seam

### 6.1 Client-as-Operator is already the load-bearing pattern for Mythos

The repo does not use the word "Operator" to mean "client" anywhere in its own contracts (CE's docs use "Operator" for CE's own human), but the **mechanism** the operator's framing describes is already live: `arad-pilot.md` explicitly separates the **pilot user** (self-serve install/onboard, sees governance) from the **Operator** (holds the ratification flip — "the only irreducible Operator gesture in the whole sequence is supplying the approver-ref," line 21) from the **Controller** (preps the host, watches venues, "never substitutes its own judgment for the Operator's ratification gesture," line 23). For Mythos, the *Operator role in that runbook is still filled by CE's own human* (the runbook is written from CE's controller's point of view) — the client (Arad) sits in the "pilot user" slot for install/onboard and is asked separately to ratify their own constitution (`tmp/arad-welcome-package/README.md:14-17`: "Your constitution to ratify... commit your ratified version into your own repo at `docs/constitution.md`").

This is an important nuance for the design: **today, the client ratifies their constitution/envelope as a document, but CE's own human still supplies the `approver_ref` gesture that gates the live PR run** (`arad-pilot.md:112-126`). For "client-as-Operator" to be structurally true (not just true-in-spirit), the `approver_ref`/ratification-binding gesture for a tenant's own repo needs to be generated and held by the **client's** identity, not CE's controller's. This is a concrete, checkable gap: nothing in `schemas/install-answers.schema.yaml`'s `ratification_binding` def ties `approver_ref` to a specific identity's provenance — it is "an opaque digest standing in for the ratifying human" (`schemas/install-answers.schema.yaml:614-618`), which is correct in shape but currently minted by whoever runs the script.

### 6.2 Delegation of the gate is a contractual act — evidence bundle as the deliverable

`docs/operations/PRESS_MERGE_BUNDLE.md` is the right shape for "invoice-grade per-PR client deliverable": it is explicitly evidence-only (`has_authority` is always `false`, line 17), deterministic and content-hashed, and already composes diff summary + test/CI rollup + review evidence + optional computer-use evidence into one structured object plus a rendered Markdown view (lines 36-56). **Status is honestly self-described as "proposed runtime and proposed schema, not frozen"** (line 3) — this is real, not yet ratified, work — matching the operator's context that ce-ops#294 is "design, ratified, build in flight" [context].

For the commercial seam, the press-merge bundle needs three additions beyond what exists:
1. A tenant-scoped rendering that never leaks CE-internal references (composes with §5's denylist).
2. A durable per-tenant archive (today it's PR-keyed and ephemeral; a client deliverable needs a retained, listable history).
3. Explicit non-authority language already present (line 17) should be preserved verbatim in client-facing renderings — it is the correct "grader lives outside the agent" framing and must not be softened into anything that reads like CE self-certifying its own work.

### 6.3 What CE's internal autonomy tiers mean tenant-side

CE's own docs-class automerge and Tier A/B autonomy decisions (memory: `ce-l2-automerge-golive-decision`) are **CE's own internal operating decisions about CE's own repo** — nothing in this repo's schemas ties them to a client repo's posture, and they must not silently apply to a client's repo. The existing `ratification_binding` mechanism (governance-weakening requires ratified-human-only binding, "an agent preparing an answers file can configure anything except a weaker grader" — `schemas/install-answers.schema.yaml:44-46`) is the correct template: **a tenant's default posture must ship maximally conservative (all autonomy tiers off, human-gated review required), and the client must explicitly ratify any autonomy tier beyond that, using the same educate-first, ratified-human-only binding shape CE already uses for its own cost opt-out** (`docs/contracts/installer.md:376-394`).

---

## 7. Gap register

Legend: **verified** = confirmed gap by reading the code/config in this repo. **[context]** = operator-supplied ticket reference not independently checkable here (ce-ops is a private tracker not present in this repo).

| ID | Gap | Evidence | Ticket | Size |
|---|---|---|---|---|
| G1 | No `tenant-record` schema/kind/validator exists | Verified: no `tenant` hits outside review worktrees; no schema file | NEW-TICKET-NEEDED | S |
| G2 | Mint-broker config is single-App-per-process; no per-tenant/per-installation routing | Verified: `tools/mint-broker/mint_broker/config.py:45-56` (`MintBrokerConfig` has exactly one `app_client_id`/`pem_path`) | ce-ops#419 [context] | M |
| G3 | No per-tenant OpenBao mount automation; only per-dev path-prefix template exists | Verified: `docs/devops/openbao/ce-dev-policy.hcl.tmpl` is dev-scoped only; no tenant analog | ce-ops#420 [context] | M |
| G4 | No `ce tenant new` / FleetIaC profile; `profile` enum is `[solo-pilot, team]` only | Verified: `schemas/install-answers.schema.yaml:65-72` | ce-ops#377/#378 [context] | L |
| G5 | No contained-controller substrate (needed so a per-tenant orchestrator can itself be sandboxed) | [context] — not directly evidenced in this repo scan | ce-ops#408 [context] | L |
| G6 | Conveyor arming blockers (fleet dispatch pipeline not fully armed) | [context] | ce-ops#410 [context] | M |
| G7 | Confidentiality denylist is unidirectional (CE-internal→CE-public) and single-tenant | Verified: `validators/creator_engine_validator/public_docs_confidentiality.py:1-30,50-59` | NEW-TICKET-NEEDED | M |
| G8 | Egress/self-push broker config hardcodes one repo (`creator-engine/creator-engine`) at the top level; seats are CE's-own-dev-shaped, not tenant-repo-shaped | Verified: `tools/egress-broker/apps.example.json:4-6,33-66` | NEW-TICKET-NEEDED | S–M |
| G9 | Press-merge bundle is proposed, not frozen; no tenant-facing rendering, retention, or denylist composition | Verified: `docs/operations/PRESS_MERGE_BUNDLE.md:3` ("Status: proposed... not frozen") | ce-ops#294 [context] (design ratified; build in flight per operator) | S |
| G10 | `architect_research` egress lane for live web research is declared but not yet enabled at runtime (relevant to tenant-scoped research workers too) | Verified: `docs/operations/WORKER_CONTAINER_PROTOCOL.md:326-334` | NEW-TICKET-NEEDED (or fold into existing PCO slice) | S |
| G11 | Reviewer-authority envelope minting is manual/out-of-band; no in-launcher minting yet (relevant once multiple tenants need parallel reviewer dispatch) | Verified: `docs/operations/REVIEWER_VENUE_AUTHORITY.md:79-84` ("Out of scope of this gate... In-launcher minting") | NEW-TICKET-NEEDED | M |
| G12 | Client-side `approver_ref` provenance is not distinguished from CE-controller-side provenance — the ratification gesture for a client repo is still generated by whoever runs the script, not verifiably by the client's own identity | Verified: `schemas/install-answers.schema.yaml:614-618`; `playbooks/controller/runbooks/arad-pilot.md:112-126` shows CE's controller-adjacent flow generating the gesture today | NEW-TICKET-NEEDED | S |

---

## 8. Phased plan

### Phase 1 — Mythos reference deployment completion
**DoD:**
- Mythos App private key migrated off tmpfs-plus-host-env-file custody into an OpenBao mount dedicated to Mythos (reusing the `ce-dev-policy.hcl.tmpl` pattern, scoped as `ce-kv-tenant-mythos` per §2.3's recommendation, not a path prefix in the shared `ce-kv` mount).
- A hand-authored tenant manifest for Mythos (§1.2 shape) checked into a governance-appropriate location, even before G1's schema is ratified — this de-risks G1 by proving the shape against a real tenant before it's frozen.
- `scripts/first-value.sh` / `arad-pilot.md`'s runbook re-runs with zero manual credential placement beyond the initial OpenBao seed (i.e., no more `/dev/shm/mythos-ce-app.pem` placement step per session).
- Confirm the client-ratification gesture (`MYTHOS_CE_APPROVER_REF`) is generated and held by an identity distinguishable from CE's own controller identity (closes G12 for Mythos specifically, ahead of the general fix).

### Phase 2 — First fleet seat on Mythos (smallest real client-skynet)
**DoD:**
- One worker/fleet seat container (reusing `deploy/dgx-runsc/` recipe shape) launched against `chmod735-dor/mythos` instead of `creator-engine/creator-engine`, using the Mythos tenant's own OpenBao mount and App identity.
- Egress/self-push broker config extended (minimally: a second broker config file scoped to Mythos, closing G8's worst instance without waiting for the full schema fix) so the seat can publish its own signed commits against the client repo under the same fail-closed policy CE uses on itself.
- Dispatch/harvest playbooks (`playbooks/controller/briefs/*.md`) pointed at the Mythos tenant's issue venue (the client repo itself, per §1.2's `issue_venue`).
- At least one governed PR authored, reviewed (distinct reviewer venue), and merged by this seat with zero manual credential handling beyond what Phase 1 established.

### Phase 3 — Tenant profile productization (`ce tenant new` / FleetIaC profile)
**DoD:**
- G1 (tenant schema/validator), G2 (broker multi-tenancy), G3 (per-tenant OpenBao mount automation), and G7 (bidirectional denylist) shipped and covered by tests, mirroring the rigor of the existing `worker-container-policy`/`container-instance` predicate pair (schema check + cross-record check + forbidden-mount-class check).
- `ce tenant new <tenant-id>` runs the full bootstrap sequence (§4.2) end-to-end for a *synthetic* second tenant (a throwaway test repo) with no controller improvisation.
- Press-merge bundle (G9) frozen as a ratified schema and wired to per-tenant retention + denylist composition.

### Phase 4 — Second real client validates
**DoD:**
- A genuinely new client's repo onboarded entirely through the Phase 3 `ce tenant new` path, with the client filling the Operator role for real (their own `approver_ref` provenance, their own ratified constitution/envelope, their own autonomy-tier opt-ins per §6.3).
- Client receives at least one press-merge evidence bundle as a real deliverable.
- Any manual step CE's controller had to perform outside the productized path is logged as a new gap, not silently absorbed — this closes the sequencing loop honestly (the point of a second client is to prove the productization, not to prove CE can still hand-hold).

---

## 9. Open questions for Operator ratification

1. **Which deployment model is the default for new clients?**
   Recommended default: **Model C (hybrid)**, matching Mythos's proven live pattern, until #419/#420-class work lands. Model A deferred; Model B offered opt-in.

2. **What is the default App-auth custody lane per tenant?**
   Recommended default: **shared+broker lane** per the operator's stated doctrine [context] — but flag the live discrepancy: **Mythos today is de facto running in an `own`-shaped custody pattern** (a dedicated App, PEM held on the controller host, not minted through any standing shared broker). If shared+broker is truly meant to be the default, Phase 1 should also migrate Mythos's mint path onto the broker (once G2 exists) rather than leaving the reference deployment as a permanent `own`-lane outlier.

3. **Tenant OpenBao mount topology: dedicated mount per tenant, or path-prefix in a shared mount?**
   Recommended default: **dedicated mount per tenant** (`ce-kv-tenant-<id>`), a deliberate strengthening over the existing per-dev path-prefix pattern, because a mount boundary is enforced at OpenBao's ACL root rather than by policy-glob correctness.

4. **Where does tenant work get filed — the client's own repo issues, or a CE-side venue?**
   Recommended default: **the tenant's own repo/venue** (already the live Mythos pattern via first-value Scopes) — never `ce-ops`, to keep the confidentiality boundary (§5) structurally simple: CE-internal tracker stays CE-internal-only.

5. **Who ratifies a tenant's autonomy-tier defaults (docs-class automerge, Tier A/B)?**
   Recommended default: **ship every new tenant with all autonomy tiers off** (human-gated review required for everything), requiring the client's explicit ratified opt-in per tier, using the same educate-first / ratified-human-only binding shape CE already uses for its own cost opt-out (`schemas/install-answers.schema.yaml` `ratification_binding`).

6. **Sequencing: strict service-first, or parallelize a second client sooner?**
   Recommended default: **strict Phase 1→4 sequencing** per the operator's stated doctrine [context] — do not onboard a second client before Phase 3's productization DoD is met, to avoid hand-authoring two bespoke integrations in parallel and silently duplicating Mythos's manual-step debt.

---

## Sources consulted (repository paths)

- `docs/contracts/installer.md`
- `docs/contracts/brownfield-adoption.md`
- `docs/contracts/plain-join.md`
- `docs/contracts/seat-class-policy.md`
- `docs/contracts/forge-persona-catalog.md`
- `docs/operations/ONBOARD_APPLY_PROTOCOL.md`
- `docs/operations/WORKER_CONTAINER_PROTOCOL.md`
- `docs/operations/REVIEWER_VENUE_AUTHORITY.md`
- `docs/operations/PRESS_MERGE_BUNDLE.md`
- `docs/guide/pilot-runbook.md`
- `docs/guide/first-value-mythos.md`
- `docs/decisions/ADR-0011-devops-privileged-action-broker.md`
- `docs/devops/openbao/openbao-secret-path-map.tsv`
- `docs/devops/openbao/ce-dev-policy.hcl.tmpl`
- `schemas/install-answers.schema.yaml`
- `validators/creator_engine_validator/onboard_apply_live.py`
- `validators/creator_engine_validator/public_docs_confidentiality.py`
- `tools/mint-broker/mint_broker/{service,config,binding}.py`
- `tools/egress-broker/{README.md,apps.example.json}`
- `deploy/dgx-runsc/{Dockerfile,README.md}`
- `surfaces/manifest.yaml`
- `playbooks/controller/runbooks/arad-pilot.md`
- `playbooks/controller/briefs/*.md`
- `tmp/arad-welcome-package/README.md`

## Risks and uncertainties not resolved by this research

- Ticket numbers #419, #420, #377, #378, #408, #410, #294 could not be independently verified (ce-ops is a private tracker outside this repo's scope) — all treated as [context] per the operator's framing; the controller should confirm these against the live ce-ops tracker before citing them as authoritative in the filed doc.
- The numeric GitHub App ids for `mythos-ce` (4103119), `mythos-arad` (4159494), and `mythos-agents` cited in the operator's framing were not independently confirmed in this repo (only the installation id `141552951` and env-var naming convention were verified via `arad-pilot.md`). The controller should verify these against the live App registrations before publishing.
- This research did not probe live OpenBao, mint-broker, or egress-broker runtime state (read-only worker; no credentials, no host access) — all findings are static-code/doc-grounded, not live-config-grounded. A `verification`-role or `ops_triage`-role worker with appropriate read access should confirm the live broker/OpenBao topology before Phase 1 work begins.

---
CONTROLLER ADDENDUM 2026-07-03: App ids mythos-ce=4103119 and mythos-arad=4159494 WERE independently verified live this morning via App-JWT authentication (controller session); mythos-arad installation = 142925881. Ticket numbers #419/#420/#377/#378/#408/#410 confirmed against live ce-ops by the controller.
