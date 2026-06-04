# PR path manifest — v3 G-3.3 forge-native gated merge op (`forge/merge.py`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR (G-3.3). It adds a pure, forge-native gated squash-merge op so the
orchestrator can MERGE its own PR only when GitHub reports it merge-eligible:

- `forge/merge.py` (NEW) adds `merge(change, *, apply=False, gh_runner=None) -> MergeResult`.
  It is **plan-by-default** and **refuses before any side effect**: `apply=False` composes the
  three G-3.2 reads (`review_state` + `checks_state` + `change_conflicts`) through the injected
  `GhRunner` and returns a value-free `MergeResult` reporting whether the PR `would_merge`
  (eligible ⇔ `review.approved and checks.all_green and conflict.mergeable == "MERGEABLE"`),
  mutating nothing; `apply=True` re-reads the gate, raises `MergeRefused`
  (code `V3-FORGE-MERGE-REFUSED`) BEFORE the merge on a gate-ineligible PR / a malformed `repo`
  / a `ChangeRef` with no open PR / an `apply` without a `head_sha`, and otherwise issues exactly
  one head-pinned squash merge (`PUT /repos/{owner}/{repo}/pulls/{n}/merge` with
  `{"merge_method":"squash","sha":<head>}`) through the same runner. A transport failure (e.g.
  GitHub `405` not-mergeable / `409` head-moved) raises `ForgeConfigError`. It reuses
  `GhRunner`/`ForgeConfigError`/`ForgeConfigRefused` (and `ChangeRef` + the three G-3.2 read ops)
  by import, re-defines `_REPO_RE` and a local `_gh_api_method` literally, and does NOT reuse the
  unrelated PCL-ledger `pcl_runtime.MergeResult` (a NEW forge-native `MergeResult`).
- `forge/__init__.py` re-exports `merge` + `MergeResult` + `MergeRefused`.
- `tests/unit/test_merge.py` (NEW) drives every path through a fake `GhRunner` returning canned
  GraphQL (gate reads) + REST (merge PUT) JSON (`subprocess.run`/`Popen`/`socket.socket`
  monkeypatched to explode — zero live network/subprocess in CI), asserting `runner.calls == []`
  on refusals and that an ineligible/plan-mode call issues NO merge PUT.

It registers **no** `@register` check, adds **no** backend (`register_backend`) and **no**
schema → `--list-checks` is **unchanged at 43** and `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`. The frozen forge siblings `change.py`, `change_status.py`,
`github_repo_config.py`, `scoped_token.py`, `plan_approval.py` are **byte-unchanged**
(reuse by import); the only existing-file edit is `forge/__init__.py`. No `cli.py`/
`ce_cli.py`/`pyproject.toml`/`requirements*` change; no new `schemas/*.yaml`.

- **base:** `fedc24b1c35671f8c91250b432c0f14069bc199c`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=63aad97aebe89ebdfc053bcd2d445163596147ae1d0d04177630d94d209770cd

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/merge.py
validators/tests/unit/test_merge.py
```
