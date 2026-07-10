---
slug: ce-453a-hashpin-hotfix
date: 2026-07-10
kind: fixed
scope: validate-pr / signed-artifact-pins / path-manifest-fidelity
issue: ce-ops#453
---

**Hotfix: signed-artifact-pins fails closed on real file; path-manifest scan counts negative fixtures as offenses.**

Two gate-side defects introduced by #935 are causing uniform branch-validate failures:

- **signed_artifact_pins (VAL-SIGNED-ARTIFACT-PINS-INVALID):** `_extract_signed_yaml` was
  calling `yaml.safe_load` on the entire HTML-comment body of `docs/llms-install.md`, including
  the human-readable prose paragraph that precedes the YAML block.  The prose contains
  colon-bearing text (e.g. `(no CE tooling: that is what breaks the bootstrap circularity)`)
  that YAML rejects as malformed mappings.  Additionally, the YAML section itself contains
  `python_requires: >=3.14` where `>` is inadvertently treated as a YAML block-scalar
  indicator.  Fix: skip the prose paragraph (non-blank lines before the first blank separator)
  and sanitize inline mapping values that start with `>` or `|` but are not valid YAML
  block-scalar headers before passing to `yaml.safe_load`.  A new `SPEC_WITH_PROSE` fixture
  and a live `docs/llms-install.md` test guard against regression.

- **path_manifest_fidelity (false offenses from negative fixtures):** the registered `run()`
  check's `_iter_documents` directory sweep included `examples/malformed/handoffs/*.md` —
  intentionally malformed fixtures (`count-mismatch.md`, `hash-mismatch.md`,
  `init-py-corruption.md`) designed to produce errors in the integration-test "malformed
  examples rejected" harness.  These files were producing false `path_manifest_count_mismatch`,
  `path_manifest_hash_mismatch`, and `path_manifest_init_py_corruption` offenses during the
  repo-wide scan.  Fix: add `_is_under_malformed_examples` guard in `_iter_documents` (follows
  the same convention used by `identity.py` and `sidecar_utils.py`).  The negative-fixture
  integration tests continue to pass because they pass each file as an explicit path, which
  takes the `root.is_file()` branch and is never filtered.
