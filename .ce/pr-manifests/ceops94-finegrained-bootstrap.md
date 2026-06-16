# PR path manifest — ceops94-finegrained-bootstrap · fine-grained PAT accept + right-sized bootstrap probe (ce-ops#94)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ceops94-finegrained-bootstrap

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified:
Operator ratified the design `.ce/state/research/DESIGN_CE_OPS_94_bootstrap_finegrained_rightsize-capability.md`
(relayed by the Controller). CE-DEV-2 governed seat, author `chmod735` (push-denied); reviewer = dev-1 /
`cedev1vps-cmd`. ONE branch, ONE PR — closed-manifest gate.

Base:
`3e6b516dd35e6a4350696a70dc90cb48369cfc97` (`main` = #236, post-#233 live-forge ApplyDriver + 0.2.0 mirror).

The changes (one branch, the two-part ce-ops#94 fix — design §5):
- **Part 2 — right-size the bootstrap requirement.** `v3_installer.bootstrap_required_scopes(mode,
  org_create_needed)` returns `()` for a plain-join (the PAT writes nothing) and the full write set
  (+ org repo-create) for greenfield; `bootstrap_scope_table` gains a `required=` override. The
  `onboard_apply.py` probe leg branches on the right-sized requirement.
- **Part 1 — accept fine-grained PATs.** `onboard_apply_live._detect_token_type` (prefix-primary,
  classic-header fallback); `probe_bootstrap_token` reports `token_type` and derives classic scopes
  ONLY for classic tokens. The probe leg accepts classic-by-scopes (unchanged), fine-grained with
  greenfield write-capability enforced fail-closed at the write legs, and refuses
  `bootstrap_token_unverifiable` / `bootstrap_token_invalid`.

Wheel pair (required by the `validators/creator_engine_validator/**` edit):
`creator_engine_validator-0.2.0-py3-none-any.whl` rebuilt from current source (`setuptools.build_meta`)
+ `validators/wheelhouse/SHA256SUMS` updated (only the app-wheel line). `_version.py` left untouched
(no version bump — the baked `BUILD_GIT_SHA` is an ancestor of HEAD, so the freshness check stays clean).

Per-file purpose (the closed path-set — 14 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ceops94-finegrained-bootstrap.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ceops94-finegrained-bootstrap.md`** *(A)* — this carrier (self-inclusive).
- **`docs/contracts/installer.md`** *(M)* — bootstrap-token VERIFICATION section: right-sizing + fine-grained acceptance.
- **`docs/operations/ONBOARD_APPLY_PROTOCOL.md`** *(M)* — probe-leg requirement note + refusal codes.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* — probe leg branches on required + token_type.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* — `_detect_token_type` + `_has_oauth_scopes_header`; probe returns token_type, classic-only scope derivation.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* — `bootstrap_required_scopes` + `bootstrap_scope_table(required=)`.
- **`validators/tests/unit/fixtures/ce88_live_forge/CAPTURE.md`** *(M)* — document the fine-grained verbatim capture.
- **`validators/tests/unit/fixtures/ce88_live_forge/user_response_finegrained.txt`** *(A)* — verbatim fine-grained `GET /user` (no X-Oauth-Scopes), PII-reduced.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* — FakeDriver token_type + leg tests (plain-join FG passes, greenfield FG defers, unknown/invalid refuse).
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* — fine-grained probe test + `_detect_token_type` unit tests; realistic token prefixes.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* — `bootstrap_required_scopes` + `required=` override tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — rebuilt-wheel digest updated (only the app-wheel line).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt from current source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=9fbf8b3e2d9691029f817c71c3a334a414f3fc3a6617e7beaf84260449eea60c

```text
.ce/changelog/ceops94-finegrained-bootstrap.md
.ce/pr-manifests/ceops94-finegrained-bootstrap.md
docs/contracts/installer.md
docs/operations/ONBOARD_APPLY_PROTOCOL.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/fixtures/ce88_live_forge/CAPTURE.md
validators/tests/unit/fixtures/ce88_live_forge/user_response_finegrained.txt
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
