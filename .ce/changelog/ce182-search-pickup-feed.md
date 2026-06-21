---
slug: codex-ce182-search-pickup-feed
ticket: ce-ops#182
type: feature
scope: belt pickup feed
---

Replaces the pickup feed's GitHub Notifications API poll with a Search API poll
so fine-grained, read-only PATs can drive the belt.

- Adds deterministic Search queries for review requests, assignments, mentions,
  and optional team labels, each mapped to the existing belt work-item shape.
- Uses stable synthetic `search:{reason}:{repo}:{kind}:{number}` thread ids so
  the dedup/claim ledger remains unchanged despite Search having no thread id.
- Fails closed with retry metadata on Search API 403/429 responses and supports
  `Retry-After` / rate-limit reset fields.
- Keeps launch disabled by default; the existing `--enable-launch` path remains
  gated and does not try to mark synthetic Search thread ids as notifications.
