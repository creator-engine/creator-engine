# Command Deprecation Policy

The Creator Engine v1 command surface is governed and shrinking. Top-level
commands are durable user promises, so new top-level commands require explicit
ratification before they become part of the public surface. Existing commands
remain available until they move through the lifecycle recorded in
`docs/contracts/command-deprecation.yaml`.

The YAML manifest is the source of truth for command deprecation state. Product
documentation and `ce --help` must agree with the manifest: a command listed as
active remains documented and visible, a command listed as deprecated warns on
use and points to its replacement, and a command listed as removed is no longer
present in the command surface. A CI gate enforces that agreement.

## Lifecycle

Each lifecycle entry is recorded in the manifest, not inferred from prose.

| Stage | Contract |
| --- | --- |
| `announced` | The intent to deprecate is public, with the replacement identified before runtime behavior changes. |
| `deprecated` | The command still runs, but each use emits a warning and names the replacement. |
| `removed` | The command has left the top-level command surface. |

The removal floor is one minor release after the command first appears in the
manifest as `deprecated`. A command may move to `removed` only in the next minor
release after that floor, and only when the manifest entry already names its
replacement and announcement release.

## Surface Budget

`surface_budget` in `docs/contracts/command-deprecation.yaml` records the
current top-level command count. Any proposal that adds a top-level command
must explicitly ratify the new budget. Any proposal that removes a command must
update the manifest lifecycle instead of silently deleting the surface.
