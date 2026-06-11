# PR path manifest - CODEOWNERS host-bound reviewer identities gate

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator interactive 2026-06-11, ce-ops#10; unblocks the PR #200 class blocked
by `require_code_owner_reviews` with a single owner.

Implementer mandate:
`/home/ce/creator-engine/.ce/state/research/codeowners-fix/MANDATE_codeowners_dev1_reviewer.md`.

Base:
`ee37a4d2b36f6dcf9c24ab35ef84241c05405436` (origin/main).

Per-file purpose (the closed path-set - 2 paths, as ratified):
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier: authorized path-set
  count, hash, and fenced block for the gate.
- **`.github/CODEOWNERS`** *(M)* - add the host-bound CE-DEV-1 reviewer
  identity `@cedev1vps-cmd` alongside `@ubuntuaws745-cmyk`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=c0280fb5d87285aeff789794b6d62124d14c1448966d69aea9bb025b83a685fc

```text
.ce/pr-path-manifest.md
.github/CODEOWNERS
```
