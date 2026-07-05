---
slug: ce-seat-image-digest-pin-0-3-2
date: 2026-07-05
kind: fix
scope: validators
issue: ce-ops#823
---

**Pin the 0.3.2 tenant seat image manifest-list digest and retire its unset-digest allowlist.**

- Record surfaces/manifest.yaml CE seat image entry with the published ghcr.io/creator-engine/creator-engine/ce-seat:0.3.2 manifest-list digest (built from release/v0.3.2 commit ec81737e8f99e42ec68f4c9dd92d7e8c5a848c5e), replacing the UNSET placeholder.
- Retire the now-satisfied UNSET_DIGEST_ALLOWLIST tuple in validators/creator_engine_validator/checks/surfaces_manifest.py so the seat image surface can never regress back to unset.
- Update the unit tests that asserted the allowlist tuple and the unpinned manifest entry shape to match the pinned state.
- Fix test_onboard_apply.py to derive the expected image_ref dynamically from _canonical_seat_image_ref() (surfaces/manifest.yaml SSOT) instead of a hardcoded placeholder literal.
