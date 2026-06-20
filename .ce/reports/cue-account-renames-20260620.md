# Completion report — CUE account renames (dogfood)

- **Envelope:** `.ce/envelopes/cue-account-renames-20260620.yaml` (sha256 `9a7e19b1…41526e`, RATIFIED 2026-06-20)
- **Tracking issue:** creator-engine/ce-ops#143 (companion schema gap: ce-ops#142)
- **Mechanic:** `account_rename` (computer-use / UI side-effect — no GitHub API exists for username changes)
- **Operator surface:** authenticated laptop Chrome, GitHub UI account switcher, driven via the `ce-browser` MCP only
- **Author / controller:** CE-DEV-2 controller; gh-authenticated forge identity `ce-overwatch` (id 150906340)
- **Executed:** 2026-06-20

## Closed-set result (no silent drops)

| From (old login) | To (new login) | Account id (identity preserved) | Status |
|---|---|---|---|
| `cedev1vps-cmd` | `ce-dev-1` | 292754681 | **DONE** |
| `ubuntuaws745-cmyk` | `ce-dev-2` | 286082568 | **DONE** |
| `cedev4vps-coder` | `ce-dev-4` | 294754021 | **DONE** |
| `chmod735` | `ce-overwatch` | 150906340 | **DONE** |
| `ce-dev-3` | — | 293633657 | **SKIPPED** (already conformant — out of scope) |

DEFERRED: none. HALTED: none (in the final run). No 2FA / sudo-mode / ambiguous dialog was bypassed at any point.

### Execution note (auth boundary honored)

The first attempt halted at a GitHub passkey 2FA challenge before any setting was touched — reported and paused, never bypassed (per the envelope's halt-and-escalate bound). The Operator completed authentication and made all four personas live in the GitHub account switcher; execution then resumed and completed via in-UI account switching (no fresh profile, no API).

## Machine verification (reproducible)

Each `to` login resolves and each `from` login is vacated:

```
$ for u in ce-dev-1 ce-dev-2 ce-dev-4 ce-overwatch ce-dev-3; do gh api users/$u --jq '.login+" id="+(.id|tostring)'; done
ce-dev-1 id=292754681
ce-dev-2 id=286082568
ce-dev-4 id=294754021
ce-overwatch id=150906340
ce-dev-3 id=293633657

$ for u in cedev1vps-cmd ubuntuaws745-cmyk cedev4vps-coder chmod735; do gh api users/$u; done
# all → 404 Not Found (vacated)
```

The preserved account ids prove these are renames (same accounts), not new-account substitutions.

## Per-target evidence (screenshots, captured on the Operator laptop)

- `chmod735 → ce-overwatch`: `/tmp/chmod735-renamed-to-ce-overwatch.png`
- `ubuntuaws745-cmyk → ce-dev-2`: `/tmp/ubuntuaws745-renamed-to-ce-dev-2.png`
- `cedev1vps-cmd → ce-dev-1`: `/tmp/cedev1vps-renamed-to-ce-dev-1.png`
- `cedev4vps-coder → ce-dev-4`: `/tmp/cedev4vps-renamed-to-ce-dev-4.png`

Each shows GitHub's "Your account has been renamed" confirmation with the new login. Only the username was changed; no other browser/account setting was touched.

## Scoped re-point (this PR)

Tight + reviewable; historical records and test fixtures intentionally left unchanged (no blanket find/replace).

- **`.github/CODEOWNERS`** — the live, forge-enforced ownership gate, re-pointed to the new logins:
  `* @cedev1vps-cmd @ubuntuaws745-cmyk @ce-dev-3 @cedev4vps-coder` → `* @ce-dev-1 @ce-dev-2 @ce-dev-3 @ce-dev-4`
- **`.ce/coordination.yml`** — the live identity SSOT (`identity_map.humans[].github_logins`) plus its present-tense explanatory comment, re-pointed `chmod735 → ce-overwatch`, `ubuntuaws745-cmyk → ce-dev-2`. (`tenants/` holds no reviewer-identity SSOT files for these personas; this `identity_map` is the live binding.)

### Intentionally NOT changed (out of scope per the envelope)

- `docs/decisions/**` ADR provenance (`ratified_by: chmod735`, `consulted: [chmod735]`) — historical attestations; rewriting would falsify the record of who ratified.
- `examples/reviewer-triage/**`, `validators/examples/**`, `validators/tests/**` — example data and test fixtures.
- `.ce/changelog/**`, `.ce/pr-manifests/**` — historical logs.
- Descriptive doc prose hedged as "today" (e.g. `docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`) and illustrative CLI help text (`validators/.../v3_cli.py`) — narrative, not enforced identity bindings.
