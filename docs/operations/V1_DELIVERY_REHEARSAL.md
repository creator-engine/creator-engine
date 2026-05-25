# v1.0 Delivery Rehearsal

**Gate**: v1.0 Gate 8 (v1.0 docs finalization + delivery rehearsal + Integration Queue dry-run seam)
**Requirement**: RV1-083
**Status**: **Rehearsed local-safe** (dry-run-safe end-to-end pipeline + offline
install proofs; reproducible via
`validators/tests/integration/test_v1_delivery_rehearsal.py`).
**Architectural companions**:
[`AGENT_NATIVE_BOOTSTRAP.md`](./AGENT_NATIVE_BOOTSTRAP.md),
[`INTEGRATION_QUEUE_DRY_RUN.md`](./INTEGRATION_QUEUE_DRY_RUN.md),
[`EVIDENCE_FAN_IN_PROTOCOL.md`](./EVIDENCE_FAN_IN_PROTOCOL.md)

---

## 1. Purpose

The delivery rehearsal walks the as-built v1.0 `ce` surface end-to-end on a real
host, using **only local-safe, dry-run-safe paths** — no live tmux Controller
spawn, no live container, no network, no GitHub/landing, no secret material. It
proves the offline install mechanism (Option B) and that the full command
pipeline runs (or refuses fail-closed) as designed, leaving the tracked tree
clean.

It is a **rehearsal**, not an authority transfer: it lands nothing, ratifies
nothing, and enqueues nothing.

## 2. Offline install (Option B)

The rehearsal installs the validator/`ce` runtime offline from the checked-in
cp314 wheelhouse, both ways, with no network access:

**uv-first (primary):**

```bash
uv venv --python 3.14
UV_PYTHON_DOWNLOADS=never uv pip install --no-index --find-links validators/wheelhouse creator-engine-validator
```

**pip fallback** (run from a neutral working directory so the source tree does
not shadow the wheel):

```bash
python3.14 -m venv .venv && . .venv/bin/activate
pip install --no-index --find-links "$PWD/validators/wheelhouse" -r "$PWD/validators/requirements.txt"
pip install --no-index --find-links "$PWD/validators/wheelhouse" creator-engine-validator
```

Both install `creator-engine-validator==0.1.0` with PyYAML 6.0.3 / jsonschema
4.26.0 and expose the `ce` console script. As of **Gate 9** the cp314 wheel was
**rebuilt from current source** (`setuptools.build_meta`), so the offline install
now exposes the full as-built surface `{lane, ledger, worker, fanin, queue, check,
doctor, init, launch, hud}` — including `ce fanin` (Gate 7) and `ce queue`
(Gate 8) — and still registers **no** `ce dev`. (The previously committed wheel
was G6-era and predated `ce fanin`/`ce queue`; Gate 9 closed that packaging
mismatch.) **Note:** because the version is unchanged at `0.1.0`, pass
`--no-cache` (uv) / `--no-cache-dir` (pip) to defeat a stale cached `0.1.0`
wheel and install the wheelhouse artifact itself.

## 3. Dry-run-safe pipeline

Run inside a governed temp git repo (`.hermes/` git-ignored). Each step is
either a benign success or a fail-closed refusal:

| Step | Command | Expected | Why safe |
|---|---|---|---|
| init | `ce init --repo-root <repo> --json` | exit 0 | writes only under ignored `.hermes/` |
| doctor | `ce doctor --repo-root <repo> --no-check-packaging --json` | report (0/1) | interpreter contract `>=3.14`; no host mutation |
| check | `ce check examples/well-formed` (from repo root) | exit 0 | read-only conformance over the shipped examples |
| launch | `ce launch --dry-run --json` | exit 0, `spawned=false` | plan only; no tmux spawn, no provider login |
| lane | `ce lane launch … --no-tmux` | exit 1, no pane record | visibility guard refuses a non-visible seat (`G3-VISIBILITY-REFUSED`) |
| worker | `ce worker status …` (absent record) | exit 1 | read-only fail-closed; no live container |
| ledger | `ce ledger verify …` | exit 0 / non-zero on tamper | read-only chain replay |
| fanin | `ce fanin build` + `ce fanin inspect` | exit 0 | deterministic packet under ignored `.hermes/fan-in/` |
| queue | `ce queue dry-run` + `ce queue inspect` | exit 0 | deterministic preview under ignored `.hermes/integration-queue/` |
| queue (live) | `ce queue dry-run … --land` | exit 1 | live landing refused (`G8-QUEUE-AUTHORITY-REFUSED`) |

`ce lane launch` has no `--dry-run` flag (only the refuse-only `--no-tmux`); the
lane step is rehearsed as the dry-run-safe **refusal**, which proves the
visibility guard and leaves no pane record — the safe equivalent of a dry run
under the no-live-spawn boundary.

After the pipeline, the temp repo's **tracked tree is clean**: every byte of
runtime output lands under the ignored `.hermes/` root (fan-in packets, queue
previews, init state). No GitHub/remote/network/daemon/web surface is touched,
and no secret material appears in the transcript.

## 4. Evidence

Rehearsal evidence is **ignored runtime state** under
`.hermes/rehearsals/<UTC-timestamp>/` (the `.hermes/` root is git-ignored, so the
evidence never enters the tracked tree):

- `install_pip_fallback.log` — offline pip-fallback install (deps + project), exit 0.
- `install_uv_first.log` — offline uv-first install, exit 0.
- `pipeline_transcript.txt` — the full dry-run-safe pipeline with per-step exit codes.
- `temp_repo_clean_status.txt` — `git status --porcelain` proof (no tracked mutation).
- `SHA256SUMS_REHEARSAL.txt` — SHA256 manifest over the four evidence files.

The most recent rehearsal recorded every expected outcome: init/check/launch/
fanin/queue at exit 0; lane (`G3-VISIBILITY-REFUSED`), worker (fail-closed), and
`queue … --land` (`G8-QUEUE-AUTHORITY-REFUSED`) at exit 1; clean tracked tree.

## 5. Reproducibility

The dry-run-safe pipeline is encoded as the reproducible integration test
`validators/tests/integration/test_v1_delivery_rehearsal.py`, which runs the
whole sequence in a governed temp repo and asserts the clean-tracked-tree and
no-leak properties on every run. The offline-install proofs are reproduced by
the commands in §2.
