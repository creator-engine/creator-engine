# OQ-1 OS-Native Sandbox Mechanism

Status: proposed decision package

## Problem Statement

The `os-native` runner backend is intentionally present but not yet a live
sandbox mechanism. It gives Creator Engine a neutral backend key for a
daemonless, unprivileged runtime, while preserving the current containment
default: `gvisor-proxy` remains the conservative default backend for runtime
policy records and shared-host deployments.

The Tranche 1 scaffold is already registered as `BACKEND_KEY = "os-native"`.
Its current behavior is fail-closed: a dirty runtime-policy record is rejected
by `RunnerBackend.provision` before backend-specific provisioning runs; a clean
record reaches `_provision`, then `os-native` raises `BackendUnavailable` because
the mechanism decision is still held. The current Linux primitive names are
exactly `("bwrap", "proxy")`. They are documented and probed prerequisites, not
auto-installed dependencies. For a privileged runtime today, the existing held
path directs users to `gvisor-proxy`.

The decision needed now is narrower than "make os-native the default." The
decision is: which mechanism should a user-elected Tier-1 `os-native` backend
use when it moves from fail-closed scaffold to live runtime?

The governance posture is fixed:

- `os-native` is real and user-selectable, but it is not the default backend.
- It must require no container daemon, no administrator install path, and no
  privilege escalation.
- It must preserve runtime-policy validation before provisioning.
- It must fail closed when a required primitive is unavailable or cannot be
  proven.
- It must keep the egress and evidence contract outside the agent process,
  rather than trusting in-process denylists as the boundary.
- It must remain a defensive containment mechanism only.

The current runtime-policy enum already contains `gvisor-proxy`, `openshell`,
`local-noop`, and `os-native`. The schema default remains `gvisor-proxy`, and
the field remains optional for back-compat records. Installer resolution is
explicit backend, then selected profile, then `gvisor-proxy`; unknown explicit
backend values fail closed. Today, the solo-pilot profile maps to `os-native`
and the team profile maps to `gvisor-proxy`. Onboarding may map an omitted
profile to solo-pilot, but this proposal still treats contained `gvisor-proxy`
as the product default unless the user elects the Tier-1 path through an
explicit backend or profile choice.

## Mechanism Options

### Option A: Linux `bwrap` + Landlock + seccomp

Use Bubblewrap for process, mount, and namespace shaping on Linux, add Landlock
for file-read confinement where available, and apply seccomp for syscall
reduction. Pair the sandbox with a host-side deny-by-default egress proxy that
the agent cannot bypass.

Pros:

- Strong fit for the Tier-1 goal: daemonless, unprivileged, and container-free.
- Uses established kernel primitives instead of an in-process policy shim.
- Aligns with the current file mediation direction: Landlock can honestly report
  whether it enforced read confinement, and unavailable hosts can fail closed.
- Lower operational weight than the gVisor path.

Cons:

- Linux-only as a complete stack.
- Landlock is capability-dependent; older kernels or restricted hosts may not
  enforce it.
- Existing Landlock wiring is only Ring-1 filesystem mediation for runner
  subprocesses, not the complete `os-native` sandbox. It probes the ABI, is
  Linux-only, can report unavailable, and currently covers file-read access with
  `no_new_privs` plus `restrict_self`.
- Landlock alone cannot express every file-policy shape. It does not provide
  sub-path deny, directory-read mediation, or network exfiltration control by
  itself, so the CE classifier and audit overlay remain defense in depth, not a
  substitute for the OS and proxy layers.
- Egress remains the risk point and needs a real proxy boundary.

Blast radius:

- Limited to the launched runner process tree and its selected workspace.
- A broken adapter can over-allow file or network access unless every primitive
  is proven before exec.
- The fallback must be refusal, not silent launch without containment.

Portability:

- Good for modern Linux workstations and developer servers.
- Not portable to macOS or Windows as-is.

### Option B: macOS Seatbelt with `sandbox-exec`

Use Apple's Seatbelt profile mechanism through `sandbox-exec` as the macOS
implementation of the same `os-native` adapter contract.

Pros:

- Native to macOS and does not require a Linux container stack.
- Can support the same user-elected Tier-1 product promise on developer Macs.
- Provides an OS-level boundary outside the agent process.

Cons:

- The interface is less stable as a long-term product dependency than Linux
  primitives.
- Policy expressiveness differs from Linux, so one shared policy cannot be
  copied directly between platforms.
- Egress control still needs a separate host-side boundary; Seatbelt is not the
  whole runtime story.

Blast radius:

- Limited to the process launched under the profile when the profile is applied
  before user code executes.
- Miscompiled profile rules can either break common tools or over-allow access.
- Fail-open compatibility modes are not acceptable for this tier.

Portability:

- Good for macOS developer machines if the primitive is present and enforceable.
- No direct Linux reuse; the adapter must translate the same CE intent into a
  platform-specific profile.

