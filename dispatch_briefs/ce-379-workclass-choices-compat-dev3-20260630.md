# SEED BRIEF — work-class validator choices back-compat (migration window) — SEAT: dev-3

**Branch:** `ce-379-workclass-choices-compat` off CURRENT origin/main (you were just refreshed to 642a2fd9). **Role:** implementer. **Work class:** declare by diff floor (likely XS/S; the body parser already accepts these post-rename).

## Problem (self-contained — do NOT rely on reading any private ticket)
The work classes were recently renamed to **XS / S / M / L** (legacy names `tiny / story / feature / epic` are kept as back-compat aliases). The FORGE work-sizing-floor CI gate reads a PR body's declared class, **normalizes a legacy name to its new canonical name** (e.g. `story`→`S`), then calls the validator CLI `verify-work-sizing-floor --declared-work-class <normalized>`.

BUG: the validator CLI's `--declared-work-class` argument still uses a hard `choices=` list that only contains the LEGACY names (`tiny, story, feature, epic`) in some code paths, so when it receives a NEW canonical name like `S` it dies with:
`error: argument --declared-work-class: invalid choice: 'S' (choose from 'tiny','story','feature','epic')`
This breaks the gate for any branch whose validator predates the rename, and is an opaque failure. The same class of bug exists in `pr_preflight.build_parser` (its `choices` rejects legacy names on a direct module call).

## Fix (migration-window: accept BOTH old and new)
1. Find every `argparse` `--declared-work-class` (and any related work-class) argument whose `choices=` is a fixed list. Search the validator package (e.g. `validators/creator_engine_validator/`) — likely in the work-sizing-floor CLI and in `pr_preflight.build_parser`. Use the canonical work-class definitions already in the codebase (there should be a `WORK_CLASSES` constant / alias map introduced by the rename) rather than hardcoding.
2. Make `choices` (or validation) accept **both** the new canonical names (XS/S/M/L) **and** the legacy aliases (tiny/story/feature/epic), normalizing internally to canonical. Reuse the existing alias map — do NOT duplicate it. If no shared constant exists, prefer wiring to the one the body-parser/rename already uses.
3. Keep behavior otherwise identical (floors, LOC metric, error messages for genuinely-invalid values unchanged).

## Tests
- Add/extend unit tests proving: passing `S` (and `XS/M/L`) is accepted; passing a legacy alias (`story`, etc.) is accepted and normalizes to the same result; a genuinely bogus value (e.g. `Z`) still errors.
- Run the FULL local preflight GREEN in ONE pass: `TMPDIR=/var/tmp .venv/bin/python -m pytest -q <the relevant test files>` and, if available in your checkout, `TMPDIR=/var/tmp .venv/bin/ce validate-pr` (use TMPDIR=/var/tmp; venv has no activate → call `.venv/bin/python`).

## Carrier / changelog
Add `.ce/pr-manifests/ce-379-workclass-choices-compat.md` (carrier_gen, stem == branch slug) + `.ce/changelog/ce-379-*.md`; carrier path-set must equal base..HEAD.

## Stop line
Commit with `git commit && echo <SHA>` (you have NO push auth in-container — that's expected; the controller harvests). Report: the SHA, files changed, the alias/constant you reused, and preflight result. Do NOT push, approve, merge, or scope-creep beyond the choices fix + tests.
