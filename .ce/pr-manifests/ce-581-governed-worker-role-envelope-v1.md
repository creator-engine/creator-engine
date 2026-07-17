# PR path manifest — ce-ops#581 · Add the governed Codex worker role envelope

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-581-governed-worker-role-envelope-v1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature
- **Review correction:** final-boundary canonical argv and provider-credential
  tuple binding plus descriptor-identity/security-metadata role-policy
  rebinding, with production-path hermetic subprocess evidence.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ebd4e2652fb4e4f53160c254de5dc980e7192f71be6fe7e0a150eaececf41892

```text
.ce/changelog/ce-581-governed-worker-role-envelope-v1.md
.ce/pr-manifests/ce-581-governed-worker-role-envelope-v1.md
specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md
validators/creator_engine_validator/codex_worker_launcher.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_codex_worker_launcher.py
```
