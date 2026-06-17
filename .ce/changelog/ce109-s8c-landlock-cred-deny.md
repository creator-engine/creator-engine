---
slug: ce109-s8c-landlock-cred-deny
date: 2026-06-17
kind: added
scope: runner / Ring-1 Section-8c filesystem mediation
base: 64678daf0376c0b3ef227b63c8a00fc6d6766f4e
---

Adds Ring-1 Section-8c filesystem mediation: a kernel-enforced Landlock
credential-path read-deny applied to the runner subprocess at launch, closing
the gap where the git/gh shims never see a non-git file access (a Section-7
runner seat could `cat .env` / `open('.env')` / read `~/.ssh/id_rsa` to
exfiltrate credentials, entirely outside Ring-1).

- Hoists the credential-shape predicate `is_secret_path` (plus its rule
  constants) out of v1 `hook_check` into a new **shared** module `secret_paths`,
  so the v3 runner reuses the exact same single source of truth without crossing
  the v1↔v3 version boundary. `hook_check.is_secret_path` is re-exported,
  byte-for-byte unchanged for existing callers.
- Adds the shared `fs_mediation` module: a Landlock read-confinement that grants
  `LANDLOCK_ACCESS_FS_READ_FILE` only beneath an explicit allow-list (system
  runtime roots + the runner's workspace) and is applied to the launched runner
  via `preexec_fn` (`no_new_privs` + `landlock_restrict_self`; survives
  `execve`, so the launched process cannot opt out). Any file-content read
  outside the allow-list — the host's `~/.ssh` / `~/.aws` / `~/.gnupg` /
  `~/.netrc` / `~/.git-credentials` stores, an out-of-workspace `.env` — is
  denied by the kernel.
- Reuses `is_secret_path` as a fail-closed config guard: a workspace read root
  that is itself credential-shaped is rejected at construction.
- Honest fallback: when Landlock is unavailable, a policy that REQUIRES
  Section-8c fails closed (`FsMediationUnavailable`), and an advisory caller
  receives a capability object declaring `sandbox_fs_enforced=false` — never a
  silent claim of FS mediation. The capability also declares the honest
  non-coverage (in-workspace `.env` residual → in-band hook/shim layer;
  pre-`restrict_self` re-exec; `READ_DIR` enumeration; net exfil = Section-8b
  #108; FUSE/fanotify deferred).
- Scope is the runner subprocess only; the deployed-Claude/controller path is
  untouched, and this is independent of the OpenShell/gVisor backends.
- Tests both directions, gated on real Landlock availability for the live proof:
  out-of-workspace `.env` / `~/.ssh/id_rsa` / `~/.aws/credentials` reads are
  DENIED under a launched confinement; in-workspace source reads and
  `git status` / `git add` are unaffected; the in-workspace `.env` residual is
  proven and declared. Host-portable unit tests cover the ABI probe, capability
  shapes, the fail-closed/advisory fallback, and the config guard.
- Rebuilds `creator_engine_validator-0.2.0-py3-none-any.whl` and refreshes
  `validators/wheelhouse/SHA256SUMS` with digest
  `1299a4769cf42678d5d780923e394f5de0e19cf555a8a5b7ed0fc986e1b1ee84`.
