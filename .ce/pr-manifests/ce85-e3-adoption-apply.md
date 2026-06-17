# PR path manifest — ce85-e3-adoption-apply · E3 brownfield adoption-apply (the governance join-PR layer, ce-ops#85)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce85-e3-adoption-apply

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified:
Operator-RATIFIED ce-ops#85 BUILD MANDATE (`/tmp/e3-build-mandate-FULL.md`) against the ratified gate-spec
`designs/CE53_E3_ADOPTION_APPLY_GATE_SPEC_DRAFT.md` @ `a4bf8b2` (sha256 `f1d0659f…c62fe8c`) + the
CLEAN-WITH-NITS verify verdict (`…VERIFY_VERDICT_20260617T1430Z.md`) — its 2 MAJORs built as HARD
requirements + the MINORs. §7-governed build seat (commit-local + HOLD, push-denied). ONE branch, ONE PR.
Review routes to dev-2 / `ubuntuaws745-cmyk` (dev-1 authored the spec → independent venue).

Base:
`1a0672071c1c77e2ee78c28490e81a40a947901a` (current `origin/main` after #250 §8c +
#252 mirror republish). The original E3 build was grounded and reviewed from
`2f3d2b0c84bcca54b3ebfe27762624ab1ecf24ab` (#249); PR #251 was then rebased
linearly onto `1a06720` so `verify-path-manifest --base origin/main` evaluates the
final 15-path E3 diff exactly, with no merge commit.

The changes (one branch, ce-ops#85 — extend-in-place, OQ-2 recommended default; `V3_RUNTIME` unchanged
at 47 — no new module; `install-answers` rows unchanged at 40 — authorization is ENV not schema; 0 new
registered checks):

- **`onboard_apply.py`** — appends the 7 mode-gated adoption legs to `LEG_IDS` (E2 §6 seam 1; ledger shape
  unchanged), the join-PR leg bodies (`_run_adoption_leg`), the affirmatively fail-closed scrub evaluator
  (`_evaluate_scrub_result`, MAJOR-2), the scaffold-artifact helper, the adoption summary counters (§4), the
  base `ApplyDriver` adoption seams, and `ApplyRequest`/`PreparedApply` adoption fields. Greenfield FORGE legs
  skip in adoption mode; adoption legs skip otherwise.
- **`onboard_apply_live.py`** — `LiveForgeAdoptionDriver` (the two-token model, MAJOR-1): READ legs ride the
  inherited Phase-1 read token (`administration:read`); the WRITE legs ride a SEPARATE token at the §6.1
  ceiling (`contents:write`+`workflows:write` Tier-2 + `pull_requests:write` Tier-3, `administration:write`
  EXCLUDED) minted for legs 4-5 ONLY and revoked immediately after. The sha-pinned two-scanner scrub seam
  reads runtime host pins (`CE_FORGE_GITLEAKS_URL`/`CE_FORGE_GITLEAKS_SHA256`,
  `CE_FORGE_TRUFFLEHOG_URL`/`CE_FORGE_TRUFFLEHOG_SHA256`) and fail-closes until valid pins are supplied.
  `adoption_forge_select` gates on the dual ENV escalation `CE_FORGE_LIVE_FORGE` +
  `CE_FORGE_ADOPTION_WRITE` (OQ-3). PR #251 fixes additionally make branch-protection read failures
  fail-closed unless GitHub returns the explicit "Branch not protected" signal, and verify the committed
  scaffold tree before any push.
- **`v3_cli.py`** — routes a genuine non-CE adoptable repo, when authorized, to the adoption-apply legs
  (`adoption_apply=True` + the plan/probe + the adoption driver); unauthorized keeps the unchanged
  `e2_brownfield_seam_unavailable` status quo; blockers always refuse. Adds an adoption summary line.
- **`v3_installer.py`** — `brownfield_inventory_sha256` (the drift-check recompute); reconciles
  `BROWNFIELD_APPLY_STEP_IDS` and `--plan` `apply_steps` to the same 7 join-PR executor legs,
  including push/open-PR, and drops `github_branch_protection` (verify-verdict MINOR); fixes the
  plan-side scanner fail-open seam (a `clean` status now requires an affirmative
  `scanner_available: True`).
- **docs** — `brownfield-adoption.md` (the join-PR contract: legs, dual escalation, two-token model,
  fail-closed scrub) + `ONBOARD_APPLY_PROTOCOL.md` (adoption legs 13-19 + the new counters).
- **tests** — the §10 plan + the HARD-requirement cases (scrub fail-closed on finding/scanner-error/timeout/
  unparseable/not-two-scanner-clean; two-token write-legs-only + revoked + read token admin:read; mint-without-
  escalation refuses; push-never-force; PR-idempotent claim; preserved-checks loss). PR #251 adds the
  fail-closed error-branch regressions for 403/transient/generic-404 protection reads, commit failures,
  committed-tree omissions, and runtime scanner pins. `test_onboard_apply.py` greenfield/plain-join count
  asserts updated for the grown `LEG_IDS` (7 adoption legs skip), and `test_v3_installer.py` pins the
  plan/executor step-id alignment.

Scope reconcile for the 10-path ratified seed manifest:
`validators/tests/unit/test_v3_installer.py` is a named exception in this per-PR carrier, alongside the
standard changelog/PR-manifest/wheelhouse exceptions, because `v3_installer._apply_steps` owns the
planner contract that must remain aligned with the executor leg ids. Keeping that assertion in the
installer unit test is deliberate; the CLI route also asserts the surfaced payload in
`validators/tests/unit/test_v3_cli.py`.

OQ answers baked in: ceiling `{metadata:read, contents:read, contents:write, workflows:write,
pull_requests:write}` with `administration:write` EXCLUDED (OQ-1); ENV `CE_FORGE_ADOPTION_WRITE` (OQ-3);
the validate workflow rides the join PR (OQ-4); NO auto-merge — open PR + stop (OQ-6); live = VPS Mode-A
only, CI = FakeDriver + #44 Mode-B (OQ-7). `plan_ref = inventory_sha256` per the spec — confirmed no
downstream consumer mis-reads it as a policy digest (the only `ce-policy-sha` consumer, `forge.plan_approval`,
runs in the coordination/merge flow the adoption phase never enters).

Wheel pair (required by the `validators/creator_engine_validator/**` edit):
`creator_engine_validator-0.2.0-py3-none-any.whl` rebuilt from current source (`uv build --wheel`,
`setuptools.build_meta`; `build/` + egg-info leak removed before commit) + `validators/wheelhouse/SHA256SUMS`
updated (only the app-wheel line, digest `a0bfe9a5b52367cd46c0f886096d8e3c29f72d556be6bfa30cb4022692fecd96`,
self-verified via `sha256sum -c`). `verify_wheel_matches_source`
clean; `_version.py` untouched (no version bump — 0.2.0).

Per-file purpose (the closed path-set — 15 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce85-e3-adoption-apply.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce85-e3-adoption-apply.md`** *(A)* — this carrier (self-inclusive).
- **`docs/contracts/brownfield-adoption.md`** *(M)* — the join-PR adoption-apply contract.
- **`docs/operations/ONBOARD_APPLY_PROTOCOL.md`** *(M)* — adoption legs + counters.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* — adoption legs + scrub gate + counters.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* — `LiveForgeAdoptionDriver` + two-token model + scanner seam + selector.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — the adoption route.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* — inventory-sha helper + step-id reconcile + scanner fail-open fix.
- **`validators/tests/integration/test_onboard_apply_brownfield.py`** *(A)* — end-to-end adoption integration test (#44 Mode-B cited).
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* — adoption leg unit tests + grown-LEG_IDS count fixes.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* — two-token model + token-ceiling + push-never-force Mode-B tests.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — the authorized adoption-route CLI test.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* — pins `--plan` apply-step ids to the executor leg set.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — rebuilt-wheel digest updated (only the app-wheel line).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt from current source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=5c9a09a7e7a4969695e3245b7e98f505977ed93dbdf80b8edee704588882f40f

```text
.ce/changelog/ce85-e3-adoption-apply.md
.ce/pr-manifests/ce85-e3-adoption-apply.md
docs/contracts/brownfield-adoption.md
docs/operations/ONBOARD_APPLY_PROTOCOL.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_onboard_apply_brownfield.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
