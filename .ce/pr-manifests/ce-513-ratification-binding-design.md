# PR path manifest - ce-513-ratification-binding-design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-513-ratification-binding-design`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=94950b0a80740773fcb318432bca28ef3043c6d4658d8e675e8e8e78f862026e

```text
.ce/changelog/ce-513-ratification-binding-design.md
.ce/pr-manifests/ce-513-ratification-binding-design.md
docs/design/ratification-authorization-binding.md
```

## Evidence / Preflight Summary

Brief verification:

- `sha256sum /var/tmp/BRIEF_dev4_513_design.md` returned
  `b0e54acec9c23c33aaad69a44f5358a9eb920b361196c230f4fda835620e4ec7`.

Working-tree checks before commit:

- `PYTHONPATH=validators python -m creator_engine_validator scan-public-docs-confidentiality docs/design/ratification-authorization-binding.md`
  returned `PASS public_docs_confidentiality`.
- `PYTHONPATH=validators python -m creator_engine_validator scan-path-manifest .ce/pr-manifests/ce-513-ratification-binding-design.md`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-work-sizing-floor --base origin/main --declared-work-class story`
  returned `PASS work_sizing_floor`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-513-ratification-binding-design`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-test-coupling --base origin/main --pr-body-file .ce/pr-manifests/ce-513-ratification-binding-design.md`
  returned `PASS test_coupling`.

Committed-state preflight:

- `ce` was not installed on `PATH`; used the module-equivalent command:
  `PYTHONPATH=validators python -m creator_engine_validator.pr_preflight --repo-root . --base origin/main --head-ref ce-513-ratification-binding-design --pr-body-file .ce/pr-manifests/ce-513-ratification-binding-design.md --declared-work-class story`.
- The command exited `1`. Its final summary showed the PR-diff gates passing:
  clean worktree, comparison base
  `cb96845279c97a7e92f8b97bb9d63a6cfc3b174e`, brain ledger current-tail
  not applicable, brain append/direct ledger XOR pass, declared work class `S`,
  baseline-diff pytest with zero new failures (`baseline=63`, `head=63`),
  public-docs confidentiality, install-spec signature guard, support-corpus
  confidentiality, fleet manifest guard, YAML parse gates, playbook format,
  malformed examples, list checks, version drift, harness promotion matrix,
  brain drift, work-sizing floor, test coupling, path manifest, and workflow
  permissions audit.
- Repo-wide false-red categories in this seat environment:
  `Control-plane portability guard` failed on the pre-existing literal `/run`
  path in `validators/creator_engine_validator/container_launcher.py:86`;
  `check-examples aggregate gate` and `well-formed examples` failed because the
  signed worktree lease example could not verify without `libsodium`
  (`examples/well-formed/worktree-leases/signed-lease/lease.yaml`, `PCO-024`).
- Confirmation commands:
  `PYTHONPATH=validators python -m creator_engine_validator scan-portability-plane`
  reproduced the portability failure above, and
  `PYTHONPATH=validators python -m creator_engine_validator check examples/well-formed/`
  reproduced only `FAIL worktree_lease_schema` for the same
  `libsodium unavailable` signed-lease verification.
