# PR path manifest - ce80-republish-s2 - republish 0.2.0 mirror to include S2

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce80-republish-s2

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified 2026-06-17 ("aim high") — republish the public install mirror
so the agent-native self-serve install surface serves the post-S2 (#248)
hardened validator wheel. Release process: ce-ops#80.

Base:
`64678da` (`origin/main` at branch creation; S2 #248 merged).

The changes (mirror / install-surface republish only — NO source/validator-package change):
- The public install mirror (`docs/downloads/0.2.0`) now carries the S2-hardened
  app wheel (digest `f94d6db443a980be06e7fbe6e977559b7cb0efb77d94ae6a70714a048b42559c`),
  and `docs/downloads/0.2.0/SHA256SUMS` is refreshed for that one entry.
- `docs/llms-install.md` is re-pinned (`required_wheels` app-wheel sha256,
  `sha256s_sha256`, `content_sha256`) and **RE-SIGNED** over its canonical bytes
  with `ce-root-v1` (SSHSIG, namespace `ce-spec-v1`); stock
  `ssh-keygen -Y verify` reports `Good` for the re-derived canonical.

Per-file purpose (the closed path-set - 5 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce80-republish-s2.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce80-republish-s2.md`** *(A)* - this carrier.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - app-wheel digest `f0c38c6…` → `f94d6db4…`.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - replaced with the S2-hardened wheel.
- **`docs/llms-install.md`** *(M)* - re-pinned (wheel sha, `sha256s_sha256`, `content_sha256`) + re-signed (`value`) via `ce-root-v1`; SSHSIG verified Good.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=753625ad7e194da7a4e3ae34453ecc0607d9d414d26aa21d95f1917f577df6ab

```text
.ce/changelog/ce80-republish-s2.md
.ce/pr-manifests/ce80-republish-s2.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
