# Fleet-IaC P1 — provisioning framing (Operator-ratified decisions, 2026-06-30)

Canonical inputs for the Fleet-IaC P1 (cloud-VM provisioning wrapper) brief. Derived from the 3 Operator decisions + the 4-axis mode canon ([[ce-mode-axes-canon]]). This is FRAMING — the implementation brief is authored from it.

## What Fleet-IaC provisions: a governed AGENT (not "a fleet")
The unit of provisioning is **one CE governed agent**, mirroring what the existing fleet already does per seat.

### Decision 1 — GitHub App identity = PER GOVERNED AGENT (not per fleet)
Each provisioned governed agent gets its **own App set**, exactly like the live fleet:
- a controller App `ce-forge-<name>` (the agent's automation/runtime identity), plus
- the role Apps it needs (`ce-forge-devops`, `ce-forge-reviewr`).
NOT one shared App per fleet. The shared slug-`creator-engine` App is only the self-serve ONBOARDING vehicle (`creator-engine[bot]`) — never a provisioned agent's runtime identity ([[ce-shared-app-published]], [[ce-github-identity-model]]). New contributor example: Nitzan → her own `ce-forge-Nitzan` App.

### Decision 2 — Model account = BYO subscription per external principal
External principals bring their **own model subscription** (Arad + Nitzan are on their own **Claude Code** subscriptions). Fleet-IaC must NOT wire an external agent onto our shared weekly codex pool — that pool is **internal-fleet-only** ([[ce-codex-shared-account-subscription]], [[ce-no-anthropic-sdk-per-token-billing]]). Provisioning surfaces a "point at your subscription" step; default for external = BYO.

### Decision 3 — Tier vs Collaboration are TWO orthogonal config axes (not one "tier" dropdown)
Old Solo/Team/Fleet was a flattened 2×2. Fleet-IaC must expose them separately:
- **Tier** (how many coordinated governed agents under one orchestration domain): **Solo** (one agent — the DEFAULT) / **Autonomous Fleet** (many, orchestrated — internal/opt-in). The governed daemons (egress broker / merge-queue-gate / integrator / review-pickup) provision **ONLY at Autonomous-Fleet tier** — a Solo provision runs none of them.
- **Collaboration** (repo sharing): **Individual** (own repo) / **Team** (shared repo with other CE principals). Orthogonal to Tier — a Solo-tier agent can be Individual or Team. This is the dimension the old "Team deployment" actually named.

**Provisioning defaults:** Tier=**Solo**, Collaboration=**Individual** (override to Team at config), BYO model subscription, per-agent `ce-forge-<name>` App set minted. Autonomous-Fleet tier (+ daemons) is the internal/advanced path, not the external default.

## Carries forward
- ce-ops#369 (denylist from SSOT identity-registry) is the guard-hardening dependency; orthogonal to these 3 decisions (ungated).
- Secret custody for minted per-agent App PEMs → OpenBao/broker path ([[ce-per-dev-identity-secret-storage]] #113), not host-local at scale.
