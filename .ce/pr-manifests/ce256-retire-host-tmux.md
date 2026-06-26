# PR path manifest - ce-ops#256 - retire host tmux anchoring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce256-retire-host-tmux` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=d43ee4884f8c58085b63293a0f1c7228199fc9fe0b928faa1c385af455023a97

```text
.ce/changelog/ce256-retire-host-tmux.md
.ce/pr-manifests/ce256-retire-host-tmux.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/systemd/README.md
deploy/systemd/ce-codex-seat@.service
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
