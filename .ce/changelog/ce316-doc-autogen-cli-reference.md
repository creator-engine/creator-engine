---
slug: ce316-doc-autogen-cli-reference
date: 2026-06-27
kind: added
scope: doc-autogen Tier-1 CLI-reference pilot
---

Adds the first slice of the CE doc-autogen program (Tier-1 pilot, ce-ops#316;
design `.ce/state/research/CE_DOC_AUTOGEN_DESIGN_20260627.md`): a deterministic
`ce --help` -> CLI-reference generator with a generate-then-verify CI guard.

- `scripts/gen_cli_reference.py` — pure `project(parser) -> markdown` over the
  `ce` argparse tree (introspected read-only; `ce_cli.py` untouched). `--check`
  (read-only, CI) regenerates and byte-diffs against the committed doc, failing
  closed on staleness; `--write` regenerates in place for developers. Internal
  command groups and `argparse.SUPPRESS`-helped commands are omitted exactly as
  `ce --help` presents them.
- `.ce/reference/cli.generated.md` — the generated, committed CLI reference
  (whole-file byte-parity), carrying a machine-readable `<!-- ce-autogen -->`
  provenance header. It lives in the INTERNAL `.ce/reference/` tree rather than
  the served public `docs/` tree because a faithful projection of every `help=`
  string carries internal references the read-only generator must not rewrite.
- A `@register`'d validator check (`cli_reference_autogen_sync`,
  `VAL-AUTOGEN-STALE-CLI`) that rides the existing `pull_request` gate so a
  stale committed reference cannot merge.

The projection normalizes the one environment-dependent default
(`validate-pr --test-command` embeds the running interpreter path) to a stable
`<python>` placeholder, keeping the render byte-identical across hosts and
Python versions.
