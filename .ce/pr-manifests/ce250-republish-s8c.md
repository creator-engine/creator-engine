# PR path manifest - ce250-republish-s8c - republish 0.2.0 mirror to include §8c

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce250-republish-s8c

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified 2026-06-17 night-shift batch (Q2 "republish overnight") —
republish the public install mirror so the agent-native self-serve install
surface serves the post-§8c (#250) hardened validator wheel. Release process: ce-ops#80.

Base:
`2568cf2` (`origin/main` at branch creation; §8c #250 merged).

The changes (mirror / install-surface republish only — NO source/validator-package change):
- The public install mirror (`docs/downloads/0.2.0`) now carries the §8c-hardened
  app wheel (digest `d81c646c5ef7f3ba73569e1aaa34c9280ab8c82579927a9697036d66149707e1`),
  and `docs/downloads/0.2.0/SHA256SUMS` is refreshed for that one entry.
- `docs/llms-install.md` is re-pinned (`required_wheels` app-wheel sha256,
  `sha256s_sha256`, `content_sha256`) and **RE-SIGNED** over its canonical bytes
  with `ce-root-v1` (SSHSIG, namespace `ce-spec-v1`); stock
  `ssh-keygen -Y verify` reports `Good` for the re-derived canonical.

Per-file purpose (the closed path-set - 5 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce250-republish-s8c.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce250-republish-s8c.md`** *(A)* - this carrier.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - app-wheel digest `f94d6db4…` → `d81c646c…`.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - replaced with the §8c-hardened wheel.
- **`docs/llms-install.md`** *(M)* - re-pinned (wheel sha, `sha256s_sha256`, `content_sha256`) + re-signed (`value`) via `ce-root-v1`; SSHSIG verified Good.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=f35df92f1f7b9a7594a04ad28ebfae1a9aba647c4601699265c87e0b075dd815

```text
.ce/changelog/ce250-republish-s8c.md
.ce/pr-manifests/ce250-republish-s8c.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
