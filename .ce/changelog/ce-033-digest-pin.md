---
slug: ce-033-digest-pin
date: 2026-07-06
kind: fix
scope: surfaces
issue: release-batch2-B1
---

**Pin the 0.3.3 runtime and tenant seat image manifest-list digests.**

- Record `surfaces/manifest.yaml` CE runtime image entry with `ghcr.io/creator-engine/creator-engine/ce-runtime:0.3.3` index digest `sha256:8f584e11f565b530b69eed2ad740387a2a78ba4207bdd290960c06741a17fa57`.
- Record `surfaces/manifest.yaml` CE seat image entry with `ghcr.io/creator-engine/creator-engine/ce-seat:0.3.3` index digest `sha256:1def5b0cd1e5e465cb42fa73934bc6ee4b1c93fe005bbd7d111a4589dc96b698`.
- Update the seat image static test assertion to match the pinned 0.3.3 manifest entry.
- Controller-provided child digests were not used as manifest pins: `ce-runtime` amd64 `sha256:1bcf34def58c9e3b13306c81fa3537e3ef1061c64e12b2901d44b7a9406b4aa5`, `ce-runtime` arm64 `sha256:9d9791828149a98ccd42e3780e4085da0964378a16a927abe6b80c1428132648`, `ce-seat` amd64 `sha256:333c005cadbaa844a8c2f0f33b484a2436386a5dc4d39163e22eb67744aeef8a`, and `ce-seat` arm64 `sha256:692c4d0c33c83d20a66dad77db7a21faff8475768b5921c74017218c32ae916a`.
