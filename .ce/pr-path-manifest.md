# PR path manifest — v3 G-2.2 (`mint_scoped_token`: JIT least-privilege per-run credential)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR (the second G-2 hardening slice). It adds a forge-native
scoped-token minter (`forge/scoped_token.py`: `mint_scoped_token` /
`revoke_scoped_token` / `TokenRequest` / `ScopedToken` [value-redacted] /
`TokenMintRefused`), wires it into the thin orchestrator via an injected
`token_minter` seam + a value-free `MintedCredential` port type + a
`CredentialNotPermitted` refusal (issuance gated on the policy `secret_allowlist`
via the G-1.3b classifier, issuance/revocation attested to the evidence spine),
and documents the seam. Pure behind the existing injectable `GhRunner`; **no
`@register` check, no schema, no `register_backend`** -> `--list-checks` is
**unchanged at 43** and `available_backends()` is unchanged; no `ce_cli.py`/wheel
change. The G-iii `forge/github_repo_config.py`, the G-2.1 `forge/plan_approval.py`,
the `runner/*` backends, and `runtime_evidence_spine.py` are byte-unchanged (reuse
only).

- **base:** `160f08d41b6ab219ff7193d8edc4c8e41fc25245`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=4df02395f6a8a851c6901a8809980f1dd20d21022e8669c48b221d56bac68b33

```text
.ce/pr-path-manifest.md
docs/contracts/orchestrator.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/scoped_token.py
validators/creator_engine_validator/orchestrator.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_scoped_token.py
```
