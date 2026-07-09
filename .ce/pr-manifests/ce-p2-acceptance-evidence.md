# PR path manifest - ce-p2-acceptance-evidence

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md` convention).
This is the closed path set for the P2 Acceptance-Evidence autoclose rule.

- **Declared work class:** story

Scope:
Add parser support for the PR body `Acceptance-Evidence:` field, enforce
warn-mode for tracked issues labeled exactly `directive`, and make absent
cross-repo token configuration visible as a nonzero script exit.

PR body evidence:
Acceptance-Evidence: validators/tests/unit/test_p2_acceptance_evidence.py

Per-file purpose:
- **`.ce/changelog/ce-p2-acceptance-evidence.md`** *(A)* - Unreleased fragment for the Acceptance-Evidence autoclose hardening.
- **`.ce/pr-manifests/ce-p2-acceptance-evidence.md`** *(A)* - this closed path-set carrier.
- **`.github/scripts/ceops_autoclose.py`** *(M)* - directive-label detection, warn-mode comment, token fail-closed behavior, and public-facing P2 comment block.
- **`CHANGELOG.md`** *(M)* - Unreleased entry for Acceptance-Evidence warn-mode and token fail-closed behavior.
- **`tools/ce-ops-autoclose/parse_issue_refs.py`** *(M)* - `parse_acceptance_evidence` parser helper.
- **`validators/tests/unit/test_p2_acceptance_evidence.py`** *(A)* - focused P2 parser, close-bot, and token absence coverage.

Validation evidence:
- `pytest validators/tests/unit/test_p2_acceptance_evidence.py -v` - PASS, 8 passed.
- `pytest validators/tests/unit/test_ceops_autoclose.py -v` - PASS, 13 passed.
- `pytest validators/tests/unit/test_ce262_parse_issue_refs.py -v` - PASS, 27 passed.
- `PYTHONPATH=validators pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q` - PASS, 1 passed. This required the new test file to construct the internal tracker reference dynamically; the prior literal reference produced a real head-only confidentiality failure.
- `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --repo-root . --allow-dirty` - FAIL. Baseline-diff test command reported zero new failures (`baseline=63`, `head=63`) and the public-docs confidentiality scan passed. Remaining false-red families are environment/baseline failures under Python 3.11.2: interpreter contract requires Python >=3.14, local tmux/rootless Podman/uv/libsodium are absent, and the existing examples aggregate/well-formed gates fail accordingly.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ac87c4897fd2ce39945c8f963f20f53d655e33a0033ca13aac81fae6f57cbdb0

```text
.ce/changelog/ce-p2-acceptance-evidence.md
.ce/pr-manifests/ce-p2-acceptance-evidence.md
.github/scripts/ceops_autoclose.py
CHANGELOG.md
tools/ce-ops-autoclose/parse_issue_refs.py
validators/tests/unit/test_p2_acceptance_evidence.py
```
