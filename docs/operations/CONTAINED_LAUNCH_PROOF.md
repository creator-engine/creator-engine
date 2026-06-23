# Contained Launch Proof

This is the proof path for ce-ops#128/#221: `ce launch --backend gvisor` must
start the governed seat through the runner backend and then prove containment
with `ce containment-probe`. The containment verdict is based on kernel evidence
from `/proc`, not on the launch contract.

## CI Proof

CI uses mocked Docker/runsc availability and fixture `/proc` evidence:

```bash
PYTHONPATH=validators python3 -m pytest \
  validators/tests/unit/test_contained_launch_proof.py \
  validators/tests/unit/test_ce_launch_cli.py \
  validators/tests/unit/test_containment_probe.py \
  validators/tests/unit/test_gvisor_proxy_backend.py -q
```

The mocked legs are:

- Docker/runsc availability and egress enforceability, through the injected
  `ContainerRunner` seam.
- The visibility surface, through a fake tmux adapter.
- Kernel evidence, through a fixture `/proc` tree consumed by
  `ce containment-probe --proc-root`.

The CI proof asserts:

- gVisor launch invokes `RunnerBackend.provision -> run` and places the sentinel
  harness command after the Docker `--runtime=runsc-gvproxy-ptrace` image ref.
- The same launched seat pid fixture probes as
  `{"contained": true, "backend": "gvisor"}` from distinct mount namespace,
  runsc cgroup scope, and dropped capabilities.
- A raw launch has no `runner_runtime` and probes
  `{"contained": false, "backend": "none"}` fail-closed.
- Missing gVisor runtime availability refuses before any tmux/raw fallback spawn.

## Live DGX Dogfood

Live DGX verification is intentionally outside normal CI because it needs the
registered Docker runtime and DGX `gvproxy` posture. On the DGX host with
`runsc-gvproxy-ptrace` registered:

```bash
CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh exec \
  "ce launch --backend gvisor --runtime-policy .ce/state/policies/gvisor-implementer-v1.yaml --harness codex --session ce128-proof --window seat && ce containment-probe --json"
```

For dry-run inspection of the wrapper posture:

```bash
CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh --dry-run exec \
  "ce launch --backend gvisor --runtime-policy .ce/state/policies/gvisor-implementer-v1.yaml --harness codex --session ce128-proof --window seat && ce containment-probe --json"
```

The live leg verifies the actual Docker runtime, runsc sandbox, namespace,
cgroup, capability, and root evidence on DGX. CI verifies the CE wiring and
verdict logic deterministically with mocks; it does not claim live Docker/runsc
execution.
