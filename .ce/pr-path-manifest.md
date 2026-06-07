# PR path manifest — v3 G-3.8 / v3.0 "MVP-complete" roadmap-flip (docs-only, CI-pure)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the **v3.0 roadmap-flip docs slice** — a pure docs edit to ONE file
(`docs/v3-roadmap.md`) + this carrier, recording the completed gate states now on
`main`: **G-3.7b** (the CI-pure merge substrate — `.0` `pr_merged` run-outcome
model #148 `894bc42` + `.1` merge-driving producer & distinct live-merge-identity
seam #149 `af60f06`) flipped to **MERGED**, and **G-3.8** (the out-of-envelope live
merge spike — one real PR opened → independently reviewed → squash-merged by a
**distinct merge identity**, merge identity ≠ run token; value-free `pr_merged`
evidence persisted on the same tamper-evident chain; **zero repo code change** — it
ran the already-merged G-3.7b seams) recorded as **PROVEN (live)**. The
**v3.0 "MVP-complete"** milestone is marked **REACHED** (the governed-run engine
proven live end-to-end **including merge**: open → independent review → merge), the
next-pointer advances to **G-3.9**, and the **v3.1 pilot-ready** arc
(G-3.9 → G-4 → G-5 → G-6 → G-7) is opened. **Docs-only / CI-pure:** the diff touches
ONLY `docs/v3-roadmap.md` + this carrier; **zero** code/schema/forge/test/example/
architecture-doc/dependency change, so the executable surface is byte-identical —
`--list-checks` STAYS **43**, `available_backends()` is unchanged
(`('gvisor-proxy','local-noop')`), `check-examples` STAYS **77/0**, and the full
suite outcome is identical to the `af60f06` baseline (nothing executable changed).
The cited `docs/architecture/pilot-*.md` (on `main` since #146) are NOT edited.
Design / acceptance source: `docs/architecture/pilot-roadmap.md` §"G-3.7b / G-3.8"
("the live open→review→merge proven once in G-3.8, merge identity ≠ run token. **=
v3.0**").

- **base:** `af60f06d9e2756cf0f1519d3c1f3541f2c37420c`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
