# PR path manifest — ce-ops#291 PR-A · CEO-mode auto-merge classifier + policy (dry-run)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce291a-automerge-classifier-dryrun
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

PR-A of the ce-ops#291 CEO-mode auto-merge spine: adds the mutation classifier, policy
engine, `automerge-decide` dry-run CLI subcommand, two YAML schemas, full unit test
coverage, and minor inventory/README updates. **Disarmed by default** — classify and
dry-run only; no minting, no live merge path. PR-B (minting glue + workflow) follows.

- **Declared work class:** epic

Per-file purpose (closed path-set — 12 paths):
- **`.ce/changelog/ce291a-automerge-classifier-dryrun.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md`** *(A)* — this carrier (self-inclusive).
- **`README.md`** *(M)* — brief mention of new `automerge-decide` CLI.
- **`schemas/automerge-decision.schema.yaml`** *(A)* — JSON Schema for policy decision records.
- **`schemas/automerge-policy.schema.yaml`** *(A)* — JSON Schema for policy configuration.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — adds `automerge-decide` subcommand.
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* — exports new forge modules.
- **`validators/creator_engine_validator/forge/automerge_policy.py`** *(A)* — policy engine.
- **`validators/creator_engine_validator/forge/mutation_classifier.py`** *(A)* — mutation classifier.
- **`validators/tests/unit/test_automerge_policy.py`** *(A)* — policy engine unit tests.
- **`validators/tests/unit/test_mutation_classifier.py`** *(A)* — classifier unit tests.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* — minor inventory update.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=0fd07282e2eabf18440ae658251ff3411c221ddd414d34aaee85f48e492e0f94

```text
.ce/changelog/ce291a-automerge-classifier-dryrun.md
.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md
README.md
schemas/automerge-decision.schema.yaml
schemas/automerge-policy.schema.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/forge/mutation_classifier.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_mutation_classifier.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
