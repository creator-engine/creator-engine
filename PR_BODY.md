## Summary

- Add a public-docs unit-test ratchet for `docs/operations/**` and `docs/delivery/**`.
- Seed explicit exception lists with the current files so future net-new files fail until moved or allowlisted.
- **Declared work class:** story

## Validation

- `PYTHONPATH=validators pytest -q validators/tests/unit/test_public_docs_confidentiality.py` - blocked locally: `pytest` command not found.
- `PYTHONPATH=validators python3 -m pytest -q validators/tests/unit/test_public_docs_confidentiality.py` - blocked locally: `No module named pytest`.
- Direct fallback invocation of all test functions in `validators/tests/unit/test_public_docs_confidentiality.py` - PASS.
- `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --base origin/main --declared-work-class story` - blocked locally: `ModuleNotFoundError: No module named 'yaml'`.
