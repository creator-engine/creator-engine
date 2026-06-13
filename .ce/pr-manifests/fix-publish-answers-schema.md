# PR path manifest — fix-publish-answers-schema · publish install-answers schema to docs/

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref fix-publish-answers-schema

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified:
Operator verbal ratification 2026-06-13 — isolate + land the rehearsal-critical answers-schema publish fix
ahead of the #54/#56/#58 batch.

Base:
`08b07e78b4af33afbd77c0b00b134d9cb4fbcc62` (`main` = #220, the v3.5-E E-wave merge).

The change (publish/mirror only):
The E-wave `install.sh` unconditionally fetches + hash-verifies the answers schema at
`https://creator-engine.dev/schemas/install-answers.schema.yaml` (`docs/install.sh:409-410`), pinned in
`docs/llms-install.md:27` at `answers_schema_sha256: 5879efacfd…`. GitHub Pages serves `docs/`, but the
schema was never mirrored there, so the URL 404s and every install aborts at `network_fetch_failed`. This
PR mirrors the already-ratified, byte-identical `schemas/install-answers.schema.yaml` into
`docs/schemas/install-answers.schema.yaml` (same sha256 `5879efacfd…` as the live signed spec pin). No
trust-chain change — it only makes the already-pinned hash fetchable. No code, schema-semantics, or
dependency edit.

Per-file purpose (the closed path-set — 2 paths):
- **`.ce/pr-manifests/fix-publish-answers-schema.md`** *(A)* — this carrier (self-inclusive).
- **`docs/schemas/install-answers.schema.yaml`** *(A)* — byte-identical published mirror of
  `schemas/install-answers.schema.yaml` (sha256 `5879efacfd62507abbc83fd5729037e09c1259203d2ab87910cc9d3a9f605488`),
  served by Pages at `creator-engine.dev/schemas/install-answers.schema.yaml`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=a76b1505081cabd15c8f1a23af991b30e37bc8b18ab6b208f06668be16e36349

```text
.ce/pr-manifests/fix-publish-answers-schema.md
docs/schemas/install-answers.schema.yaml
```
