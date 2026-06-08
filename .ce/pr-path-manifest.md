# PR path manifest — docs(roadmap): fill the G-7 row commit SHA (pending → 5ffc28d)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **DOCS — fill the deferred G-7 roadmap-row commit SHA.** The G-7 product-surface
row in `docs/v3-roadmap.md` carried a literal `pending` in its commit column (the
SHA was deferred from G-7 because the OpenShell A.1 PR — the natural carrier — kept it
out of its closed manifest). Fill it with **`5ffc28d`**, the `#170` merge that reached
the **v3.1 pilot-ready** milestone. One-token edit; **no code/schema/test/example
change**; `docs/` is the only path touched besides this carrier.

- **base:** `df85fe027d9414c205ac602c121f75b55f3f6a64`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
