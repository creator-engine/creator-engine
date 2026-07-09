# Contract: v3 Naming Hygiene + Neutral Local-State Convention (G-4.1)

**Status:** Canonical. Enforced by the `v3_naming_hygiene` check.

## Purpose

CE terminology must stay **decoupled from implementation** in the v3 / v3.1
surface. CE was bootstrapped on a forked upstream harness named "Hermes"; its
local-state directory `.hermes/` was inherited as CE's instance-local state root
and then frozen into the v1 substrate. That is **naming-decoupling debt**: the
*function* (one gitignored local-state root) is by design, but the *name* is
residue from one harness.

**Disposition (split by version):**

- **v1 keeps `.hermes/`** — frozen, retained for coexistence. Renaming it churns
  the live v1 substrate; deferred (see "Deferred", below).
- **v3 / v3.1 no longer hard-require `.hermes/` for user-facing state** — the
  active v3 state root is `.ce/state`; ce-hermes-retirement completes the
  user-facing retirement of the inherited local-state precondition while leaving
  v1 coexistence intact.
- **v3 / v3.1 must NOT inherit the residue** — neither a `.hermes/` local-state
  hard requirement nor the CE bootstrapping-harness names in its code/schema surface. This is
  enforced **by machine, not by chance**: green on day one (the v3 surface is
  clean) and ratcheting.

## The guard — `v3_naming_hygiene`

A self/structural fitness-function check (sibling to `version_boundary`). It
scans, against the `creator_engine_validator._versions` taxonomy:

- the **v3 CODE surface** — every module with `classify(...) == "v3"`; and
- the **v3 SCHEMA surface** — every file declared in `_versions.V3_SCHEMAS`
  (currently `schemas/runtime-policy.schema.yaml`,
  `schemas/runtime-evidence.schema.yaml`).

**Forbidden residue tokens** (case-insensitive): `.hermes`, `Hermes`,
`Nefarious` — the CE bootstrapping-harness residue. A new occurrence in the v3
surface **fails** the check (`VAL-V3NAME-RESIDUE`).

**Ratchet floor:** a justified exception is a baselined `(file, token)` entry in
`_versions.BASELINE_V3_NAMING_ALLOWLIST` (the allowlist **only shrinks**; it is
**empty** on day one — the v3 surface is clean). A stale entry warns
(`VAL-V3NAME-STALE-ALLOW`). A declared `V3_SCHEMAS` file that no longer exists
errors (`VAL-V3NAME-MISSING-SCHEMA`).

**Explicitly NOT forbidden — legitimate transport/runtime adapter names.**
`Claude`, `Codex`, `gVisor`, `ACP`, `OpenShell` are correct impl-named *adapters*
(e.g. `runner.cc_hook_adapter`, `runner.gvisor_proxy_backend`); impl-named
adapters are correct. The residue token-set is precisely the CE bootstrapping
harness, nothing else.

**Scope exclusions** (the check does NOT scan these):

- **v3 docs** — historical/research documents may legitimately point to archived
  `.hermes/research/` provenance; current user-facing functional docs must use
  `.ce/state`;
- the **v1 / shared** surface — v1 checks legitimately validate v1's `.hermes/`
  layout;
- the **grandfathered legacy corpus** (`specs/001`/`002` + the docs mirroring
  them).

**Scoped exception to the v1 exclusion:** the load-bearing user-facing surfaces
now default to `_versions.V3_LOCAL_STATE_ROOT` (`.ce/state`) for governed state.
The ce-hermes-retirement change completes this cleanup for onboarding, deployed
runsc defaults, hook evidence roots, and current functional docs. This does not
authorize a full v1 rename; templates, schemas, and v1-only surfaces remain under
the deferred v1 freeze until a separate ratified migration.

## Neutral v3 local-state convention

All v3 / v3.1 instance-local state writes go under the neutral, CE-namespaced
root `creator_engine_validator._versions.V3_LOCAL_STATE_ROOT` = **`.ce/state`**:

- **NEVER `.hermes/`** — that is the v1 bootstrapping-harness residue (kept frozen
  for v1 only).
- **NEVER `.claude/`** — that is Claude Code's own tool dir (hooks/settings/
  skills); using it would re-bind CE state to one harness — the same mistake.

The v3 sink/driver are already path-neutral (`evidence_sink(root)` /
`make_run_driver(root)` take the write-root as a parameter), so this is a wiring
choice — no orchestrator change. The v3 work-driving CLI / seat-launch (G-7)
wires production local state under this root.

## Standing requirement on the v3.1 planning prompts

Every v3.1 planning/execution prompt (**G-5 … G-7**) MUST cite (1) this
naming-hygiene guard and (2) the neutral local-state convention, so no future
gate reintroduces `.hermes/` or a bootstrapping-harness name into the v3 surface,
or wires v3 local state under `.hermes/`.

## Deferred (NOT this contract's concern)

The full **legacy-terminology-corpus migration** (`specs/001`/`002` + the docs
mirroring them: `Source`/`Hermes` → Operator/Controller) and any rename of
v1-frozen `.hermes/` templates/schema constants migrate grandfathered legacy and
touch the live v1 substrate. They belong together in ONE separate, post-pilot,
ratifiable terminology/naming-migration gate.

See also: `docs/architecture/agent-interaction-model.md` (current-terminology
note), `creator_engine_validator/checks/version_boundary.py` (the sibling v1⊥v3
boundary guard).
