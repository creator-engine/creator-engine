# Fleet IaC Deployment — Research Report (condensed) — 2026-06-30
**Opus architect_research, read-only.** Full transcript: agent aa89ab4b1c0ca8812. Brief: `.ce/briefs/fleet-deployment-iac-research.md`. Locked: fresh isolated VM/project · product-aware/internal-first · tiered (one path, knob).

## HEADLINE: CE already has ~70%
- `deploy/*/run-*-runsc.sh` = a working **env-parameterized fleet provisioner** (~30 `CE_DGX_*` knobs: image/runtime/repo/seat-user/uid/container/egress-socket/ledger/reviewer-ref/restart). Biggest reuse win.
- `cev3 onboard --apply` (`onboard_apply.py` `GREENFIELD_LEG_IDS`, 12 legs) already does repo-create + App-install + workflow-install + branch-protection + workspace-checkout + first-project-smoke = **the per-project forge bootstrap**.
- `surfaces/render.py` = already IaC-adjacent (manifest→build-args/env; treats OpenBao/gVisor/gvproxy as `host-only` = the "provision-once-per-VM" set).
- `launch_runtime.py` (`ce launch`) = canonical fail-closed seat spawn (backend select, resource bound, brain bootstrap). `v3_installer.py` reconcilers = idempotent fail-closed re-run. Signed install.sh (`PINNED_KEYS`, SSHSIG verify-before-execute) = the trust anchor.

## NET-NEW (build) — only 4 things
1. **Fleet manifest** (per-project YAML, schema-sibling of surfaces/manifest.yaml + identity-registry.schema.yaml): project/tier/cloud/isolation_backend/forge/seats/secrets(pointers-only)/brain/egress/daemons.
2. **Cloud-VM provisioning wrapper**: cloud-init (in-VM substrate) + thin Terraform module (VM/network/firewall/cloud-KMS). NOT a rewrite — thin IaC shell over existing `deploy/` + `cev3 onboard` executors.
3. **Per-project secret/identity bootstrap** = THE LONG-POLE. OpenBao-per-VM + cloud-KMS auto-unseal + per-seat PAT minting + the C2 credential-transport deputy. **Blocked on ce-ops#239** (controller credential transport stubbed; `ce-controller-gh-guard` fails closed until C2 ready) + intertwined ce-ops#240 (C1-C4).
4. **`ce fleet` CLI verb** (thin wrapper: provision→install→render→bootstrap→launch→verify).

## IaC TECH (2026-grounded): cloud-init + thin Terraform over existing executors
Terraform owns only outer cloud resources (VM/net/KMS); cloud-init runs once-per-VM substrate; existing deploy/ + cev3 onboard + ce launch do everything inside. Reject K8s (Team-tier overkill for 1-VM-solo) + Nix (digest-pinned manifest already gives reproducibility). OpenBao **cloud-KMS auto-unseal** is what makes secret bootstrap near-one-click. Pulumi Automation-API = optional spike for programmatic N-VM.

## ISOLATION (zero CE-vs-other-project mixing) — physical VM primary + 4 layered guarantees
(a) physical VM separation (CE-internal stays on DGX/Hetzner; fleets never run there); (b) fail-closed `ce-controller-gh-guard` (does NOTHING without project-scoped injected cred); (c) immutable-identity reconcilers (`plan_app_config_reconcile` refuses to repoint app_id/installation_id); (d) **a CI guard on the fleet-manifest schema rejecting CE-internal identifiers** (creator-engine/ce-ops) = cheapest strongest mixing-prevention. Separate org/App/PATs/OpenBao/state/brain/crons per project.

## IRREDUCIBLE HUMAN GESTURES (~2-3/deploy): cloud auth · GitHub App install consent · identity-registry/KMS approval. Everything else automatable (mirror R5 emit-bytes→ratify). "One-click-minus-consent."

## TIER KNOB (reuses existing BACKEND_DEPS/PROFILE_DEFAULT_BACKEND)
- **Solo+CEO (lean):** workers.count 0; 1 contained controller; os-native (no sudo, Tier1); file/single-OpenBao KMS-unseal; NO daemons/crons; brain OFF. 1 small VM.
- **Autonomous Fleet:** controller + N codex seats (ce-codex-seat@); gvisor-proxy/openshell; OpenBao per-seat paths; belt+integrator+review-pickup daemons + crons; brain optional. Larger/GPU VM + N× model spend.

## PRODUCT FRAMING
Operationalizes the ratified Solo/Team/Autonomous-Fleet tiers; same artifact serves internal-other-projects AND the NVIDIA pitch (each fleet = containerized CE + real usage → "live users + usage data" pillar). Forcing function to mature OpenShell #82. Ship: schema/provisioner/signed-install/tier-knob/isolation. Keep internal: CE identity-registry values, DGX/Hetzner specifics, GPU/brain topology, ce-ops refs.

## ROADMAP (bounded)
- **P0 (FIRST, small, net-new):** fleet-manifest schema + validator + **CI guard rejecting CE-internal identifiers** (load-bearing isolation guarantee). Decision-independent — buildable now.
- **P1:** `ce fleet render` (extend surfaces/render.py) → env files + scoped identity-registry.
- **P2:** Solo-tier provisioner on one cloud VM → first-project-smoke green = first e2e proof.
- **P3 (LONG-POLE, blocked ce-ops#239/#240):** per-project secret/identity bootstrap + C2 transport.
- **P4:** Fleet-tier (templated deploy/systemd units + crons).
- **P5:** Terraform module + AWS/GCP; optional Pulumi N-VM spike.
- **P6:** rented-surface sync (`ce fleet update` re-pulls signed artifact; never in-fleet self-update — ties to ce-ops#114).

## RISKS
1. Cost — N VMs + N× model spend (mitigate: Solo default, spend-envelope, resource_bound). 2. Secret bootstrap = long-pole (ce-ops#239). 3. GitHub-App shared-vs-own multi-tenant (rec own-App for isolation; shared for demo). 4. **Self-referential rented-surface sync** — each fleet is a rented surface of CE that fossilizes without governed update (ce-ops#114 lesson). 5. Isolation regression (mitigate: P0 CI guard + fail-closed guard). 6. Substrate portability (cloud kernel/arch vs DGX/VPS; pin per-arch images).

## OPERATOR DECISIONS SURFACED
(a) shared-App vs per-project-App (rec: own-App for isolation; shared for demo). (b) per-fleet model account vs shared pool (sharing reintroduces cross-project coupling — partly defeats isolation). (c) default tier for first external deployment (rec: Solo+CEO, os-native).

## FOLLOW-UP: tooled-confirm current state of ce-ops#239/#240/#82/#207/#208/#114 before P3 (architect had no gh).
