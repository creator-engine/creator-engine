# PR path manifest — ce34-rs-resolver-seam · ce-ops#34 RS lane AuthorityResolver seam

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce34-rs-resolver-seam
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED scope (ce-ops#34) RS lane MVP per
`/home/ce/ce34-staging/ce34-rs-seat-mandate.md`, grounded in
`/home/ce/ce34-staging/ce-34-triage-controlplane-design-DRAFT.md` sections 4,
6.3, and 9 Track-RS (design sha256
`a22ea73e6919b3305e35a1377d4ae38962441cf2cefe6c68a7e4cce3434ac6af`).
Scope: behavior-preserving AuthorityResolver Dev seam over the existing
`plan_approved` + `assemble_dispatch` dispatch path, with the RS-3
authority-never-in-the-forge guard. CEO and strangeLoop resolvers remain out of
MVP and are not enabled.

Base:
`20c460c` (`main`; rebased from the mandated base `82a38645` past the benign #220
v35e-prime-wave + #222 + #224 ce-ops#69 mirror-rescope — the #224 rescope is exactly
what unblocks this lane: the two pages-mirror tests now assert `docs/downloads`
internal self-consistency, NOT a byte-match against the dev wheelhouse, so this lane's
rebuilt `0.2.0` app wheel no longer reds them. The rebase was clean
(`test_packaging_contract.py` is touched by #224 only, not this lane); the app wheel was
re-built fresh from the rebased source. `V3_RUNTIME` count = 39 (onboard_apply/v3_greenfield
from #220 + this lane's authority_resolver); path-set unchanged).

The change:
Add the v3 AuthorityResolver interface and Dev resolver as a thin wrapper around
the existing binding gates. Route the front-gate `assemble_dispatch` call and the
merge gate-read/apply path through the Dev resolver while preserving the original
gate results. Add the RS-3 test proving hostile advisory forge context
(`auto-ok` / `ready`) cannot authorize any verdict. Bump the v3 runtime boundary
for the new module. Rebuild the wheelhouse app wheel so its bundled `.py` files
byte-match the current source tree; the signed release copy under `docs/downloads/`
is intentionally untouched.

Per-file purpose (the closed path-set — 9 paths):
- **`.ce/pr-manifests/ce34-rs-resolver-seam.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/authority_resolver.py`** *(A)* — the
  AuthorityResolver protocol, minimal decision/Verdict shapes, and Dev resolver that
  delegates to the existing scope, plan-approval, and merge gates.
- **`validators/creator_engine_validator/forge/plan_approval.py`** *(M)* — routes the
  public `plan_approved(...)` function through the Dev resolver while keeping the
  existing implementation as the delegated gate.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — routes `ce drive`
  front-gate dispatch assembly and `ce merge` gate-read/apply through the Dev
  resolver, consuming the same underlying gate result as before.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — classifies the new
  AuthorityResolver seam as v3 runtime surface.
- **`validators/tests/unit/test_authority_resolver.py`** *(A)* — resolver wrapping tests
  plus the RS-3 hostile advisory context guard.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — v3 runtime module count
  bump for the new seam.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* —
  rebuilt from this worktree's current source so `verify_wheel_matches_source` passes.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheelhouse
  app wheel only.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=e3d91c575f480146221eccbbc2dcb5014b9f8b54bc9626dd8a04c4a6d5741849

```text
.ce/pr-manifests/ce34-rs-resolver-seam.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/authority_resolver.py
validators/creator_engine_validator/forge/plan_approval.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_authority_resolver.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
