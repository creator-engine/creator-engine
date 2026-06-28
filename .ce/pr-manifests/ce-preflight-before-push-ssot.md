# PR path manifest — ce-ops#343 · mandate full offline suite (`ce validate-pr`) before pushing any PR incl releases

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-preflight-before-push-ssot
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself).

- **Declared work class:** story

Scope: docs/playbooks only. Strengthens the PR/merge SSOT + release runbook to make the
full CI-parity offline suite (`ce validate-pr`, whole tree, CLEAN working tree) mandatory
before EVERY push — feature, release/publish, and controller-authored PRs alike — so
failures are caught locally, never surfaced at the forge. Motivated by release-publish PR
#603, where 6 version-pinned install-spec tests still expecting `0.2.0` failed at CI after
only the release signature was verified. The durable version-agnostic-tests fix is filed as
ce-ops#343 (under ce-ops#291 / W2 release-bump). No source, test, or release-artifact edits.

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/changelog/ce-preflight-before-push-ssot.md`** *(A)* — changelog carrier.
- **`.ce/pr-manifests/ce-preflight-before-push-ssot.md`** *(A)* — this carrier (self-inclusive).
- **`docs/delivery/VERSIONING_AND_RELEASE_POLICY.md`** *(M)* — adds the "Release-publish
  preflight" section (offline-suite-before-push for release PRs; the install-spec version-pin
  break; the #603 example; the ce-ops#343 durable fix).
- **`docs/operations/AUTHOR_A_CE_VALID_PR.md`** *(M)* — adds the "MANDATORY before EVERY push
  — no exemptions" directive (no release/signature-ceremony exemption; mirrors `validate.yml`;
  #603 example; ce-ops#343).
- **`playbooks/controller/briefs/merge-gate.md`** *(M)* — adds the "Preflight precondition
  (before EVERY push, no exemptions)" section.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=f14cf785d34d51c96137456b61171862e73315f4d31bbbeba3c2016f47706306

```text
.ce/changelog/ce-preflight-before-push-ssot.md
.ce/pr-manifests/ce-preflight-before-push-ssot.md
docs/delivery/VERSIONING_AND_RELEASE_POLICY.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
playbooks/controller/briefs/merge-gate.md
```
