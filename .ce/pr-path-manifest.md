# PR path manifest — v3 G-3.3 roadmap status-flip (`docs/v3-roadmap.md`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **docs-only** PR. It updates `docs/v3-roadmap.md` to reflect that
**G-3.3** (`forge.merge()` gated squash-merge — `MergeResult` / `MergeRefused`,
PR #130, merge commit `25db4e5`) is MERGED: it flips the G-3.3 gate-status row to
`#130` / `25db4e5` / MERGED, advances the status-summary prose and "What's next"
pointer (G-3.0/G-3.1/G-3.2/G-3.3 merged; G-3.4 next), and adds a `forge/merge.py`
(G-3.3) row to the "Where the v3 code lives" table. It touches **no** Python,
schema, or check surface → `--list-checks` is **unchanged at 43** and
`available_backends()` is unchanged at `('gvisor-proxy', 'local-noop')`; no
`ce_cli.py`/wheel change. The draft passes `ce_terminology_v2` and
`no_limitless_strings`.

- **base:** `25db4e5a3f5ffb4a40a267cf077377f7309ed335`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
