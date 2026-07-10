# DISPATCH — dev-3 — 2026-07-10 — unit: seat launch configs default to gpt-5.6-terra — class XS
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-terra-default-flip <full-40-hex-sha>`
or `BLOCKED ce-terra-default-flip <one-line-reason>`.
Branch `ce-terra-default-flip` off freshly fetched origin/main OR LATER. Worktree
/var/tmp/wt-ce-terra-default-flip. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (product lens)
The fleet's ratified seat default model moved from gpt-5.5 to gpt-5.6-terra at effort high.
The seats were relaunched with argv overrides to land on the ratified default; however, the
repo's launcher configs still write the old default (gpt-5.5), so config and policy have
drifted. This unit flips the repo defaults so a plain launch (without argv overrides) lands
on the ratified default: gpt-5.6-terra with model_reasoning_effort = "high".

## Unit
1. In `deploy/dgx-runsc/run-codex-runsc.sh` and `deploy/vps-runsc/run-vps-runsc.sh`, find
   every hardcoded model default: the generated codex config heredoc lines `model = "gpt-5.5"`
   and any `-m gpt-5.5` fallback argv defaults. Change all to `gpt-5.6-terra`, keeping
   `model_reasoning_effort = "high"` unchanged.
2. grep the two launchers plus their README files for other stale gpt-5.5 default references
   and update those lines only (no behavioral changes, config-text-only).
3. If a test asserts the generated toml content (search `validators/tests/` for
   `run-codex-runsc`, `run_vps_runsc`, `dgx_runsc`, `vps_runsc` launcher tests mentioning
   `gpt-5.5`), update those assertions to the new default — assertion-tracking only, never
   delete a test.

## Files (allowed writes)
`deploy/dgx-runsc/run-codex-runsc.sh`, `deploy/vps-runsc/run-vps-runsc.sh`, their README.md
files if stale references exist, matching launcher test modules under `validators/tests/`
that mention the old default, `.ce/changelog/ce-terra-default-flip.md`, and carrier
`.ce/pr-manifests/ce-terra-default-flip.md` (slug=branch) with exactly:
`- **Declared work class:** XS`. Product lens; no internal ticket numbers.

## Stop lines
Everything else — especially `tools/**`, `validators/creator_engine_validator/**` (non-test),
`ce_cli.py`, `docs/llms-install.md`, `install.sh`, `.ce/brain/assertions.yaml`, `.github/**`.
Do not edit model selection logic, effort logic, or runtime dispatch — this is config-only.
