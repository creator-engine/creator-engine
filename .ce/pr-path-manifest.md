# PR path manifest — v3 pilot design → `docs/architecture/` (curated, fresh-clone-durable)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **docs-only** gate: it commits the 2026-06-06 pilot design — the
full-stack-first roadmap-to-pilot, the deployment/transport-selection matrix, and
the pilot UI/UX model — into `docs/architecture/` as **curated, redacted,
fresh-clone-resolvable** design references (the established `docs/architecture/`
curated-copy pattern), and indexes them in `docs/architecture/README.md`. Purpose:
make the **G-4…G-7 design durable in-repo** so those gates' planning prompts cite
in-repo docs rather than an instance-local design corpus. It touches no
code/schema/spine/check/example/contract/forge/backend/CLI/wheel surface and adds
no dependency → `--list-checks` is **unchanged at 43**, `available_backends()` is
unchanged at `('gvisor-proxy', 'local-noop')`, and `check-examples` stays 77/0.
The committed docs are redacted per the README provenance discipline (no transient
SHAs / account-host identifiers / gitignored absolute-path pointers / internal IDs;
design substance + dated external citations preserved).

- **base:** `a1325343b7f74b31dcd51e2f954b36f3aac8bb66`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=694614ff0af44b6eda69746b750cbbf3412efc91aa4299b0ef5dc6a304f3e573

```text
.ce/pr-path-manifest.md
docs/architecture/README.md
docs/architecture/pilot-deployment-transport.md
docs/architecture/pilot-roadmap.md
docs/architecture/pilot-uiux-model.md
```
