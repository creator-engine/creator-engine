# BATCH ADDENDUM — dev-4 — queue after your review-analysis of #859
Foreman fan-out, standing rules per unit (fresh main, validate-pr GREEN, carrier, changelog, G5 line), COMMIT-ONLY → controller harvests, READY <sha> per unit.
UNIT B1 — 0.3.3 digest pin (analog of 0.3.2's PR #841 — read its merged diff for the exact shape): pin the freshly published 0.3.3 image digests wherever #841 pinned 0.3.2's. Controller-resolved values (embed verbatim, do NOT re-resolve):
  ce-runtime:0.3.3 index sha256:8f584e11f565b530b69eed2ad740387a2a78ba4207bdd290960c06741a17fa57 (amd64 sha256:1bcf34def58c9e3b13306c81fa3537e3ef1061c64e12b2901d44b7a9406b4aa5, arm64 sha256:9d9791828149a98ccd42e3780e4085da0964378a16a927abe6b80c1428132648)
  ce-seat:0.3.3 index sha256:1def5b0cd1e5e465cb42fa73934bc6ee4b1c93fe005bbd7d111a4589dc96b698 (amd64 sha256:333c005cadbaa844a8c2f0f33b484a2436386a5dc4d39163e22eb67744aeef8a, arm64 sha256:692c4d0c33c83d20a66dad77db7a21faff8475768b5921c74017218c32ae916a)
  Branch ce-033-digest-pin, class tiny (match #841's class if different).
UNIT B2 — ce-ops#426 (G11): read the ticket; if its #837-adjacent file preconditions are now settled on main, implement per ticket in its own worktree; if still blocked, report BLOCKED with the specific unsettled files and stop.
Territory: surfaces/manifest.yaml is YOURS (B1); do not touch README/deploy version refs (dev-3), install chain files (⛔ sha-pinned → STOP), brain_append_*.
