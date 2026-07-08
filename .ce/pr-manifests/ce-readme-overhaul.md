# PR path manifest - ce-readme-overhaul - public README overhaul

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-readme-overhaul` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Slug: `ce-readme-overhaul`

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

## Purpose

- Replace the stale public README with a concise product front door: hero, badges, conceptual model, quickstart, modes, non-rotting status, documentation fan-out, and license footer.
- Add a public CLI reference at `docs/reference/cli.md` and retarget the v1 docs reconciliation guard from README inventory text to that reference.
- Extend the current-version drift gate so README CE-version text claims are checked against the canonical release version.
- Add unit coverage for matching README version text, stale README version text, version-free README content, CLI-reference parity, and the README reference link.
- Supersede the affected brain assertion for the docs reconciliation evidence and update its active-record count probe.

## Changed Paths

- `README.md` - public-facing README overhaul.
- `docs/reference/cli.md` - public `ce` command inventory.
- `validators/creator_engine_validator/checks/version_drift.py` - additive README CE-version text pattern in the existing version-drift current surface gate.
- `validators/tests/unit/test_version_drift.py` - README version drift matrix coverage.
- `validators/tests/unit/test_v1_docs_reconciliation.py` - CLI-reference reconciliation surface and README link guard.
- `validators/tests/unit/test_ce_brain_drift.py` - active brain assertion count update for the superseded docs reconciliation assertion.
- `.ce/brain/assertions.yaml` - superseded docs reconciliation assertion plus replacement active assertion.
- `.ce/changelog/ce-readme-overhaul.md` - changelog fragment.
- `.ce/pr-manifests/ce-readme-overhaul.md` - this carrier.

## Command Source Grounding

README command lines and the public CLI reference were grounded in local `origin/main` documentation or CLI help/source; no web fetches were used.

- `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash` - `origin/main:docs/install.sh` header and `origin/main:docs/contracts/installer.md`.
- `ce onboard` - `origin/main:docs/guide/zero-to-governed-seat-quickstart.md`, `origin/main:docs/guide/solo-dev-onboarding.md`, and `origin/main:validators/creator_engine_validator/ce_cli.py` help surface.
- `ce launch` - `origin/main:docs/guide/zero-to-governed-seat-quickstart.md` and `origin/main:validators/creator_engine_validator/ce_cli.py` help surface.
- Developer-mode verbs `ce brain init`, `ce shape`, `ce scope`, `ce ratify`, `ce drive --spawn`, and `ce report` - `origin/main:docs/guide/quickstart.md`, `origin/main:validators/creator_engine_validator/ce_cli.py`, and `origin/main:validators/creator_engine_validator/v3_cli.py`.
- `docs/reference/cli.md` public inventory - current `validators/creator_engine_validator/ce_cli.py` argparse registry, excluding command groups marked internal-only by `ce_cli.INTERNAL_COMMAND_GROUPS`.

## 30-Second-Comprehension Self-Test

Paste tested from the README hero plus "What is Creator Engine" section:

```text
Creator Engine turns an idea into governed, working software through a guided AI-development journey where quality is enforced by evidence gates, not by trusting model output.

Creator Engine is a terminal-first governance layer for the coding agent you already use. You describe the change you want, confirm the Goal, Done-when, and Change-type, and CE runs the build loop with auditable evidence. The agent can draft, implement, test, and prepare review artifacts; CE keeps the work inside the confirmed boundary and holds privileged actions for human approval. Review is evidence-gated: you judge the diff, tests, and Completion Report against the Done-when you approved. A Budget can be added when a lane requires a cap, but it is not part of the default first journey.
```

Self-test result: a new reader can identify what CE is, why it matters, how the human participates, and how quality is enforced without relying on dated release prose.

## Gate Test Matrix

- CLI docs reconciliation: `PYTHONPATH=validators python -m pytest validators/tests/unit/test_v1_docs_reconciliation.py -q` -> `11 passed in 1.55s`.
- README version-drift matrix: `PYTHONPATH=validators python -m pytest validators/tests/unit/test_version_drift.py -q` -> `13 passed in 4.10s`.
- Brain assertion drift probe: `PYTHONPATH=validators python -m pytest validators/tests/unit/test_ce_brain_drift.py::test_authoritative_migrated_assertions_validate_and_probe -q` -> `1 passed in 1.33s`.
- Current repository version-drift gate: `PYTHONPATH=validators python -m creator_engine_validator verify-version-drift .` -> `PASS version_drift_current_surfaces`.
- Matrix rows covered by `validators/tests/unit/test_version_drift.py`:
  - Matching README version text passes for `Current release: 0.3.2`, `Version 0.3.2`, `CE v0.3.2 is current`, `Creator Engine Version 0.3.2 is current`, and case variants: `test_readme_ce_version_text_matching_current_version_passes`.
  - Stale README version text fails for `Current release: 0.3.1`, `Version 0.3.1`, `CE v0.3.1 is current`, `Creator Engine Version 0.3.1 is current`, and case variants: `test_readme_ce_version_text_stale_version_fails_for_public_current_claim_forms`.
  - Version-free README passes: `test_readme_without_version_text_passes`.
- Path manifest: `PYTHONPATH=validators python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-readme-overhaul --require-carrier .` -> `PASS path_manifest_fidelity`.
- Full contained-seat preflight: `PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --profile contained-seat` -> `FAIL: PR preflight`; clean worktree, comparison base, brain ledger current-tail, brain append/direct-edit XOR, declared work class, baseline-diff test command, public-docs confidentiality, install-spec signature, support-corpus, fleet manifest, YAML parses, version drift, brain drift, work-sizing floor, test-coupling, path-manifest PR-diff, and workflow permissions passed. Baseline-diff reported zero new failures (`baseline=63`, `head=63`). Remaining failures are outside this PR diff: control-plane portability guard on unchanged `validators/creator_engine_validator/container_launcher.py`, check-examples aggregate / well-formed examples, and worktree lease signature verification with unavailable libsodium. Prior proven outside-diff seat-environment failures remain allowed only for Python `3.11.2` below the `>=3.14` contract, missing runtime tools such as `tmux`/rootless `podman`, check-examples fixture failures, and worktree lease signature failures.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=46e5800e0f060250d5b46d08cbc54559044fd7491e30b952f0b4f6773aa0ee50

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-readme-overhaul.md
.ce/pr-manifests/ce-readme-overhaul.md
README.md
docs/reference/cli.md
validators/creator_engine_validator/checks/version_drift.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_drift.py
```
