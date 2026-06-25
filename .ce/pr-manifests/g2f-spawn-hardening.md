# PR path manifest — ce-ops#16 · v3.1-G2f venue/seat spawn hardening (roadmap W2)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref g2f-spawn-hardening
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED ce-ops#16 rev-2 gate spec
(`designs/ce-16-spawn-hardening-gate-spec-DRAFT-20260612.md`, sha `462ac5e5…`); the
ratification comment resolved all six open questions — venues UNATTENDED-by-default with
`--no-unattended` opt-out (Q4); seat env files refused unless owner-only/0600-class (Q1);
readiness poll 30s default (Q2); hard-fail-over-guess at collect with `--transcript-override`
kept (Q5); F6 merge head-override + F8 durable credential fix deferred to named follow-ups
(Q3/Q6). The combined-source wheel rebuild + `SHA256SUMS` re-pin after the #21 landing is
pre-authorized by the ratification (a content-pin change, declared in §9 of the spec).

Base:
`0e379d91751834af8f792466da3fc4289331a3ef` (origin/main = #206, the ce-ops#21 per-PR
carrier migration; the §9 re-ground confirmed #21 has MERGED → post-#21 carrier form, the
legacy shared `.ce/pr-path-manifest.md` already retired in #206 and absent from this diff;
the §2 grounding line-anchors on the five source modules hold at this base — no unlisted
drift).

Scope adjudication (IN, the demo-critical subset): F3 unattended reviewer venues (D1) ·
F4 reviewer-credential exec-wrap (D2-a) · F5 absolutized state-root refs (D3-a) · F7
Cockpit LIVE chains `RUNS_SUBDIR` (D4) · F9 stamped `harness_session_id` + exact-key collect
(D6-a) · G1-followups PATH preflight + seed readiness poll + send-keys rc (D5) · F8
docs-only declared-pre-push note (D7). F6 + F8's durable fix + G1-codex + escalation-sync
labeling are explicitly OUT (deferred per §3).

Per-file purpose (the closed path-set — 15 paths, as ratified §5; the carrier path swapped
to the per-PR form per §9):
- **`.ce/pr-manifests/g2f-spawn-hardening.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — D1 unattended-venue
  argv · D3 absolutized refs (`Path(root).resolve()`, + `unattended` param on
  `materialize_review_dispatch`) · D5 PATH preflight + seed readiness poll + send-keys rc
  checks · D6 `harness_session_id` mint/stamp + `--session-id` on both spawn argvs + brief
  text · D2 `seat_env_file` pass-through + recorded path ref · corrected F4 docstring.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* — D2 `seat_env_file`
  validation (owner-only) + exec-wrap between the Ring-0 pin and the resource-bound wrap.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — D2 `--seat-env-file` flag on
  `lane launch`, threaded to `lane_runtime.launch`.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — D1 `--no-unattended` + D2
  `--seat-env-file` on the `review` parser, threaded to the bridge · D6 collect transcript
  resolution (stamped-key lookup, mismatch refusal, `--transcript-override`,
  `--claude-config-dir`, `transcript_source` stamp; outcome determined before resolution).
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — D4
  `RUNS_SUBDIR` constant + call-site fix + `load_chains` docstring.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — §6 tests (unattended pair,
  absolute refs, preflight refusal, readiness poll + timeout fail-closed, send-keys
  failure, session-id stamp, seat-env-file pass-through).
- **`validators/tests/unit/test_lane_runtime_reviewer_venue.py`** *(M)* — §6 tests
  (seat-env wrap shape + secret-not-in-argv, refuse missing/world-readable, wrap inside the
  resource-bound wrap).
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — §6 tests (review `--no-unattended` +
  `--seat-env-file` threading; collect stamped resolution / mismatch refusal / override /
  unstamped conservation) + collect-test migration to the stamped-key resolution path.
- **`validators/tests/unit/test_cockpit_readmodel.py`** *(M)* — §6 test (chains read from
  `<root>/runs/`, not directly under `<root>`) + fixture migration to the runs subdir.
- **`schemas/dispatch-record.schema.yaml`** *(M)* — additive OPTIONAL properties on the
  CLOSED schema (`harness_session_id`, `transcript_source`, `seat_env_file_ref`); no new
  required field; `schema_version` stays `"1"`; old records validate byte-unchanged
  (repo-root schema — NOT wheel-shipped, no packaging impact).
- **`docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`** *(M)* — D7 (F8) declared
  pre-push limitation/procedure note (§i); docs-only disposition, zero code.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — wheel
  rebuilt from this branch's source (all five source modules are wheel-shipped; the
  packaging contract byte-checks bundled `.py` against source).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.
- **`docs/v3-roadmap.md`** *(M)* — the v3.1-G2f gate-status row.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=5057d6f94f86ed3364b40faae1ce70a2416c0341de4ea37a82b3009d2f83d439

```text
.ce/pr-manifests/g2f-spawn-hardening.md
docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md
docs/v3-roadmap.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_cockpit_readmodel.py
validators/tests/unit/test_lane_runtime_reviewer_venue.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_seat_bridge.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
