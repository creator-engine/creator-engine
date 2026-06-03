# PR path manifest — committed `docs/architecture/` (curated v3 design source-of-truth) + G-2.2 roadmap status-flip

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **docs-only** PR. It adds curated/redacted copies of the load-bearing v3
architect reports under `docs/architecture/` (`v3-spec.md`, `v3-secure-runtime.md`,
`v3-product-brief.md`, and a `README.md` index) so the roadmap's design-source
pointers resolve in a fresh clone, and MODIFIES `docs/v3-roadmap.md` to (a) repoint
the "Design source-of-truth" section at the committed copies (keeping the
`.hermes/research/` full-fidelity note) and (b) flip the **G-2.2 status row →
MERGED `b3caa5e`** (PR #122). No code, no `@register` check, no schema, no backend
-> `--list-checks` is **unchanged at 43** and `available_backends()` is unchanged;
no `ce_cli.py`/wheel change. The pre-existing `docs/architecture/*.md` (the v2-era
docs) are left byte-unchanged and are out of this diff.

- **base:** `b3caa5ee7aa05e0ca7bbd4bcc84cd78f0e5682be`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=9f6e9e7c5eed043ee6df8187a35a71879a4a7d219d4c88fba99974325580a54b

```text
.ce/pr-path-manifest.md
docs/architecture/README.md
docs/architecture/v3-product-brief.md
docs/architecture/v3-secure-runtime.md
docs/architecture/v3-spec.md
docs/v3-roadmap.md
```
