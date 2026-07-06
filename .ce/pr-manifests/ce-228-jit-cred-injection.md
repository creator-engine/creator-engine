## Summary

- add `mint-seat-credential` / `revoke-seat-credential` handling to the egress host broker
- add per-seat allowed credential class config and a JIT credential store with flock-serialized single-active state
- cover no env/Docker delivery, unknown-class refusal audit, TTL expiry, concurrent mint serialization, and forge-scoped token reuse

## Validation

- `python -m pytest validators/tests/unit/test_jit_credential_broker.py validators/tests/unit/test_egress_host_broker.py`
