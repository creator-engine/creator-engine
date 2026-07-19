---
slug: ce-df4-mc1-arming
date: 2026-07-19
kind: added
scope: automerge policy — MC1 docs_envelope arming materialization surface
issue: DF-4-MC1-arming
---

**Arm MC1 (docs_envelope) zero-gesture merge tier: add policy materialization surface and arming decision record.**

This PR creates the materialization surface specified in ADR-0016 §2.d ("tier arming happens via governance PR updating the policy materialization variables; no direct edit of policy.json") and records the arming decision.

Changes:

- **`deploy/automerge/policy-declaration.yaml`** — New governed declaration YAML: the single source of truth for `.ce/state/automerge/policy.json`. Sets `run_mode: ceo`, `classes.docs.auto_merge: true`, `tiers.docs_envelope.auto_merge: true`, all other mutation classes and tiers `false`, and `enabling_decision_ref` citing the ADR-0016 ratification prompt SHA. Header comment states file is the single governed source and changes are governance-class two-key PRs.

- **`deploy/automerge/materialize-automerge-policy.py`** — New standalone deploy script invoked as `python3 deploy/automerge/materialize-automerge-policy.py --repo-root <root> [--dry-run]`. Loads the declaration YAML, validates it strictly (unknown keys, non-bool flags, empty enabling_decision_ref, run_mode outside valid set → exit 2, nothing written), constructs `AutoMergePolicyState` via `from_payload`, and on non-dry-run writes atomically via `save_automerge_policy_state` to `automerge_policy_state_path`. Re-loads and prints effective state after write. Imports from `creator_engine_validator` (PYTHONPATH=validators); no new ce CLI command group.

- **`docs/decisions/DEC-0017-mc1-docs-envelope-arming.md`** — Arming decision record: declares MC1 docs_envelope armed under ADR-0016 ratification; cites prerequisite merges PR #1041 and PR #1043; records activation procedure and disarm paths.

- **`validators/tests/unit/test_automerge_policy_materializer.py`** — Unit tests: declaration→payload round-trip; dry-run writes nothing; malformed declaration (unknown key, bad run_mode, empty enabling ref, non-bool flag) refuses with exit 2; idempotent re-run; materialized state satisfies ADR-0016 predicates P11, P12, P13.
