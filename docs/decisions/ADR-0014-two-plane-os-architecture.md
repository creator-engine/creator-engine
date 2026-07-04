---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0014
title: "Two-plane OS architecture"
status: accepted
date: "2026-07-04"
decision_makers: ["ce-runtime-architect"]
consulted: ["internal governance: two-plane OS strategy ratification thread"]
informed: []
review_by: "2027-01-04"
mutation_class: governance
evidence_refs:
  - kind: issue
    ref: "internal governance: two-plane OS strategy ratification and amendments, 2026-07-04"
    tag: two-plane-ratification
  - kind: doc
    ref: "docs/design/oq1-os-native-sandbox-mechanism.md"
    tag: oq1-os-native
  - kind: adr
    ref: "docs/decisions/ADR-0013-substrate-independent-authority.md"
    tag: adr-0013
  - kind: doc
    ref: "surfaces/manifest.yaml"
    tag: surfaces-manifest
ratification:
  ratified_by: "chmod735"
  ratified_at: "2026-07-04"
  ratification_prompt_sha: "244b247f6e95e7d1497b35e2338b21050829694e73c855714af8433a6b699660"
  quorum: n1_solo
crosswalk:
  supersedes:
    - "docs/design/oq1-os-native-sandbox-mechanism.md"
  informs:
    - ADR-0013
    - "surfaces/manifest.yaml"
---

# Two-plane OS architecture

> **Traceability note:** Precise internal governance linkage is maintained in the
> internal decision thread, not in this public record.

## Context and Problem Statement

CE began with an OS-agnostic control-plane intent, but its runtime requirements
have accumulated Linux-specific assumptions: process containment, egress
boundaries, broker and daemon supervision, runtime sockets, and path conventions
do not share one portable native abstraction across Linux, macOS, and Windows.
The ratified two-plane decision separates the part that should remain portable
Python from the part that needs one governed Linux runtime substrate
([two-plane-ratification]).

The prior OQ-1 `os-native` plan selected native OS sandbox mechanisms for a
user-elected solo path ([oq1-os-native]). That mapping is now superseded:
container-first runtime delivery applies everywhere, and native OS containment
implementations are no longer the CE architecture direction.

## Decision Drivers

- Preserve the portable Python surface where it is real: CLI, validators,
  onboarding, brain, carrier generation, and preflight orchestration.
- Stop multiplying runtime threat models, test matrices, and containment
  implementations per host operating system.
- Use one governed runtime image and one deployment model for both solo and
  fleet use.
- Remove systemd from CE's architectural contract rather than preserving a
  fleet-only exception.
- Confine container-runtime API access to one explicit privileged component.
- Keep release surfaces digest-pinned and reviewable through the existing
  manifest discipline ([surfaces-manifest]).

## Considered Options

1. Build native runtime implementations per host OS.
2. Keep an OS-agnostic runtime abstraction over host-native primitives.
3. Split CE into a portable Python control plane and a canonical Linux
   container runtime plane.

## Decision Outcome

Chosen option: **portable Python control plane plus canonical Linux container
runtime plane**, because it preserves CE's portable authoring and governance
interfaces while standardizing the isolation and service-runtime substrate
([two-plane-ratification]).

### D1 - Control Plane

The control plane remains portable Python. It includes:

- `ce` CLI flows;
- validators and local preflight;
- onboarding;
- brain and knowledge orchestration;
- carrier and path-manifest generation.

Control-plane modules must not assume systemd, Unix-domain sockets, or literal
runtime paths such as `/run/...`. A follow-on CI guard must enforce this
portability boundary with the same structural posture used by existing public
docs and confidentiality scanners.

### D2 - Runtime Plane

The runtime plane is standardized on **one canonical Linux container runtime
image**. That image is delivered through:

- Docker or Podman on Linux;
- Docker Desktop or Apple container facilities on macOS;
- WSL2 on Windows.

The runtime image is a governed release artifact. It must be multi-architecture
where supported, and runtime image references must follow the existing
per-surface and per-architecture digest-pin discipline in
`surfaces/manifest.yaml` ([surfaces-manifest]).

### D3 - One Deployment Model

CE has no fleet-vs-solo runtime-plane split. The stack is a set of containers on
the canonical runtime image: seats, brokers, daemons, belt, review pickup,
conveyor, and adjacent runtime services. Fleet and solo deployments differ only
in compose topology:

- seat count;
- the secrets backend behind the gateway.

They do not differ in deployment model.

### D4 - systemd Is Out of CE Architecture

systemd units are no longer a CE adapter tier. Container restart policies,
healthchecks, and compose topology own service supervision inside CE's runtime
plane. `deploy/systemd/` is migration legacy after this decision, not a parallel
architecture.

What starts containers at host boot is host bootstrap outside CE's contract.
Compose, quadlet, Docker Desktop autostart, or equivalent host-level mechanisms
may start the stack, but CE does not define that layer as part of its runtime
architecture.

### D5 - Single Privileged Launcher

Exactly one privileged component may hold container-runtime API access: the
launcher. The launcher is itself a container with the runtime socket mounted.
There is no host-shim launcher in the CE architecture.

The container around the launcher is packaging, not containment. A mounted
container-runtime socket is root-equivalent for the runtime boundary it controls,
so the launcher must be treated as privileged even when it is shipped as a
container.

Runtime-socket scoping preference order:

1. rootless Podman user socket;
2. allowlisting socket-proxy sidecar with a narrow create/start interface and
   no general exec or arbitrary mount authority;
3. raw socket mount as the floor, acceptable for solo macOS where the desktop
   runtime VM already bounds the blast radius.

This exclusivity must become a CI guard: exactly one compose service may mount
the container-runtime socket. Seat containers and all other services must not
mount it.

The launcher blast surface is intentionally narrow:

- no general egress;
- read-only configuration;
- runtime socket plus work queue only;
- a narrow internal runtime-interface abstraction so Docker, Podman, or remote
  runtime swaps stay behind the same boundary.

## Consequences

- Good: CE keeps a genuinely portable Python control plane while making the
  runtime substrate explicit and testable.
- Good: Solo and fleet delivery converge on one governed runtime artifact and
  differ only by compose topology.
- Good: Native OS containment ambitions from OQ-1 are superseded before CE
  commits to multiple sandbox implementations.
- Good: systemd leaves the architecture rather than persisting as a privileged
  adapter tier.
- Good: Runtime API root-equivalence is localized to one explicit launcher and
  can be linted in compose.
- Bad: Hosts need a container-capable bootstrap path outside CE's contract.
- Bad: The launcher remains privileged by design; container packaging does not
  make a mounted runtime socket safe.
- Bad: Follow-on work is required to containerize gate daemons and brokers,
  write the control-plane portability guard, and publish the runtime image as a
  governed digest-pinned artifact.

## Workstream

This ADR requires the following implementation stream:

1. Add a control-plane portability CI guard for systemd, Unix-domain socket, and
   literal `/run` assumptions in control-plane modules.
2. Containerize gate daemons and brokers onto the canonical runtime image, with
   fleet and solo compose topologies.
3. Publish the CE runtime image as a governed release artifact with
   multi-architecture digest pins recorded through the surfaces manifest.
4. Add a compose structural guard that permits exactly one service to mount the
   container-runtime socket.

## Ratification

Ratified by Operator **chmod735** on **2026-07-04** via this ADR's ratification
record. The ratified decision stack includes the initial two-plane decision, the
amendment that removes fleet/solo runtime differentiation, and the launcher-form
decision that selects a containerized privileged launcher.
