# PR path manifest - ce251-republish-e3 - republish 0.2.0 mirror to include E3

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce251-republish-e3

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Operator-ratified 2026-06-18 ("republish E3, it should be on the public mirror")
— republish the public install mirror so the agent-native self-serve install
surface serves the post-E3 (#251) validator wheel. Release process: ce-ops#80.

Base:
`50ce51a` (`origin/main` at branch creation; E3 #251 merged).

The changes (mirror / install-surface republish only — NO source/validator-package change):
- The public install mirror (`docs/downloads/0.2.0`) now carries the E3
  app wheel (digest `884aeb457cc008120622910dc8a59ea1fa893b50d24f7db6af3048c9f9bca2ff`),
  and `docs/downloads/0.2.0/SHA256SUMS` is refreshed for that one entry.
- `docs/llms-install.md` is re-pinned (`required_wheels` app-wheel sha256,
  `sha256s_sha256`, `content_sha256`) and **RE-SIGNED** over its canonical bytes
  with `ce-root-v1` (SSHSIG, namespace `ce-spec-v1`); stock
  `ssh-keygen -Y verify` reports `Good` for the re-derived canonical.

Per-file purpose (the closed path-set - 5 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce251-republish-e3.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce251-republish-e3.md`** *(A)* - this carrier.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - app-wheel digest `d81c646c…` → `884aeb45…`.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - replaced with the E3 wheel.
- **`docs/llms-install.md`** *(M)* - re-pinned (wheel sha, `sha256s_sha256`, `content_sha256`) + re-signed (`value`) via `ce-root-v1`; SSHSIG verified Good.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=0b5e2fee05d4253d94b6fab691ccaefa340f9bc250dd30a74bbf903cdb7ef654

```text
.ce/changelog/ce251-republish-e3.md
.ce/pr-manifests/ce251-republish-e3.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
```
