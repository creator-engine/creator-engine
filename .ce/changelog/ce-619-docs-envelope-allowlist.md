---
slug: ce-619-docs-envelope-allowlist
date: 2026-07-19
kind: fixed
scope: automerge policy — docs_envelope tier predicate
issue: ce-ops#619
---

**Close MC1 docs_envelope security hole: non-markdown executables no longer qualify for zero-gesture merge.**

Prior to this change `docs_envelope_tier_matches()` admitted any path whose
prefix began with `docs/` regardless of file extension, meaning an attacker
could craft a PR containing `docs/scripts/x.py`, `docs/hooks/x.sh`, or a
YAML workflow-like file and have it classify as the `docs_envelope` merge
class — qualifying for pre-delegated, zero-gesture merge when MC1 is armed.

- Added `_DOCS_ENVELOPE_ALLOWED_EXTENSIONS` constant (`.md`, `.txt`, `.html`,
  `.css`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`).
- Extracted `_docs_envelope_path_permitted()` helper: paths under
  `.ce/changelog/` and `.ce/pr-manifests/` pass by existing prefix rule; root
  `.md` files pass via `_root_markdown`; `docs/**` paths must carry an
  extension from the allow-list (case-insensitive); all other paths fail
  closed to GESTURE.
- `docs_envelope_tier_matches()` signature and return semantics unchanged;
  now delegates per-path logic to the new helper.
- `automerge_actuator.py` already imports and calls `docs_envelope_tier_matches`
  from `automerge_policy`; no logic duplication exists; no actuator change
  required.
- New tests: deny cases (`docs/scripts/build.py`, `docs/hooks/x.sh`,
  `docs/conf.yaml`, `docs/Makefile`), allow cases (`docs/guide.md`,
  `README.md`, `docs/img/logo.svg`, mixed valid set), and case-insensitive
  extension variants (`.PNG` allowed, `.PY` denied).
