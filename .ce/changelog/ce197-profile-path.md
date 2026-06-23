---
slug: ce197-profile-path
ticket: ce-ops#197
type: feat
scope: installer profile PATH
---

Adds a CE-marked, idempotent shell-profile PATH writer and wires the bootstrap
installer to run it by default after installing the `ce`/`cev3` user-local shims.

- The managed block is delimited by `# >>> creator-engine PATH >>>` and
  `# <<< creator-engine PATH <<<`.
- The block prepends `$HOME/.local/bin` and the npm global bin without
  duplicating entries on repeated shell startup.
- Re-running the writer replaces only the CE-marked block and preserves
  non-CE profile lines.
- The installer accepts `--no-fix-path` to skip profile mutation.
- The signed 0.2.0 install spec and versioned download mirror are not
  republished in this source PR; that remains an Operator-signed release step.
