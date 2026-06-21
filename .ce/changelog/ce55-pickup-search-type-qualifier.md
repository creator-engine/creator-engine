---
slug: ce55-pickup-search-type-qualifier
date: 2026-06-21
kind: fixed
scope: belt pickup feed
issue: ce-ops#55, ce-ops#182
---

Adds explicit GitHub Search type qualifiers to every pickup poll query.

- Keeps review-request pickup PR-only with `is:pull-request`.
- Splits assigned, mention, and label pickup across PR and issue queries so both
  surfaces remain covered without broadening the selector scope.
- Preserves repo/org scoping, label scoping, result normalization, and existing
  dedupe behavior.
