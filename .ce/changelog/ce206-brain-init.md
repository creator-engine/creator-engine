---
slug: ce206-brain-init
ticket: ce-ops#206
type: feature
scope: ce brain init genesis bootstrap (CLI)
---

Adds an idempotent `ce brain init` CLI command that bootstraps a valid genesis
brain assertion ledger so a freshly-installed CE workspace comes up able to
pass `lane launch`'s `G3-BRAIN-BOOTSTRAP-REFUSED` gate with no hand-run step.

- `ce brain init [--state-root <path>]` writes a single deterministic genesis
  assertion (`brain-assertion-genesis-0001`, scope `global`) to
  `<state-root>/brain/assertions.yaml` via the SSOT `assert_claim` write path,
  so `brain_runtime.verify_ledger()` returns `ok=True` afterward. The default
  `--state-root` (`.ce/state`) mirrors the resolution the sibling brain
  commands use.
- Idempotent: if a VALID ledger already exists, `init` is a byte-preserving
  no-op (exit 0, "already initialized") — it never appends a duplicate genesis
  or rewrites the ledger.
- Fail-closed: if a ledger file exists but is corrupt/invalid/conflicting
  (e.g. a tampered hash chain or a non-mapping file), `init` REFUSES with
  `CE-BRAIN-INIT-REFUSED` and a non-zero exit, and never overwrites it.
- `--json` emits a machine-readable record (`created`/`already_initialized`/
  `genesis_id`/`record_count`/`head_content_hash`) matching the sibling brain
  command output conventions; the human output mirrors `ce brain assert`.

Wired alongside the existing `ce brain` subcommands (`bootstrap`/`assert`/
`verify`/…) via the same argparse subparser + `_BRAIN_DISPATCH` style. No
change to `brain_bootstrap()` (which still requires an existing valid ledger);
`init` uses the assert/genesis path so it works on an empty/absent ledger.
