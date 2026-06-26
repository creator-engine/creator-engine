---
slug: ce281-broker-optional-signature
date: 2026-06-26
kind: changed
scope: egress-broker / policy core (security)
issue: ce-ops#281
work_class: story
---

**Per-policy commit-signature requirement: OFF for contained seats (ce-ops#281).**

The egress-broker signature gate was previously mandatory for every seat. Contained seats
running in zero-key gVisor environments cannot sign commits (no GPG/SSH key available), which
blocked the host-side self-push path for those seats entirely.

**What changed:**

- Added `require_signed_commits: bool = True` to `BrokerPolicy` (default `True` preserves
  full back-compat for all existing configs and callers — fail-closed; omitting the key
  keeps the signature gate on).
- The config loader (`_build_policy`) parses the new field with a strict fail-closed rule:
  ONLY an explicit JSON `false` boolean opts out; `null`, `0`, empty string, and a missing
  key all resolve to `True`. A typo never silently disables the check.
- When `require_signed_commits=False`, the signature gate is SKIPPED and replaced with an
  explicit synthetic pass logged as "signature check disabled by policy
  (require_signed_commits=false)". ALL other gates — author allow-list, branch namespace,
  forbidden-branch, rate-limit, head-sha well-formedness, and preconditions — remain
  enforced without relaxation. The broker's own authorization boundary is the trust boundary.
- `apps.example.json` documents the field and provides an annotated contained-seat policy
  example with `require_signed_commits: false`.
- 34 new unit tests in `test_egress_signature_policy.py` cover: (a) `True` + unsigned →
  reject; (b) `False` + unsigned → allow; (c) `False` + bad author → reject; (d) `False` +
  forbidden branch → reject; (e) `False` + rate exceeded → reject; plus config-loader
  fail-closed parsing and decision serialization. Zero live crypto, network, or git calls.

**Security note:** When `require_signed_commits=False`, the skip is intentional and logged.
The author allow-list (exact email or GitHub no-reply login), branch namespace enforcement,
forbidden-branch gate, rate-limit, and head-sha well-formedness checks all remain active
and are NOT relaxed. The design is reviewed as part of the PR gate.
