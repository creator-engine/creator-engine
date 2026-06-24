---
slug: ce-search-api-headroom
date: 2026-06-24
kind: added
scope: validator engine Search API pollers
---

Adds shared Search API headroom for parallel CE pollers.

- Introduces a boundary-neutral file-backed Search API limiter with jittered
  retry/backoff and a v3 forge wrapper so v1 pickup does not import forge.
- Wires live/default Search API REST calls and v3 GraphQL search discovery
  through the limiter while preserving offline fake-transport seams.
- Keeps daemon loops alive after exhausted Search rate-limit retries, logging a
  bounded rate-limit event instead of hard-crashing.
