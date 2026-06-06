# PR path manifest — v3 G-3.7 roadmap-flip + pilot-map extension (docs-only)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the **final G-3.7 slice** — the ONE roadmap flip closing the whole G-3.7
program (no per-sub-slice flips), folded with the approved roadmap-to-pilot
extension (`.hermes/research/V3_ROADMAP_TO_PILOT_EXTENSION_PROPOSAL_20260606.md` +
`~/Documents/ce-v3-roadmap-to-pilot-design-20260606.md`). It edits ONLY
`docs/v3-roadmap.md`: flip **G-3.7 → MERGED** (the live OPEN drive proven
end-to-end; gated merge deferred → G-3.7b/G-3.8), append the Pilot block to the
gate-map + 7 `designed` rows (G-3.7b/G-3.8 · G-3.9 · G-4 · G-5 · G-6 · G-7), a
coherence prose fix, and the milestone-aware "What's next" (the **v3.0
MVP-complete** + **v3.1 pilot-ready** milestones + the deferred post-pilot
backlog; cites the in-repo `docs/architecture/pilot-*.md`). **Docs-only, CI-pure:**
zero code/schema/forge/test/architecture-doc change → the suite (1860/1/1),
`--list-checks` (43), `available_backends()`, and `check-examples` (77/0) are all
byte-unchanged. When this merges, **G-3.7 is CLOSED**.

- **base:** `7095cfbfbdb040b1511b899ebe70fab2bd9fec6d`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