### Option C: CE-native jail

Build a CE-owned jail layer that directly assembles per-platform process,
filesystem, syscall, and egress controls.

Pros:

- Maximum control over the policy model and evidence emitted by the adapter.
- Avoids tying the public contract to a single external runtime package.
- Can keep the CE runtime-policy vocabulary as the primary interface.

Cons:

- Highest implementation and maintenance cost.
- Highest security risk if CE becomes the author of subtle sandboxing behavior
  instead of composing well-understood OS primitives.
- Cross-platform parity would take longer and require more test infrastructure.
- Delays the user-facing Tier-1 backend.

Blast radius:

- Potentially broader than Options A or B because mistakes live in CE-authored
  mediation code.
- Requires extensive negative tests and live capability probes before it can be
  trusted.

Portability:

- Potentially broad over time, but least portable in the near term because each
  OS still needs a different low-level implementation.

## Recommendation

Recommend Option A as the first live `os-native` mechanism on Linux, with Option
B as the parallel native macOS lane and Option C deferred. OpenShell remains a
separate external adapter path with its own policy shape and logging behavior;
it is useful contrast, but it is not the recommended OQ-1 default mechanism.

The recommended default option for the decision is:

> Build the Tier-1 `os-native` adapter as a platform adapter over native OS
> primitives: Linux first with `bwrap` + Landlock + seccomp + deny-by-default
> proxy; macOS next with Seatbelt through `sandbox-exec`; defer a CE-native jail
> unless the platform adapters cannot satisfy the policy contract.

Rationale:

- It preserves the current default: `gvisor-proxy` remains the conservative
  contained backend unless a user or profile explicitly elects `os-native`.
- It makes `os-native` a genuine Tier-1 backend, not a synonym for raw local
  execution.
- It preserves the current dependency split: `os-native` stays at the
  user-level dependency floor, while privileged runtime dependencies remain
  specific to `gvisor-proxy`.
- It avoids making CE the first author of a full sandbox implementation.
- It matches the existing runner abstraction: backend selection stays a policy
  field, while each backend proves its own prerequisites.
- It keeps portability honest by using one adapter contract with
  platform-specific implementations rather than pretending one mechanism maps
  perfectly everywhere.

## Tranche-2 Adapter Scope

The next implementation slice should wire the live mechanism behind the existing
backend key. It should not change the backend default.

Linux `_provision` scope:

- Validate the runtime-policy record before any side effect.
- Probe required primitives: `bwrap`, Landlock availability, seccomp support,
  and the host-side egress proxy.
- Build a fresh sandbox rooted in the selected workspace and scratch area.
- Apply file-read confinement before user code executes.
- Apply syscall and process restrictions before user code executes.
- Route network access only through the deny-by-default proxy.
- Emit evidence that names which primitives were enforced.
- Refuse if any required primitive cannot be proven.

macOS `_provision` scope:

- Validate the runtime-policy record before any side effect.
- Probe `sandbox-exec` and the required Seatbelt profile capability.
- Compile a profile from the CE runtime-policy intent rather than reusing Linux
  policy text directly.
- Launch user code only after the profile is attached.
- Route network access only through the deny-by-default proxy.
- Emit evidence that names the profile and proxy enforcement state.
- Refuse if the profile cannot be applied or the proxy is unavailable.

User-election path:

- Runtime-policy records that omit a backend continue to resolve to
  `gvisor-proxy`.
- A user can elect `os-native` through an explicit backend field or through a
  profile whose ratified default maps to `os-native`.
- If onboarding selects the solo-pilot profile, the plan may select `os-native`;
  the apply result must still record the runtime as held until the live adapter
  exists.
- The plan must display the selected backend and isolation tier before apply.
- A selected `os-native` backend must never silently fall back to raw local
  execution or to `gvisor-proxy`; mismatches are refusals.

Fail-closed behavior:

- Missing primitive: refuse before launch.
- Unsupported OS: refuse before launch.
- Policy validation failure: refuse before launch.
- Egress proxy unavailable: refuse before launch.
- Partial setup failure: tear down created state and report no live runtime.
- Evidence ambiguity: report not enforced rather than inferred enforcement.

## Ratification Ask

Please ratify this precise decision:

> For OQ-1, the live `os-native` Tier-1 backend will use native OS primitives
> through a CE adapter contract: Linux `bwrap` + Landlock + seccomp plus a
> deny-by-default proxy first, macOS Seatbelt through `sandbox-exec` second, and
> a CE-native jail deferred unless those adapters cannot satisfy the contract.
> `gvisor-proxy` remains the default backend; `os-native` is user-elected and
> fail-closed.

Approval unblocks the Tranche-2 adapter implementation, live capability probes,
evidence shape, and platform-specific tests. It does not authorize changing the
default backend or launching an unconfined local runner.
