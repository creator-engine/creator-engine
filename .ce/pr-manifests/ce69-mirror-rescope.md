# PR path manifest — ce69-mirror-rescope · ce-ops#69 Pages-mirror test re-scope

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce69-mirror-rescope
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-APPROVED, filed `ce-ops#69`. Work claim `wclaim-4b1361bdc3919191` (holder `ce-pilot-1`)
held for the duration. The HALT-check is cleared: ce-ops#69 confirms the dropped byte-match's only
purpose was the mirror-publish guarantee, now replaced by the mirror's internal self-consistency —
no hidden second purpose, so the re-scope is safe.

Base:
`e427b67cd3edbb09476faee771c72528015f8c12` (`origin/main` = #222, the install-answers-schema
publish fix on top of #220 which introduced these pages-mirror tests). The path-set + hash are
satisfiable at this base.

The change (test-only):
PR #220 added two packaging-contract tests that BYTE-MATCH the published Pages mirror
(`docs/downloads/0.2.0/`) against the live dev wheelhouse (`validators/wheelhouse/`). That coupling
deadlocks every post-#220 code lane that legitimately advances the dev wheelhouse to a `0.2.0+sha`
build (e.g. RS #223 and the #54/#56/#58 batch): a rebuilt dev wheel is no longer byte-identical to
the frozen published 0.2.0 artifact, so the mirror tests go red even though nothing about the
published release changed. This re-scope replaces the dev-wheelhouse byte-match with an assertion of
the published mirror's **own internal self-consistency** — `docs/downloads/0.2.0/SHA256SUMS` must
match its OWN wheels plus `docs/install.sh`. The published 0.2.0 mirror is a frozen, self-verifying
release artifact; the dev wheelhouse advances freely; the published wheel changes only at a ratified
release + re-sign (→ 0.3.0). The dev-wheel↔source contract is UNTOUCHED — `verify_wheel_matches_source`
(and its two tests) still guard it. No production code, schema, workflow, wheel, changelog fragment,
signed spec, or install-chain artifact is edited (V1/V3/registry counters UNCHANGED).

Per-file purpose (the closed path-set — 2 paths):
- **`.ce/pr-manifests/ce69-mirror-rescope.md`** *(A)* — this carrier (self-inclusive).
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* — re-scope the two pages-mirror tests:
  `test_pages_mirror_wheels_are_byte_identical_to_wheelhouse` (which dropped its wheelhouse byte-match)
  is renamed to `test_pages_mirror_wheels_match_published_sha256sums` and now asserts every wheel under
  `docs/downloads/0.2.0/` hashes to its own SHA256SUMS entry; `test_pages_mirror_sha256s_publishes_install_sh_and_wheels`
  keeps publishing `install.sh` + the wheels but verifies them in-place against the mirror's own files,
  not `validators/wheelhouse/`. A shared `_parse_sha256sums` helper is added. Together the two tests pin
  a bijection between the mirror's wheel files and its SHA256SUMS wheel entries.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=bf76c92284f72cc6310cc5398cfe2074f7f0ec53413749f93a3ca345b18768d3

```text
.ce/pr-manifests/ce69-mirror-rescope.md
validators/tests/unit/test_packaging_contract.py
```
