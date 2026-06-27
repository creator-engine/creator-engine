# PR path manifest - deterministic-citations-brain-gotcha

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref deterministic-citations-brain-gotcha --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feat

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
- **`.ce/changelog/deterministic-citations-brain-gotcha.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/deterministic-citations-brain-gotcha.md`** *(A)* - this
  closed path-set carrier.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(M)* - authoritative-ledger
  test updated for the new active assertion (count 9 -> 10) and its presence.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=593ab9959f2387a2392f3b67e699ca0b48d1a5cad417b7a36561c045d01e03b8

```text
.ce/brain/assertions.yaml
.ce/brain/notes/deterministic-citations.md
.ce/changelog/deterministic-citations-brain-gotcha.md
.ce/pr-manifests/deterministic-citations-brain-gotcha.md
validators/tests/unit/test_ce_brain_drift.py
```
