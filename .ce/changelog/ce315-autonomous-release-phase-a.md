---
slug: ce315-autonomous-release-phase-a
date: 2026-06-27
kind: added
scope: validator CLI — autonomous release (CEO-mode) Phase A stage-to-seam
issue: ce-ops#315
---

**Autonomous release Phase A (stage-to-seam): three validator subcommands that
collapse the manual release-staging ritual to one command, stopping at the
Operator signing seam — no signing, no publish.**

- **`release-bump`** — tag-as-source-of-truth version bumper. Derives the
  target from a `release/vX.Y.Z` tag (or `--part {major,minor,patch}` for the
  rehearsal path), drives both canonical version sources (`version.py`
  `__version__` and `validators/pyproject.toml [project].version`) atomically,
  and asserts `tag_version == version.py.__version__` fail-closed — rolling
  both files back on any mismatch. Staged-only; nothing is committed.
- **`release-changelog`** — aggregates `.ce/changelog/*.md` fragments since the
  last `release/*` tag (all fragments when no release tag exists) into dated,
  kind-grouped release notes. `towncrier` is not available offline, so a
  minimal deterministic aggregator over the existing `{slug,date,kind,scope,
  issue}` front-matter is used (fragments without front-matter are still
  included). Read-only — no fragment is archived (that is Phase B publish).
- **`release`** — orchestrator chaining bump → changelog → the existing
  `release-stage`, producing the fully-staged, signature-SHAPED artifact with
  the unchanged placeholder signature, and surfacing the ratification packet
  (canonical bytes, stage manifest, signing instructions, one command) the
  Operator signs offline. Fail-closed, `--dry-run`.

The existing `release-stage` root-signing HARD REFUSAL
(`release_publish.py:89`) is preserved untouched; these subcommands wrap it and
add no signing or publishing path. (Workflow trigger, tag ruleset, and the
post-signature publish/verify automation are deferred Phase A4-A5 / Phase B.)
