### ce-ops#229 — live-action GitHub query must declare scope or fail closed

- Extract a shared `pickup_search.py` chokepoint (classified `shared`, neither V1 nor V3 runtime — stdlib-only, respects the v1⊥v3 boundary) carrying `SearchScope`, `declared_search_scope`, and `build_scoped_search_query`.
- Every live-action Search-API query builder must now pass an explicit `scope=` — constructing a token-scoped query without a declared scope fails closed rather than silently running unscoped. Closes the unscoped-by-default belt hazard (same class as the #412/#411 belt bugs).
- Route the v1 work-poller (`pickup.py`), v3 review-pickup (`forge/review_pickup.py`), and eviction detection (`forge/eviction_detection.py`) through the chokepoint with explicit scopes.
