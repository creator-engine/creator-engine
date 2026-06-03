# PR path manifest — v3 G-1.3b (classifier + backend-agnostic audit overlay)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR adds the v3 **G-1.3b** classifier + audit overlay: a PURE
`classify(event, runtime_policy) -> {allowed|denied|escalate}` policy decision
point evaluated against the G-1.0 `ce_runtime_policy` record, and an
`AuditOverlayBackend(RunnerBackend)` **decorator** that wraps any backend and
attests every provision/run/collect/teardown step (and every observed runtime
event) to a tamper-evident, hash-chained evidence record via the merged G-1.3a
`runtime_evidence_spine`, bound to the `policy_sha` it attests. Together with
G-1.3a this completes G-1.3 / G-1 (plane C).

The overlay is pure-in-process Python behind the adapter: it registers NO
validator check and NO `isolation_backend`, so `--list-checks` is **unchanged at
43** and `available_backends()` stays `('gvisor-proxy','local-noop')`. The
concrete backends and the G-1.0 deny surface are byte-untouched. No `ce_cli.py`/
wheel change (stdlib only).

- **base:** `6fe06cdfa0f9e816878ab0b322110c011b5ba3eb`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=43a88d3710358989a7bf99b0566defb1f3230a27f9778fbef170772be0a5eef6

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/audit_overlay.py
validators/tests/unit/test_audit_overlay.py
```
