---
slug: ce-434-contained-seat-profile
date: 2026-07-05
kind: feature
scope: governance
issue: ce-ops#434
---

**validate-pr contained-seat profile for harvest-side carriers.**

- Add `ce validate-pr --profile contained-seat`, a narrow profile that runs the normal preflight while tolerating only `path_manifest_carrier_required` because contained-seat carriers are generated harvest-side.
- Choose a named profile instead of a general skip flag so validate-pr stays fail-closed: unknown profiles are refused and no broad check-skipping surface is introduced.
- Keep the profile parseable but hidden from generated CLI help so the existing committed CLI reference remains unchanged.
- Keep default `ce validate-pr` behavior byte-identical with no profile, and cover the profile, notice line, and refusal paths in validate-pr tests.
