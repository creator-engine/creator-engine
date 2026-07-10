# Rootless-Podman spike — DGX (aarch64) — 2026-07-04 (time-boxed, ratified on ce-ops#437)

## Verdict: PASS for the validation-sandbox tier; gVisor-under-rootless-podman NOT viable out of the box.

## Evidence
- Host: DGX Spark, Ubuntu 24.04 aarch64, kernel 6.17. Installed `podman 4.9.3` + uidmap +
  slirp4netns via apt. subuid/subgid ranges for cedev2 pre-existed (296608:65536).
- **Rootless basic**: `podman run --rm alpine echo` → OK. `podman info`: rootless=true,
  graphDriver=overlay (native), cgroupVersion=v2, cgroupManager=systemd.
- **Validation-sandbox profile (the slice-8b shape), rootless**: `--network=none --read-only
  --tmpfs /var/tmp -v <worktree>:/work:ro` → read-only ENFORCED (touch refused), tmpfs writable,
  egress BLOCKED (wget fails, no DNS). Exactly the CE-410 verification-role policy, proven in
  one run with zero configuration.
- **gVisor (runsc) under rootless podman**: FAILS three ways —
  1. default (systemd cgroups): "systemd error: Interactive authentication required"
  2. `--cgroup-manager=cgroupfs`: "cannot set up cgroup for root ... permission denied"
  3. `--runtime-flag=ignore-cgroups` (with and without `--network=none`): "cannot run with
     network enabled in root network namespace" — runsc's rootless netns integration expects
     the gvproxy arrangement our Docker setup provides via the `runsc-gvproxy-ptrace` wrapper.
  Porting that wrapper to rootless podman is real integration work, not configuration.

## Decision shape this yields (recommended)
Split by threat tier, both on the same canonical OCI image:
- **Validation sandbox + PCO worker containers** (semi-trusted governed-seat code, empty
  egress/secret allowlists): **rootless Podman, no gVisor** — the profile itself closes the
  CE-410 defect classes (credential inheritance, artifact leakage, egress); namespace isolation
  suffices; matches the schema enum `podman-rootless` as-is and the ratified scoping order
  (socketless = strongest form).
- **Agent seats** (long-lived, model-driven, networked): **Docker + runsc-gvproxy-ptrace stays**
  (proven live for dev-3/dev-4) until a podman+gvproxy port is done (backlog hardening ticket,
  not this arc).

## Residual
- podman+gVisor rootless integration = filed as a hardening backlog item.
- Slice 8a/8b briefs bind to: engine=rootless podman, runtime=default (crun), verification
  policy record as shipped in examples (podman-verification.yaml promotion).
