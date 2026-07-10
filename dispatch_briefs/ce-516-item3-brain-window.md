---
brief_id: ce-516-item3-brain-window
ticket: ce-516-item-3
branch: ce-516-item3-brain-window
role: implementer
worktree: /home/ce-dev-2/creator-engine/.ce/wt-ce-516-item3-brain-window
base: origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c
declared_work_class: story
brain_window: exclusive
---

# ce-516 Item 3 — fail-closed workflow comment + record-65 correction

Follow `.claude/agents/implementer.md` exactly. Work only in the allocated
worktree and only on the closed path set below. Do not use network egress,
credentials, controller keys, signing material, Docker, push, PR, approval, or
merge authority. Commit for controller harvest only.

## Ground truth

Items 1, 2, and 4 of ce-516 merged in PR #923. Only Item 3 remains: the
workflow comment still says the bot is fail-open even though the script now
emits `::error::` and returns nonzero when the cross-repository token is absent.

Behavioral novelty check: inspect the comment block in
`.github/workflows/ce-ops-autoclose.yml`. If it no longer contains the stated
fail-open claim, STOP and report the exact current text; do not use a bare
keyword hit elsewhere as an already-resolved verdict.

Pinned main facts, recomputed immediately before dispatch:

- main/head: `727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- workflow current SHA-256: `24882022b91f667b3c29f0fb8a0b9a7600cb87cada9ce4428b7584b3d8c7b282`
- authoritative ledger SHA-256: `ea7ae84c7a013ae855257f0b44ad253d0d3a800b30229f557eedbc725881b348`
- ratchet-test SHA-256: `9943126d7c37682c818f1ca521ce52ed492d930e3d5d947da9d3d956b4bc9643`
- ledger records/active/tail: `163 / 104 / sequence 162`
- active record: `brain-assertion-d1b-16-cross-repo-closes-bot-v2`, original
  sequence 65, whole-file evidence pin to the workflow
- expected workflow SHA-256 after the exact comment edit below:
  `ed1be82ac0a735fc4155633135ff2fdc25488c5bedf0c612041fb1d46ddae486`

## Closed path set

- `.github/workflows/ce-ops-autoclose.yml`
- `.ce/brain/assertions.yaml`
- `validators/tests/unit/test_ce_brain_drift.py`
- `.ce/changelog/ce-516-item3-brain-window.md`
- `.ce/pr-manifests/ce-516-item3-brain-window.md`

No other path is authorized. In particular, do not change workflow logic,
permissions, triggers, jobs, steps, `.github/scripts/ceops_autoclose.py`,
`validators/tests/unit/test_p2_acceptance_evidence.py`, brain probe/runtime
code, or any signed artifact. This unit does not perform the separate projection
migration; it minimally corrects the existing whole-file pin.

## Exact workflow edit

Replace only this comment:

```yaml
# Fail-open: if the secret is absent/empty the step logs a warning and exits 0,
# so this workflow never blocks a merge.
```

with:

```yaml
# Fail-closed: a missing cross-repo token emits an ::error:: and exits nonzero.
# continue-on-error keeps this cleanup job non-blocking; the script also invokes
# its governance-alert hook when a suitable alert token is available.
```

Verify the resulting workflow SHA-256 is exactly the expected value above. If
it differs, STOP before touching the ledger and report the hash and diff.

## Chain-safe record-65 correction

Use main-vintage code from this worktree for every brain command:

`PYTHONPATH=validators /home/ce-dev-2/creator-engine/validators/.venv-test/bin/python -m creator_engine_validator.ce_cli ...`

Do not hand-edit hashes or reorder/rewrite existing ledger entries. Run one
`brain correct` against the tracked ledger using `--state-root .ce`:

- supersede ID: `brain-assertion-d1b-16-cross-repo-closes-bot-v2`
- new ID: `brain-assertion-d1b-16-cross-repo-closes-bot-v3`
- scope: `doctrine/day1`
- statement: preserve the current statement exactly
- type: `convention`
- verification method: `static`
- evidence ref: `.github/workflows/ce-ops-autoclose.yml`
- claim: preserve every current field exactly except set `evidence_sha256` to
  `ed1be82ac0a735fc4155633135ff2fdc25488c5bedf0c612041fb1d46ddae486`

The corrected claim JSON is:

```json
{"details":"Cross-repository closing keywords are mention-only without the dedicated close workflow; merged PRs rely on the close bot for issue closure.","evidence_sha256":"ed1be82ac0a735fc4155633135ff2fdc25488c5bedf0c612041fb1d46ddae486","item":16,"object":"cross-repo-closes-bot","predicate":"asserts","refs":[".github/scripts/ceops_autoclose.py","tools/ce-ops-autoclose/parse_issue_refs.py"],"subject":"doctrine-item"}
```

Expected post-correction ledger facts: 165 records, active-count ratchet 105,
tail sequence 164, new active ID `brain-assertion-d1b-16-cross-repo-closes-bot-v3`.
Update only the authoritative active-count assertion in
`validators/tests/unit/test_ce_brain_drift.py` from 104 to 105.

Run `brain verify --state-root .ce --drift` and the focused brain-drift tests.

## Carriers and validation

Generate the changelog and carrier via `carrier_gen.write_carriers(base="origin/main")`;
do not hand-list or hand-hash the carrier. The carrier slug must equal the branch
exactly and declare work class `story`.

Commit the complete closed-set change, then run:

1. `git diff --check origin/main..HEAD`
2. focused `validators/tests/unit/test_ce_brain_drift.py`
3. full `validate-pr` through the main-vintage test interpreter, with credential
   variables unset and this test command so baseline/HEAD scratch is reused:

`/home/ce-dev-2/creator-engine/validators/.venv-test/bin/python -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup --basetemp /var/tmp/ce-preflight-basetemp-ce516`

The full preflight must be green before READY. Do not push.

## Stop/report

Stop on stale base, any scope expansion, any second brain chain, any unexpected
hash/count, or any need for credentials/authority. Final response first line:

`READY-FOR-HARVEST ce-516-item3-brain-window <full-40-hex-sha>`

or

`BLOCKED ce-516-item3-brain-window <reason>`

Then report changed paths, exact correction IDs/counts, validation evidence,
and residual risk.
