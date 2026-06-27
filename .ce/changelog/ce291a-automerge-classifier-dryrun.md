---
slug: ce291a-automerge-classifier-dryrun
date: 2026-06-27
kind: added
scope: forge — CEO-mode auto-merge mutation classifier + policy engine (dry-run)
issue: ce-ops#291
---

PR-A of the ce-ops#291 CEO-mode auto-merge spine. Adds the mutation classifier
and policy engine with a `automerge-decide` dry-run CLI subcommand. **Disarmed
by default** — classify and dry-run only; no minting, no live merge calls.

- **`validators/creator_engine_validator/forge/mutation_classifier.py`** *(A)* —
  classifies PR mutations into AUTO / GESTURE / OPERATOR tiers from diff metadata.
- **`validators/creator_engine_validator/forge/automerge_policy.py`** *(A)* —
  policy engine: evaluates classifier output against configurable policy; emits
  structured YAML decisions; all privileged paths resolve to GESTURE or OPERATOR.
- **`schemas/automerge-decision.schema.yaml`** *(A)* — JSON Schema for policy
  decision records emitted by the engine.
- **`schemas/automerge-policy.schema.yaml`** *(A)* — JSON Schema for policy
  configuration files.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — adds
  `automerge-decide` subcommand (dry-run only; exits non-zero if any path
  would AUTO without an explicit Operator-reserved flip).
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* — exports
  new forge modules.
- **`validators/tests/unit/test_automerge_policy.py`** *(A)* — full unit
  coverage for the policy engine.
- **`validators/tests/unit/test_mutation_classifier.py`** *(A)* — full unit
  coverage for the classifier.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* — minor
  inventory update reflecting new forge modules.
- **`README.md`** *(M)* — brief mention of new `automerge-decide` CLI.

PR-B (minting glue + workflow wiring) follows separately.
