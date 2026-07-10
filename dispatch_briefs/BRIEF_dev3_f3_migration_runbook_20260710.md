# DISPATCH — dev-3 — 2026-07-10 — unit F-3: controller-migration completeness runbook + snapshot manifest codification
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-f3-migration-runbook <full-40-hex-sha>`
or `BLOCKED ce-f3-migration-runbook <one-line-reason>`.
Branch `ce-f3-migration-runbook` off freshly fetched origin/main; worktree /var/tmp/wt-ce-f3-migration-runbook.
SUITE POLICY: focused tests ONLY (in-seat full suites remain suspended); commit before signalling.

## Context (embedded — arc item F-3 from the ratified incident design)
The 2026-07-09 emergency controller migration (host A → host B) was executed manually and
left four discovered gaps. This unit codifies the migration as a governed runbook and closes
the one code gap.

## Deliverable 1 — runbook `docs/operations/CONTROLLER_MIGRATION_COMPLETENESS.md` (NEW)
A checklist-form runbook where every item carries an acceptance-evidence line ("verified by
<command/observable>"). Sections, from the live incident:
(a) **Agent role definitions travel**: `.claude/agents/` role files are not git-tracked; they
    must be included in the controller state snapshot (see Deliverable 2) and restored on the
    new host before any worker dispatch. Evidence: role files present + a worker spawn resolves.
(b) **Memory sync**: controller memory directory + its index travel; index host-topology
    header MUST be rewritten for the new host before first autonomous act; peers may append
    artifacts but never rewrite the executor's live index (multi-controller artifact rule).
(c) **Credentials matrix**: secrets NEVER travel in bundles; enumerate what the Operator
    provisions on the new host (auth env, per-identity tokens, signing key + passphrase,
    inter-host ssh keys) vs what regenerates (harness auth, npm/pip toolchains).
(d) **Session infra recreate-list**: crons, watchers, monitors die with the old session —
    enumerate + recreate; acting infra must be systemd/IaC, not session-owned.
(e) **Gate topology as declared state**: the merge-gate service placement (which host holds
    the singleton), its drop-ins (host-network), AND the host firewall rule allowing the
    gate's container subnet to reach the local secrets backend (currently the UFW allow
    172.17.0.0/16 → port 8200/tcp rule — presently undeclared local knowledge) — all belong
    in the deployment declaration, with the old host's unit disabled as the singleton proof.
Write for the PRODUCT lens: generic host-A/host-B names in prose, zero internal ticket refs;
the concrete evidence lines may reference repo paths and service names.

## Deliverable 2 — snapshot manifest codification (code)
`tools/controller/state_sync.py`: add a `claude_agents` data class that includes
`.claude/agents/*.md` in the snapshot tree (mirroring how existing data classes collect
paths; respect the existing secret-denylist plumbing). Extend
`validators/tests/unit/test_controller_state_sync.py` with: agents dir present → included in
manifest + tree; absent → clean skip (no error). Keep the tool's existing behavior byte-stable
otherwise (extend-don't-weaken).

## Files (allowed writes)
docs/operations/CONTROLLER_MIGRATION_COMPLETENESS.md (NEW), tools/controller/state_sync.py,
validators/tests/unit/test_controller_state_sync.py, .ce/changelog/ce-f3-migration-runbook.md,
carrier .ce/pr-manifests/ce-f3-migration-runbook.md (slug=branch) containing exactly:
`- **Declared work class:** S`

## Stop lines
install.sh, docs/llms-install.md, ce_cli.py, v3_cli.py, launch_runtime.py, seat_reaper.py,
doctor_runtime.py, ticket_reconcile.py, checks/**, pr_preflight.py, forge/**, deploy/**,
.github/**, .ce/brain/assertions.yaml, other docs/operations/* files.
