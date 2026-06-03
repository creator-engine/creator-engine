# PR path manifest — docs/v3-roadmap.md (durable in-repo v3 roadmap)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **docs-only** PR: it adds `docs/v3-roadmap.md`, a durable, shareable,
in-repo consolidation of the v3 roadmap (orientation + design-source pointers +
the G-i/ii/iii -> G-1 -> G-2 -> G-3 gate map + a per-gate status table with PR /
commit + what's next + a code-location table + a maintenance note). No code, no
`@register` check, no schema, no backend -> `--list-checks` is **unchanged at 43**
and `available_backends()` is unchanged; no `ce_cli.py`/wheel change. Re-baselined
onto `main` after the G-2.1 merge (PR #120) advanced it; the path-set is unchanged
(same COUNT + SHA), only the base and the roadmap's G-2.1 status row moved.

- **base:** `269c8f25c561a287ff7d8f92f810621c8cc3364f`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
