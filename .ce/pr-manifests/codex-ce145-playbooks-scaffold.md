# PR path manifest - codex-ce145-playbooks-scaffold

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce145-playbooks-scaffold
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#145 playbooks scaffold, format contract, schema, CI format gate, and
first in-tree playbooks. This folds ce-ops#151 into the reviewer playbook's
re-review branch.

Base:
`e8e40b2c7503d3783c96ad69fa4dad7c5ddc8998` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 50 paths):
- **`.ce/pr-manifests/codex-ce145-playbooks-scaffold.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - run the explicit `ce_playbook_format` gate and parse playbook YAML.
- **`docs/contracts/README.md`** *(M)* - index the new playbook format contract.
- **`docs/contracts/playbook-format.md`** *(A)* - prose contract for the playbook scaffold and workflow descriptor.
- **`playbooks/README.md`** *(A)* - playbook index and seat consumption contract.
- **`playbooks/author/**`** *(A)* - author role/action playbook with base-only refresh and address-review stages.
- **`playbooks/computer-use-ticket/**`** *(A)* - authenticated-browser computer-use ticket playbook.
- **`playbooks/controller/**`** *(A)* - controller role/action playbook including courier-forge-op.
- **`playbooks/reviewer/**`** *(A)* - reviewer role/action playbook including ce-ops#151 re-review branches.
- **`schemas/playbook.schema.yaml`** *(A)* - machine schema for `workflow.ce.yml`.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - register the new validator check.
- **`validators/creator_engine_validator/checks/ce_playbook_format.py`** *(A)* - scaffold, schema, brief-reference, name-binding, and index validator.
- **`validators/tests/integration/test_playbook_format_examples.py`** *(A)* - integration coverage over in-tree playbooks.
- **`validators/tests/unit/test_ce_playbook_format.py`** *(A)* - TDD unit coverage for the new gate.
- **`validators/tests/unit/test_*` count updates** *(M)* - update registered-check count from 54 to 55.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app wheel digest re-pinned after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing the new check.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=50

AUTHORIZED_PATHS_SHA256=8113f612547f625d47430b347730e9eba17049326fe2a11145d132d0dce1d778

```text
.ce/pr-manifests/codex-ce145-playbooks-scaffold.md
.github/workflows/validate.yml
docs/contracts/README.md
docs/contracts/playbook-format.md
playbooks/README.md
playbooks/author/README.md
playbooks/author/briefs/address-review.md
playbooks/author/briefs/base-only-refresh.md
playbooks/author/envelope.template.yml
playbooks/author/harness.md
playbooks/author/workflow.ce.yml
playbooks/computer-use-ticket/README.md
playbooks/computer-use-ticket/briefs/capture-evidence.md
playbooks/computer-use-ticket/briefs/closeout.md
playbooks/computer-use-ticket/briefs/connect-browser.md
playbooks/computer-use-ticket/briefs/execute-change.md
playbooks/computer-use-ticket/briefs/prepare-ticket.md
playbooks/computer-use-ticket/envelope.template.yml
playbooks/computer-use-ticket/harness.md
playbooks/computer-use-ticket/workflow.ce.yml
playbooks/controller/README.md
playbooks/controller/briefs/courier-forge-op.md
playbooks/controller/briefs/dispatch.md
playbooks/controller/briefs/merge-gate.md
playbooks/controller/briefs/seat-refresh.md
playbooks/controller/envelope.template.yml
playbooks/controller/harness.md
playbooks/controller/workflow.ce.yml
playbooks/reviewer/README.md
playbooks/reviewer/briefs/re-review.md
playbooks/reviewer/briefs/refresh-seat.md
playbooks/reviewer/briefs/review.md
playbooks/reviewer/envelope.template.yml
playbooks/reviewer/harness.md
playbooks/reviewer/workflow.ce.yml
schemas/playbook.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_playbook_format.py
validators/tests/integration/test_playbook_format_examples.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_ce_playbook_format.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
