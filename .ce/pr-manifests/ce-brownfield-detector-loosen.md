# PR path manifest — ce-brownfield-detector-loosen · loosen the already-CE workflow detector

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-brownfield-detector-loosen

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

> Carrier filename is locked to `branch_slug(head_ref)`. This file is named for branch
> `ce-brownfield-detector-loosen` (`branch_slug("ce-brownfield-detector-loosen") == "ce-brownfield-detector-loosen"`).

Ratified:
Operator-ratified in ce-ops#90 (2026-06-16) — "Option A: loosen the brownfield already-CE detector"
(loosen ≠ weaken). Built by a governed CE seat on base `bcf8464` (#240); push/merge Operator-gated.

Base:
`bcf8464` (`main` = #240, the 0.2.0 mirror republish to match the post-#239/#238 wheel).

The change (loosen the already-CE workflow detector):
The plain-join already-CE detector hard-pinned a SINGLE workflow filename+digest
(`.github/workflows/ce-validate.yml` at one `CE_WORKFLOW_SHA256`), so an already-CE repo whose CE
validate workflow uses a different filename (e.g. the flagship's legacy `.github/workflows/validate.yml`)
404'd → detection `False` → `e2_brownfield_seam_unavailable`. This replaces the single cosmetic
filename+digest coupling with GOVERNANCE-SIGNAL detection over a KNOWN SET of CE workflow identities
(`CeWorkflowIdentity` / `KNOWN_CE_WORKFLOWS` / `detect_ce_workflow`): a repo is workflow-CE iff ANY
known identity (canonical `ce-validate.yml` OR the legacy `validate.yml`) verifies at its EXACT pinned
digest. The per-identity byte-pin is PRESERVED (the same read the install leg verifies with), so a
tampered / drifted / non-CE / absent workflow matches none and detection fails closed — the anti-tamper
guarantee is unchanged. Both `repo_is_already_ce_governed` and the plain-join `github_workflow_install`
verify leg key on the known-set. Greenfield install is unchanged (canonical `ce-validate.yml`).
Renaming the flagship's `validate.yml` is deferred (Option B), out of scope here.

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce-brownfield-detector-loosen.md`** *(A)* — ce-ops#65 release-surface fragment (kind: fixed).
- **`.ce/pr-manifests/ce-brownfield-detector-loosen.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* — `CeWorkflowIdentity` +
  `KNOWN_CE_WORKFLOWS` (canonical + legacy byte-pins) + `detect_ce_workflow`; `repo_is_already_ce_governed`
  and the plain-join `github_workflow_install` verify leg rewired onto the known-set. Greenfield path unchanged.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* — path-keyed contents in the Mode-B forge +
  REAL-shape detector tests: legacy `validate.yml` accepted, canonical `ce-validate.yml` accepted, a
  tampered CE-validator workflow rejected (anti-tamper), non-CE/absent rejected, and a full plain-join
  `--apply` against a legacy-filename repo COMPLETES exit-0.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned the app-wheel line for the rebuilt wheel (the
  6 dependency-wheel lines are byte-unchanged).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt 0.2.0 app
  wheel (source parity: `packaging_runtime.verify_wheel_matches_source` requires the committed wheel's
  `.py` bytes to equal source). The standard per-PR wheel-rebuild tax for a source change; `_version.py`
  is unchanged (its baked `BUILD_GIT_SHA` stays a valid HEAD-ancestor, so no re-bake is required).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=bec88300395122b4a6278e5ff45f6188e518126799ef298cef04d46bee77f34e

```text
.ce/changelog/ce-brownfield-detector-loosen.md
.ce/pr-manifests/ce-brownfield-detector-loosen.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
