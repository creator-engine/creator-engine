# PR path manifest - ce-505-guided-journey-research

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-505-guided-journey-research`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=a73ba55b456451a1f3260288b87b881653049b94622bd7fc1d4582bc5c74d0f4

```text
.ce/changelog/ce-505-guided-journey-research.md
.ce/pr-manifests/ce-505-guided-journey-research.md
docs/design/guided-journey-ux.md
```

## Evidence / Preflight Summary

Brief verification:

- `sha256sum /workspace/creator-engine/.ce/briefs/ce-505-guided-journey-research-dev3.md`
  returned `f116f7443801d8dfecebd12422e5f06ec8d5af7aa182a960e87458d2e9b9825f`.
- `sha256sum /var/tmp/BRIEF_ce505_research.md` returned
  `29d2db132b29b3093d5d3840b1b3a3ed49d7f3f50289288188af9c03c89b236d`.

Working-tree checks before commit:

- Required content scan confirmed `Frame -> Shape -> Build -> Review -> Ship`,
  awaiting-operator inbox coverage, batch ratification, vacation test,
  completion reports as emission feed, non-goals, decisions with rejected
  alternatives, absolute references, and ONE-face/read-model wording in
  `docs/design/guided-journey-ux.md`.
- `grep -R "Declared work class"` across the authorized files returned exactly
  one match: `- **Declared work class:** S` in this carrier.
- `git diff --check` returned clean.
- `PYTHONPATH=validators python -m creator_engine_validator scan-path-manifest .ce/pr-manifests/ce-505-guided-journey-research.md`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator scan-public-docs-confidentiality docs/design/guided-journey-ux.md`
  returned `PASS public_docs_confidentiality`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-505-guided-journey-research`
  returned `PASS path_manifest_fidelity`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-work-sizing-floor --base origin/main --declared-work-class S`
  returned `PASS work_sizing_floor`.
- `PYTHONPATH=validators python -m creator_engine_validator verify-test-coupling --base origin/main --pr-body-file .ce/pr-manifests/ce-505-guided-journey-research.md`
  returned `PASS test_coupling`.
- Full `creator_engine_validator.pr_preflight` was attempted before commit and
  correctly refused dirty state: `FAIL clean worktree`.
