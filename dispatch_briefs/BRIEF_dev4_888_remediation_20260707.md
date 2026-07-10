# BRIEF — dev-4 — 2026-07-07 ~22:xxZ — 1 unit: PR #888 review remediation (your ce-488 slice 1)

Your #488 memory-layer slice was harvested as PR #888 and received an independent
REQUEST-CHANGES verdict (head f75ab6470). This unit remediates findings F1–F5 on the
SAME branch `ce-488-memory-layer-slice1`. COMMIT-ONLY: signal
`READY <branch> <sha> <evidence-path>`; controller harvests and force-pushes the PR head.
Worktree: fresh /var/tmp checkout; fetch the branch from origin
(`git fetch origin ce-488-memory-layer-slice1`) and base your work on THAT head
(f75ab6470 — it contains harvest-side carrier repairs and regenerated autogen docs your
original commit lacked), NOT on your old local worktree.

COMMIT EARLY AND OFTEN (one commit per finding) — your filesystem is RAM-backed; an
OOM loses uncommitted work. Run pytest with `PYTEST_ADDOPTS="-n 2"`.

## Findings to remediate (full text is on PR #888's review; substance embedded here)

F1 (BLOCKER, brain_runtime.py ~L1068-1075): `newest_resume_state.mtime` uses
`stat.st_mtime` — hydrate output changes on touch. Replace with a sha256 content hash
of the resume file (field rename mtime→content_sha256), or drop the field. Update the
takeover consumer + tests accordingly.

F2 (BLOCKER, brain-assertion.schema.yaml decision/$def): add a required
`authority` field to `decision` records (who ratified: e.g. "operator" | "controller"
| free-form identity string — pick the schema shape that matches existing record
conventions) and a `source` field to `brain-lesson`. Additive schema change; update
append validation, fixtures, autogen schema reference (scripts/gen_schema_reference.py
--write), and the hydration contract passthrough.

F3 (MAJOR, test_brain_runtime.py): add the byte-identical determinism pin — call
hydrate_contract twice on the same POPULATED state root (including a seeded resume
file) and assert identical serialized JSON. This test must fail on the old F1 code.

F4 (MAJOR, brain_runtime.py L880-1003): `append_decision`/`append_lesson` bypass the
append worker's origin/main chaining invariant. Privatize them (`_append_decision`/
`_append_lesson`) and update the test fixtures that call them, OR enforce the same
origin/main chaining check the worker applies. Choose privatization unless it breaks a
legitimate consumer; state the choice in the evidence file.

F5 (MAJOR): add the corrupt-ledger takeover test — seed a syntactically-valid but
chain-invalid ledger, run `ce takeover --dry-run`, assert exit code 2 with a
machine-readable error (fail-closed pin).

OPTIONAL if cheap (same revision, don't force): F7 inline comment on the hydration
empty-records lenience; F8 unify schema_version type (int vs str) between contract and
records; F10 note in the doc where brain_append_intent.schema.yaml lives.

EVIDENCE: update the carrier if the path set changes (slug==branch, work class stays
story); changelog fragment already exists — extend it with a remediation line. Evidence
summary with test counts; each finding's fix named.

Standing preflight directive (ce-ops#303): FULL local preflight (validate-pr) before
commit-for-harvest, with the -n 2 cap; if the full suite OOMs, focused modules + explicit
ENV-SKIP (controller re-runs host-side).

STOP LINE: no pushes, no PRs, no gate acts, no signing, no scope beyond the findings
above + their tests/autogen/carrier/changelog. If a finding's fix requires a design
decision not covered here, signal BLOCKED-DESIGN with the specific question.
