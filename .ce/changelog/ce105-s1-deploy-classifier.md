---
slug: ce105-s1-deploy-classifier
date: 2026-06-17
kind: added
scope: runner / Ring-1 deploy classifier hardening
base: 58990ff0ef3d649d25b6874340b3c1c6364702b3
---

Hardens the shared Ring-1 git-subcommand deploy classifier (ce-ops#105 Scope-2
S1) so more outward mechanics are caught before the real binary runs, and adds a
distinct deny exit code for observability. Additive and low-blast-radius;
mirrors #242.

- Classifies `git send-pack` as `deploy` (a first-class outward verb alongside
  `push`).
- Classifies the foreign-VCS bridges' only outward sub-verbs — `git p4 submit`
  and `git svn dcommit` — as `deploy`, while leaving their read sub-verbs
  (`git p4 sync`, `git svn fetch`, any other) allowed. An absent or unparseable
  bridge sub-verb falls conservative (treated as the outward sub-verb → deploy).
- Adds an abbreviation guard: an unknown subcommand that is a UNIQUE prefix of a
  restricted verb (`push`, `send-pack`, `branch-delete`) is classified as that
  verb's mechanic (e.g. `git pus` → deploy), removing the dependency on git's
  autocorrect. An ambiguous prefix (matching more than one restricted verb) or a
  plain non-prefix unknown stays unclassified (allow). The guard applies only to
  directly-typed unknowns; an unknown reached via alias resolution stays
  conservative (`git_opaque`).
- Added `DENY_EXIT_CODE = 121` to `ring1_tool_guard` (distinct from shell exit
  126, "command found but not executable"), so a CE Ring-1 denial is observably
  distinct from a real exec failure. Observability only — the deny semantics are
  unchanged; only the emitted exit-code value differs.
- Added both-direction unit coverage: DENY → deploy for `git send-pack`,
  `git p4 submit`, `git svn dcommit`, the unique-prefix `git pus`, and an alias
  that expands to a restricted verb; ALLOW-regression for `git p4 sync`,
  `git svn fetch`, `git status`, `git log`, and a plain non-prefix unknown.
- Rebuilt the validator app wheel from current source (`setuptools.build_meta`)
  and refreshed `validators/wheelhouse/SHA256SUMS` (only the app-wheel line).
  `_version.py` is untouched — S1 registers no new runtime tool, so there is no
  version bump (`test_version_boundary` stays green; no `V3_RUNTIME` collision
  with the parallel #246 branch).

No new mutation-class vocabulary is introduced: all outcomes reuse the existing
`deploy` / `alter_repo_settings` labels (and `git_opaque`). The hardening adds
no over-denial — every read/inward path and non-prefix unknown stays allowed.
