# SEED BRIEF — ce-ops#322: schema-reference doc-autogen generator (dev-4)

**Seat:** dev-4 (contained ce-dgx-codex). **Role:** implementer. No-egress — everything needed is embedded or in-repo; do NOT fetch external tickets.

## Ticket (ce-ops#322, embedded)
Build the **second Tier-1 doc-autogen generator** (epic ce-ops#312). Mirror the EXACTLY-established pattern of the MERGED first one — **`scripts/gen_cli_reference.py`** (PR #581 / ce-ops#316), which projects the `ce` argparse tree → `.ce/reference/cli.generated.md` with `--check`/`--write` and a validator `@register` gate. READ that generator + its registration + its test first; copy its structure.

**This slice's source:** the committed **`schemas/*.yaml`** JSON-schema set (~40 schemas) → a deterministic **schema reference** markdown. Pure `project(schemas) -> markdown` (file→text only; NO live-host/fleet/network probing — that's Tier-2, OUT of scope).

## Deliverables (mirror #581 structure)
- `scripts/gen_schema_reference.py` — pure `project(schemas) -> markdown`; `--check` mode (CI: fail-closed/non-zero if the committed doc is stale) and `--write` mode (dev: regenerate). Deterministic (sorted keys, fixed templates; no time/random).
- The generated doc (follow #581's location convention, e.g. `.ce/reference/schema-reference.generated.md`) with the same autogen header marker #581 uses.
- Register the generator behind the validator `@register` gate (same mechanism #581 used) so a STALE committed reference FAILS the `pull_request` gate (generate-then-verify per-merge).
- A unit test mirroring #581's generator test (determinism + `--check` catches staleness).

## Process
- Branch `ce-322-schema-reference-gen` off current `origin/main`.
- Add changelog `.ce/changelog/ce-322-schema-reference-gen.md`. Regen carriers via `carrier_gen.write_carriers(base=<merge-base>)` (dashed slug); rm build/egg-info first.
- FULL validate-pr GREEN one-pass: `TMPDIR=/var/tmp PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --head-ref ce-322-schema-reference-gen`. If a NEW `ce` group/doc-coupling check trips, satisfy it (this IS a generator, so the autogen doc must be committed + fresh). RED → STOP + report.
- STOP at READY-FOR-HARVEST (contained — do NOT push). Report: branch + full SHA + merge-base + changed-paths + validate one-line result. Declared work class: likely `story`.
