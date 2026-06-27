# PR path manifest - ce323-install-shell-fix - ce-ops#323 install one-liner `| sh` → `| bash`

- **Declared work class:** tiny

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce323-install-shell-fix

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Doc-correction worker brief for ce-ops#323 — the Arad pilot runbook install
one-liner pipes the bash-only `install.sh` to `sh` (dash on Ubuntu), which
crashes (`set: illegal option -o pipefail` → `curl (23) failure writing
output`) and broke a real test user. Replace with the canonical hardened
`| bash` form.

The change:
- Fix the single `| sh` install pipe to
  `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`.
- A full-tree sweep confirmed this is the only remaining `| sh` install pipe in
  docs/README/playbooks; all other one-liners already use `| bash`.

Out of scope (separate follow-ups): the `verify-install` / `onboard` command
references that exist only on unreleased `main` (pending fresh-release decision),
and `install.sh` self-recovery hardening.

Per-file purpose (the closed path-set - 3 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce323-install-shell-fix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce323-install-shell-fix.md`** *(A)* - this carrier.
- **`playbooks/controller/runbooks/arad-pilot.md`** *(M)* - install one-liner `| sh` → `| bash`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=7db629c1583e0cb1887c55f2db41701e9a0caf6c0e0adf6fc071b37287641f15

```text
.ce/changelog/ce323-install-shell-fix.md
.ce/pr-manifests/ce323-install-shell-fix.md
playbooks/controller/runbooks/arad-pilot.md
```
