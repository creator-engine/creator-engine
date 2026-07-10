# BRIEF — dev-3 — 2026-07-08 — 1 STORY unit: ce-ops#499 seat-ready validate-pr profile

Role: implementer. Design #892 (ce-ops#499) merged onto main; the design file is at
`docs/design/seat-side-preflight.md` in the worktree. ce-ops#499 is not readable from
this seat; ticket summary: governed seats currently signal READY before repairing stale
autogen artifacts or malformed carriers, leaving harvest to do author repair work; the
fix is a new `seat-ready` successor profile for `ce validate-pr --profile` that enforces
carrier presence, carrier self-inclusion, changelog inclusion, digest fidelity, declared
work class in canonical vocabulary, registered autogen freshness repair, and public-docs
confidentiality before the READY stop line; this profile is a new addition and does NOT
mutate the existing `contained-seat` profile, which continues to tolerate a missing
carrier because harvest generates it harvest-side. COMMIT-FOR-HARVEST: do not push —
self-push canary not yet re-proven; controller harvests. On green preflight emit exactly
`READY ce-499-seat-ready-profile <commit-sha> <carrier-path>` in the pane; if blocked
emit `BLOCKED ce-499-seat-ready-profile <one-line reason>`.

Worktree setup: `git fetch origin main` first, then create a fresh worktree at
`/var/tmp/ce-499-seat-ready-profile` off `origin/main`. Branch: `ce-499-seat-ready-profile`.
Do NOT activate any venv.

## U1 — branch `ce-499-seat-ready-profile` (work class: S)

I1 — `validators/creator_engine_validator/pr_preflight.py`: add constant
`SEAT_READY_PROFILE = "seat-ready"` and append it to `VALIDATE_PR_PROFILES`. The
existing `_validate_profile` guard already gates by the tuple, so the addition is
sufficient for acceptance. Do NOT add a carrier omission for `seat-ready`: the
`path_manifest_carrier_required` code must NOT be suppressed for this profile — carrier
presence is a non-optional enforced gate. The `contained-seat` omission logic must
remain untouched and unbroadened.

I2 — Same file: add `SEAT_READY_PYTEST_WORKER_CAP = 4` constant. When
`config.profile == SEAT_READY_PROFILE` and the caller did not supply a custom
`--test-command`, substitute a seat-ready test command that is identical to
`DEFAULT_TEST_COMMAND` except `-n auto` is replaced by `-n 4`. Never widen the cap
above 4 for this profile. Additionally, when the seat-ready profile's environment is
built for the pytest subprocess, set `TMPDIR` to the user's `~/tmp` (expand `~` at
runtime) rather than the existing `/var/tmp` default; all other `_python_env` rules
remain unchanged.

I3 — Same file: add a seat-ready autogen repair gate that runs before the final
path-manifest gate, guarded by `config.profile == SEAT_READY_PROFILE`. For each
registered generator pair — `cli_reference_autogen_sync` / `scripts/gen_cli_reference.py
--write` / `.ce/reference/cli.generated.md` and `schema_reference_autogen_sync` /
`scripts/gen_schema_reference.py --write` / `.ce/reference/schemas.generated.md` — use
the existing check module's source-surface detection to determine whether the
`base..HEAD` diff touches the corresponding surface; do not reimplement the surface
matcher. If a surface is touched, invoke the generator's `--write` mode, stage the
checked artifact if it changed (`git add`), and recommit before the final byte-parity
pass. The final byte-parity pass must run the registered check in read-only verify mode,
not trust timestamps. If the generator cannot run due to missing environment deps,
classify as `ENV-SKIP` for that specific artifact and surface it in the check output;
carrier fidelity, changelog presence, and declared work class are never `ENV-SKIP`.
Tooling error (non-ENV-SKIP) is treated as FAIL and triggers BLOCKED, not READY.

I4 — `validators/tests/unit/test_ce_validate_pr_cli.py`: add tests covering:
`--profile seat-ready` is accepted and dispatched with `profile="seat-ready"` in the
captured args; `--profile bogus` still exits 2; `"seat-ready"` is a member of
`VALIDATE_PR_PROFILES`; `seat-ready` does not appear in `--help` output (profile flag
remains suppressed).

I5 — `validators/tests/unit/test_pr_preflight.py`: add tests covering:
`_validate_profile("seat-ready")` does not raise; `seat-ready` profile does NOT emit
the contained-seat carrier notice and does NOT classify `path_manifest_carrier_required`
as omitted; the seat-ready test command default contains `-n 4` and does not contain
`-n auto`; the autogen repair gate is triggered only when the profile is `seat-ready`
and a registered source surface is in the diff, not on `contained-seat` or unprofile
runs; ENV-SKIP classification is emitted (not silently swallowed) when the generator
environment is absent.

No other files are in scope. Do not modify `validators/creator_engine_validator/check_profiles.py`
(that module serves `ce check --profile`, not `ce validate-pr --profile`); do not
modify the autogen check modules, the generator scripts, or any other validator source.

EVIDENCE: changelog fragment `.ce/changelog/ce-499-seat-ready-profile.md`; carrier at
`.ce/pr-manifests/ce-499-seat-ready-profile.md` with slug equal to branch name, file
self-inclusive, changelog path included, `AUTHORIZED_PATHS_COUNT` and
`AUTHORIZED_PATHS_SHA256` computed over the real `base..HEAD` diff; carrier body
contains exactly one line `- **Declared work class:** S`.

Standing preflight directive (ce-ops#303): FULL `ce validate-pr` (CI parity) before
commit-for-harvest. Because this unit introduces the `seat-ready` profile itself, run
the final preflight pass as `ce validate-pr --profile seat-ready` to exercise the new
profile against the live branch diff. pytest worker cap for this run: `-n 4`;
`TMPDIR=$HOME/tmp`. ENV-SKIP fallback: if the full profile cannot complete, emit
`BLOCKED ce-499-seat-ready-profile <reason>`; do not emit READY on a partial run.
Do not discover gates via CI.

STOP LINE: `validators/creator_engine_validator/pr_preflight.py`,
`validators/tests/unit/test_pr_preflight.py`,
`validators/tests/unit/test_ce_validate_pr_cli.py`,
`.ce/changelog/ce-499-seat-ready-profile.md`,
`.ce/pr-manifests/ce-499-seat-ready-profile.md` — and nothing else. No changes to
`deploy/dgx-runsc/*` (those paths carry unrelated local modifications in the controller
root checkout; the seat's base is origin/main, and those paths are not touched by this
design). No changes to live seat containers, launcher, or deployment configuration.
No approval, merge, enqueue, gate action, signing, or push of any kind.
