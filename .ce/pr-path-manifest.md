# PR path manifest — v3 G-1.3a (hash-chained evidence-spine substrate)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR adds the v3 **G-1.3a** evidence-spine substrate: a tamper-evident,
append-only, content-addressed **hash-chained runtime-evidence** record chain
(`schemas/runtime-evidence.schema.yaml` + the PURE
`runtime_evidence_spine.append`/`verify_chain` substrate), validated by a new
`@register`-ed `ce_runtime_evidence` dogfood check. Each record is content-
addressed and chain-linked, anchored to the runtime-policy it attests via
`policy_sha`. Reuses the proven `ce-event-block` / side-effect-ledger hash-chain
discipline; pure (no container/subprocess/socket/disk). The classifier + audit
overlay over the RunnerBackend lifecycle is the deferred G-1.3b slice.

This registers a new validator check, so `--list-checks` changes **42 → 43**
(`test_cli.py` updated accordingly). No `ce_cli.py` / wheel change (stdlib only).

- **base:** `ae2315baae4cc672fa921c7ee17e349e7b5a20e3`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=3b1a50a4fbe8717e346abb3c79cf3135be335470abf405f2cd4c077853cfbfc9

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-evidence.md
examples/malformed/runtime-evidence/broken-chain-link.yml
examples/malformed/runtime-evidence/mutated-content-hash.yml
examples/malformed/runtime-evidence/unbound-policy-sha.yml
examples/well-formed/runtime-evidence/example-runtime-evidence-chain.yml
schemas/runtime-evidence.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_runtime_evidence.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/integration/test_ce_runtime_evidence_examples.py
validators/tests/unit/test_ce_runtime_evidence.py
validators/tests/unit/test_cli.py
```
