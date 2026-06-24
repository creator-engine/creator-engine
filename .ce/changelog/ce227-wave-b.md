### ce-ops#227 — Wave-B: herdr send-keys Enter commit + sha256 verify-after-render delivery

- `HerdrSession.send` now commits input: after `pane send-text`, settle then a bounded `pane send-keys <id> Enter` loop, confirming via `recent-unwrapped` reads that the pending input line left the prompt; fail closed if uncommitted after N attempts (fixes the b′ "Enter doesn't commit" bug; ports the proven v3_seat_bridge submit cadence).
- New `HerdrSession.deliver_brief`: appends a `==CE-BRIEF-SHA256:<digest>==` marker, delivers via the committing send path, then polls `pane read` until the marker renders — fails closed if absent (fixes the b″ silent-no-op delivery; sha256 verify-after-render, no docker cp).
- All timing injectable (sleep/clock) for deterministic tests.
