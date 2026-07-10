# BRIEF — ce-440-s3c — align migration-guide systemd snippets with the S3b unit migration

Role: implementer (dev-1 self-push). Branch: `ce-440-s3c-migration-doc-snippets` off freshly-fetched
origin/main (MUST include the s3b merge — verify deploy/systemd/ce-integrator-daemon.service:11 says
`/usr/bin/env ce ` at your branch tip; if not, fetch again or signal BLOCKED).

## Deliverable (3 lines; flagged non-blocking in the #785 review)
docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md — the "After" prose already says `ce`, but the
systemd unit snippets still show cev3:
- line ~42: `ExecStart=/usr/bin/env cev3 queue-daemon ...` → `ce`
- line ~47: prose "can resolve the installed `cev3` script" → `ce`
- line ~66: `ExecStart=/usr/bin/env cev3 review-pickup ...` → `ce`
Match the snippets to the actual unit files at your branch tip (copy the real lines). Touch NOTHING
else in the file ("Before" blocks stay cev3 by design — they document the old state).

## Constraints
- Files (closed set): docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md ·
  .ce/changelog/ce-440-s3c-migration-doc-snippets.md · .ce/pr-manifests/ce-440-s3c-migration-doc-snippets.md.
- Public-docs product lens: no internal ticket refs in the doc body.
- ⛔ Signed-artifact stop-line: any signature-gate failure → STOP + report bytes; never sign.
- Carrier via carrier_gen API, stem == branch. Changelog required (issue: ref in frontmatter only).

## Preflight
FULL `ce validate-pr` GREEN one pass before push.

## PR + evidence
PR to main, title `docs: align dogfood-migration systemd snippets with the unified ce surface`.
Body: exactly one `- **Declared work class:** tiny` line. Signal:
`READY-FOR-HARVEST ce-440-s3c-migration-doc-snippets <40-hex sha> PR #<n>`.

## Stop line
No approve/merge/enqueue/self-review. Controller reviews.
