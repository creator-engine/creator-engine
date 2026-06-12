# PR path manifest — esc-26-sentinel-readiness-regression · seat-sentinel wrapper readiness fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref sentinel-readiness-fix
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED fix-gate mandate `esc-26-sentinel-readiness-regression`
(`.ce/state/research/w2-parallel/MANDATE_sentinel_readiness_fix.md`). A live regression
escaped #211's standardized seat-sentinel wrapper: the wrapper (CORRECT, by design) runs the
harness as a CHILD of `sh` so it can write the `exited` event after the child returns, but
`v3_seat_bridge._await_pane_ready` polled only `#{pane_current_command}` — which stays a shell
forever under the wrapper — so every `cev3 drive --spawn` author seat refused at the 30s
seed-readiness timeout while the seat behind it was healthy (two conserved refusals:
run-f6-phase0-restamp-20260612T0929{12,48}Z; pane autopsy shows the REPL up).

Base:
`3dcd8206...` (#211 = `feat(ce-ops#26): standardized seat lifecycle sentinels (push-not-poll)`;
this fix extends only the `_await_pane_ready` readiness probe introduced/adjacent to that
seat-sentinel surface — no unlisted drift). `seat_sentinel.py` and the wrapper are UNTOUCHED.

The fix (smallest-correct, §"The ratified fix"):
In `_await_pane_ready`, keep the existing foreground check; when the foreground is STILL a
shell, additionally read the pane's pid (`tmux display-message -p -t <pane> '#{pane_pid}'`,
helper `_pane_pid`) and inspect its direct child tree (`ps -o comm= --ppid <pane_pid>`, helper
`_pane_has_nonshell_child`) — ready when ANY non-shell child exists (the wrapper's harness child
is exactly one level down). Both probes ride the SAME injectable `runner` seam (CI: zero live
subprocess); both helpers stay private to the bridge. Timeout/refusal semantics are unchanged —
the pane is never killed and a never-ready pane is conserved for autopsy (`mark_spawn_failed` by
the caller, no spawn side effect). `seat_sentinel.py` and the wrapper are NOT touched.

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/sentinel-readiness-fix.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — `_pane_pid` +
  `_pane_has_nonshell_child` helpers and the `_await_pane_ready` child-tree fallback; the
  foreground check and the timeout/refusal path are conserved.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — four new tests recording the REAL
  output shapes in the fakes: wrapper shape (`sh` foreground + non-shell `ps` child → ready,
  spawn proceeds), bare-launch shape conserved (foreground leaves the shell → ready with NO ps
  probe), shell-only/no-children → timeout → refusal identical to today (pane CONSERVED, no
  spawn side effect), and the ps probe rides the injectable runner seam (zero live subprocess).
  The existing readiness tests stay green unmodified.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — wheel
  rebuilt from this branch's source (`v3_seat_bridge.py` is wheel-shipped; the packaging
  contract byte-checks every bundled `.py` against source).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=f1505dd29ee1e0901e450d88ed83f81c67e09b8e9f98e49a5207c471cb60804d

```text
.ce/pr-manifests/sentinel-readiness-fix.md
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_v3_seat_bridge.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
