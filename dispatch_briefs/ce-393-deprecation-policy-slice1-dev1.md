# SEED BRIEF — ce-ops#393 Slice 1: command-deprecation policy doc (dev-1)

- **Ticket**: ce-ops#393 — "Command-surface reduction gate: deprecation policy +
  CI gate so the ~40-command v1 surface shrinks by mechanism, not wish"
  (filed off the external technical review's command-surface finding).
- **This slice**: the POLICY DOC + machine-readable deprecation manifest ONLY.
  The CI gate is Slice 2 (separate PR later — do NOT build the check now; the
  check registry file `checks/__init__.py` has two in-flight claims and is
  off-limits this slice).
- **Role**: implementer. **Branch**: `ce-393-command-deprecation-policy` off
  fresh `origin/main`. **Declared work class**: S.

## Deliverable

1. `docs/contracts/command-deprecation-policy.md` (new) — a public,
   product-lens contract doc (NO ce-ops# refs, no internal fleet/seat names)
   codifying:
   - The v1 command surface is a governed, shrinking surface: net-new
     top-level commands require explicit ratification; removals ride the
     deprecation lifecycle.
   - Lifecycle stages: `announced` → `deprecated` (command warns on use,
     points at replacement) → `removed` (next minor after a stated floor,
     e.g. one minor version or 30 days, pick and state one) — with the stage
     recorded in the manifest, not prose.
   - The manifest is the SSOT; docs and `ce --help` surfaces must agree with
     it (enforced by the Slice-2 CI gate; the doc may say "a CI gate enforces
     this contract" without naming internal tickets).
2. `docs/contracts/command-deprecation.yaml` (new) — machine-readable manifest:
   `kind`, `schema_version: "1"`, `surface_budget: <current top-level command
   count on main — count it, don't guess>`, and an empty (or seeded, if any
   command is already informally deprecated — check `ce --help` + docs)
   `deprecations:` list with per-entry `command`, `stage`, `replacement`,
   `announced_in`.
3. `.ce/changelog/ce-393-command-deprecation-policy.md` + carrier
   `.ce/pr-manifests/ce-393-command-deprecation-policy.md` (regen via
   `carrier_gen.write_carriers(base="origin/main")`, never hand-list).

## Allowed paths (EXACTLY; anything else → STOP and report)
- docs/contracts/command-deprecation-policy.md (new)
- docs/contracts/command-deprecation.yaml (new)
- .ce/changelog/ce-393-command-deprecation-policy.md (new)
- .ce/pr-manifests/ce-393-command-deprecation-policy.md (new)

⚠️ GOTCHA [new-ce-group docs coupling]: you are NOT adding a CLI group, so
test_v1_docs_reconciliation should be untouched — but if any docs-reconciliation
test trips on the new contract doc, fix by following the test's own convention,
and if that requires a file outside the allowed list, STOP and report instead.

⚠️ NOTE: a doctrine-coverage ratchet for docs/contracts/** is in flight on
another seat (new manifest `.ce/brain/doctrine-coverage.yaml`). It is NOT on
main yet, so your preflight will not see it. Your new contract doc may need a
coverage entry later — the controller handles that at merge sequencing; do not
touch `.ce/brain/`.

## Standing preflight directive (ce-ops#303)
FULL `ce validate-pr` (CI-parity, TMPDIR=/var/tmp if host /tmp has the .git
trap) GREEN in ONE pass before push. Do not discover gates via CI.

## Evidence + delivery (you self-push)
1. Verbatim GREEN preflight tail.
2. The counted current top-level command surface number + how you counted it.
3. Push branch, open PR with body carrying exactly one
   `- **Declared work class:** S` line and `Refs: creator-engine/ce-ops#393`.
4. Done-report with PR number + head SHA.

## Stop line
No CI gate/check code this slice. No edits to validators/**, .github/**,
.ce/brain/**. You do not approve/merge — the controller gates.
