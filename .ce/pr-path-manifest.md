# PR path manifest — v3.5-C N1-CARVEOUT (honest `quorum: n1_solo`)

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

Ratified gate:
`~/ce-launch/v35c-n1-wave/GATE_N1_CARVEOUT_composed.md`
(sha256 `64e0346b4137193af72c819dda66d0761e7cd806cb75fb8e7f3f9932bbaf5d73`; Fork A no-cooling-off,
Operator-ratified v1+v2 2026-06-10, v3 wheelhouse amendment 2026-06-11).

Per-file purpose (the §3 closed manifest):
- **`schemas/coordination-policy.schema.yaml`** *(M)* — optional `quorum: n1_solo` on
  `ratifications[]` entries; `quorum_by_tier.privileged` stays >= 2, `no_self_approval` const true.
- **`schemas/decision-record.schema.yaml`** *(M)* — optional `ratification.quorum: n1_solo`.
- **`validators/creator_engine_validator/checks/peer_authority.py`** *(M)* — exact-one-human
  validity, auto-expiry at >= 2 humans (`VAL-PA-N1-SOLO-EXPIRED`), required solo marker /
  laundered-quorum guard (`VAL-PA-N1-SOLO-REQUIRED`), `quorum_mode` on the grader, and the
  map-sensitive Decision-Record cross-scan (scoped by `area_owners`); no-self unchanged.
- **`validators/creator_engine_validator/checks/decision_record.py`** *(M)* — local shape guard
  `VAL-DR-N1-SOLO-MISUSED` (marker only on accepted privileged records); self-ratification unchanged.
- **`docs/contracts/peer-authority.md`** *(M)* — N=1 native-mode contract, `n1_solo` semantics,
  auto-expiry, no-self/fail-closed non-bypass, new codes.
- **`docs/contracts/decision-record.md`** *(M)* — `ratification.quorum: n1_solo` documentation +
  `VAL-DR-N1-SOLO-MISUSED`.
- **`.ce/coordination.yml`** *(M)* — comment-only ride-along: privileged solo ratifications are
  recorded as `quorum: n1_solo`, not as quorum 2; no threshold lowering.
- **`validators/examples/peer-authority/n1-solo-valid/coordination.yml`** *(NEW)* — one-human policy.
- **`validators/examples/peer-authority/n1-solo-valid/ADR-0201-n1-solo.md`** *(NEW)* — valid solo DR.
- **`validators/examples/peer-authority/n1-solo-two-humans/coordination.yml`** *(NEW)* — two-human policy.
- **`validators/examples/peer-authority/n1-solo-two-humans/ADR-0202-n1-solo-expired.md`** *(NEW)* —
  same `n1_solo` claim under two humans; must fail (auto-expiry).
- **`validators/examples/peer-authority/n1-solo-laundered-quorum/coordination.yml`** *(NEW)* —
  one human with two account labels.
- **`validators/examples/peer-authority/n1-solo-laundered-quorum/ADR-0203-laundered-quorum.md`** *(NEW)* —
  omits the marker, mimics quorum via account multiplicity; must fail (laundered quorum).
- **`validators/tests/unit/test_peer_authority.py`** *(M)* — N=1 pass/fail + regression tests.
- **`validators/tests/unit/test_decision_record.py`** *(M)* — `ratification.quorum` shape + no-self tests.
- **`docs/decisions/ADR-0001-public-private-storage-policy.md`** *(M)* — add
  `ratification.quorum: n1_solo` (canonical first consumer; without it the new
  `VAL-PA-N1-SOLO-REQUIRED` guard retroactively fails this committed accepted-privileged DR).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — rebuilt from
  THIS branch's source so the #185 wheel-matches-source oracle stays green (v3 amendment).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned to the rebuilt app wheel (v3 amendment).
- **`.ce/pr-path-manifest.md`** *(M)* — this carrier.

- **base:** `a79b1f0` (origin/main, head of #195).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=19

AUTHORIZED_PATHS_SHA256=f735e294ee69db6b82e9e0ebe0f29d339c68e329552f874186420523c250110e

```text
.ce/coordination.yml
.ce/pr-path-manifest.md
docs/contracts/decision-record.md
docs/contracts/peer-authority.md
docs/decisions/ADR-0001-public-private-storage-policy.md
schemas/coordination-policy.schema.yaml
schemas/decision-record.schema.yaml
validators/creator_engine_validator/checks/decision_record.py
validators/creator_engine_validator/checks/peer_authority.py
validators/examples/peer-authority/n1-solo-laundered-quorum/ADR-0203-laundered-quorum.md
validators/examples/peer-authority/n1-solo-laundered-quorum/coordination.yml
validators/examples/peer-authority/n1-solo-two-humans/ADR-0202-n1-solo-expired.md
validators/examples/peer-authority/n1-solo-two-humans/coordination.yml
validators/examples/peer-authority/n1-solo-valid/ADR-0201-n1-solo.md
validators/examples/peer-authority/n1-solo-valid/coordination.yml
validators/tests/unit/test_decision_record.py
validators/tests/unit/test_peer_authority.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
