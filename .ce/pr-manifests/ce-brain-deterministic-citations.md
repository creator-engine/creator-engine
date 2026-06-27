# PR path manifest - ce-brain-deterministic-citations

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-deterministic-citations --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** tiny

Scope (ce-ops#310):
Persist a durable, discoverable design learning in CE's Knowledge-SSOT: any
outward-facing doc-grounded / customer-support agent must use **deterministic
citations** (docs-as-skills loading of allowlisted source files, not
RAG/embeddings or context-stuffing) so cite-or-refuse is enforceable,
provenance is verifiable, confidentiality is bundle-build-enforced, and
freshness is checkable. Captured via the established `ce brain assert
--type gotcha` mechanism (internal Knowledge-SSOT), not a public `docs/**` ADR,
to keep the unshipped support-agent feature out of the published surface while
making the general principle durable and `ce brain recall`-able.

Per-file purpose:
- **`.ce/brain/assertions.yaml`** *(M)* - appended the `gotcha` assertion
  (scope global, verification static, content-addressed to the design note).
- **`.ce/brain/notes/deterministic-citations.md`** *(A)* - the tracked design
  note the assertion cites (resolvable in a fresh clone).
- **`.ce/changelog/ce-brain-deterministic-citations.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce-brain-deterministic-citations.md`** *(A)* - this
  closed path-set carrier.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(M)* - authoritative-ledger
  test updated for the new active assertion (count 9 -> 10) and its presence.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=5957d46ab8ddda7fb3432d8254812f735ff0b1e176236a797cd60169c078c73d

```text
.ce/brain/assertions.yaml
.ce/brain/notes/deterministic-citations.md
.ce/changelog/ce-brain-deterministic-citations.md
.ce/pr-manifests/ce-brain-deterministic-citations.md
validators/tests/unit/test_ce_brain_drift.py
```
