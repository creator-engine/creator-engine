# PR path manifest - ce28-web-control-ui-adr

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce28-web-control-ui-adr
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Ratified controller relay:
ce-ops#28 / #45 web-L3 design only. Produce a ratifiable ADR + a sliced build
plan for CE's web control UI (the web L3 over the L2 cockpit read-model), modeled
on OpenClaw's, grounded in the real OpenClaw `ui/` source and CE's existing
read-model / cockpit-serve / journey-cockpit gate-seam. Low-fi visual mockups are
staged uncommitted under `tmp/webui-shots/` for the Operator's visual checkpoint.
No implementation (no gateway, no SPA), no binding changes, no push.

Base:
`28e57111` (`origin/main` at branch point, post PR #283 / ADR-0007).

Per-file purpose (closed path-set - 3 paths):
- **`.ce/changelog/ce28-web-control-ui-adr.md`** *(A)* - changelog fragment for the design artifact.
- **`.ce/pr-manifests/ce28-web-control-ui-adr.md`** *(A)* - this carrier.
- **`docs/decisions/ADR-0008-web-control-ui.md`** *(A)* - accepted design-only ADR (Operator-ratified 2026-06-20).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=042148a0af62d58bfe8ae26394d33c8203ad2be88f6fc38eb0f608598fc1ece9

```text
.ce/changelog/ce28-web-control-ui-adr.md
.ce/pr-manifests/ce28-web-control-ui-adr.md
docs/decisions/ADR-0008-web-control-ui.md
```
