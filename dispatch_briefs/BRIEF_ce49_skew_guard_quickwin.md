# BRIEF — ce-49-skew-guard-quickwin — stale-wheel skew guard in `ce` (QUEUED UNIT 2)

Role: implementer (dev-1, self-push, foreman mode). This is your SECOND unit — start it
immediately after your ce-446 PR is opened (do not wait for its merge; territory is disjoint).
Branch: `ce-49-skew-guard-quickwin` off freshly-fetched origin/main.

## Mandate
Read ce-ops#49 and its 2026-07-05 controller comment (three false-RED incidents). Implement the
QUICK-WIN tactical guard (not the full fleet-coherence epic): when `ce` runs from an installed
wheel INSIDE a repo checkout whose validators source is NEWER than the running package, the stale
wheel silently produces wrong gate verdicts. Deliver:
1. Detection: on startup, if cwd (or --repo-root target) is a creator-engine checkout, compare the
   checkout's declared validators version (validators/pyproject.toml or the package version file)
   against the running package's version. Newer-source-than-wheel = SKEW.
2. Behavior on SKEW: for gate-relevant subcommands (`validate-pr`, `brain verify`, `brain
   correct`, `brain sync`) REFUSE fail-closed with a clear message naming both versions and the
   main-vintage escape: run `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli
   <cmd>`, or set `CE_ALLOW_STALE_WHEEL=1` to proceed anyway (explicit, logged). For all other
   subcommands: one prominent stderr warning, proceed.
3. Zero behavior change when versions match, when not in a checkout, or when running from source
   (module invocation must detect itself as source-vintage and never refuse).
4. Behavioral tests for: skew+gate-command → refusal + message; skew+escape-hatch → proceeds;
   skew+non-gate command → warns+proceeds; no-skew → silent; running-from-source → silent.

## Semantic novelty check FIRST
Verify no equivalent guard already exists on main (grep ce_cli for version/skew/stale checks and
check `ce doctor` if present). Found equivalent → `BLOCKED ce-49-skew-guard-quickwin already-resolved`.

## Constraints
- Files (closed set): validators/creator_engine_validator/ce_cli.py (+ ONE new small helper module
  if cleaner, named in carrier) · its existing test module (find the ce_cli test file; if none
  exists, a new validators/tests/unit/test_ce_cli_skew_guard.py) · changelog · carrier.
- Do NOT touch: v3_cli.py, secret_identity.py, forge/, .github/workflows/, deploy/, brain ledger,
  test_ce_brain_drift.py (your ce-446 unit owns the last two).
- Note: editing ce_cli.py may trip docs-reconciliation or brain-pin gates — check
  `.ce/brain/assertions.yaml` for pins on ce_cli.py BEFORE starting (grep evidence_ref); if
  pinned, the supersession + count-ratchet bump in test_ce_brain_drift.py is PRE-AUTHORIZED for
  this unit too (same mechanism as your ce-446 addenda — but test_ce_brain_drift.py is shared with
  your ce-446 branch: if both units need ratchet bumps, serialize this unit's push AFTER ce-446
  merges and rebase, to avoid a conflicting double-bump).
- Use main-vintage invocation for all ce commands (Addendum-2 rule applies here too).
- ⛔ Signed-artifact stop-line as always.

## Preflight + deliver
FULL validate-pr GREEN one pass. Work class: story. Changelog + carrier (stem == branch).
Self-push PR titled `ce-ops#49 quick-win: refuse gate commands under stale-wheel version skew`;
body: one work-class line + `Closes creator-engine/ce-ops#49`? NO — #49 is the broader epic; use
`Part of creator-engine/ce-ops#49` instead so the epic stays open.

## Stop line
No review, no approve, no merge, no enqueue. Report PR URL.
