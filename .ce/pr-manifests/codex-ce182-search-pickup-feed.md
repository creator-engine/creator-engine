# PR path manifest - codex-ce182-search-pickup-feed - ce-ops#182 Search-backed pickup feed

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce182-search-pickup-feed
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set below
(including this carrier).

Base:
`21176dd2508b4a8b7f3d730402ee2ef16a2205b3` (`origin/main` at branch creation).

Change:
ce-ops#182 replaces the pickup feed's GitHub Notifications API observation leg
with GitHub Search API queries so fine-grained read-only PATs can operate the
belt. The downstream claim/dedup ledger and default no-launch behavior remain
unchanged. The existing gated `--enable-launch` path is preserved, but Search
synthetic thread ids are not sent to `/notifications/threads/*`; launch success
records `thread_marked_read: false` for those ids and relies on the claim ledger
for idempotency.

Per-file purpose:
- **`.ce/changelog/ce182-search-pickup-feed.md`** *(A)* - changelog fragment for ce-ops#182.
- **`.ce/pr-manifests/codex-ce182-search-pickup-feed.md`** *(A)* - this carrier.
- **`README.md`** *(M)* - refresh `ce pickup` inventory wording for Search API / fine-grained PAT compatibility.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wire `ce pickup poll` Search options (`--label`, `--org`, scoped `--repo`, ambient-gh opt-in), JSON backoff output, and synthetic-thread launch bookkeeping.
- **`validators/creator_engine_validator/pickup.py`** *(M)* - Search API poller, query builder, hit normalizer, synthetic thread ids, auth fallback policy, and rate-limit fail-closed metadata.
- **`validators/tests/unit/test_pickup.py`** *(M)* - Search API fake transport tests, reason mapping, label query, rate-limit/auth failures, CLI help/JSON, and no-launch safety.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pin the rebuilt app wheel hash.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - app wheel rebuilt from this branch source because the CLI source changed.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=d45a020959b1cb83528b3b2967bf1666225b17facb79c285d3b759a40f661dc2

```text
.ce/changelog/ce182-search-pickup-feed.md
.ce/pr-manifests/codex-ce182-search-pickup-feed.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_pickup.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
