# Creator Engine v1.0 — Governed-Environment Guard Predicate Requirement (`V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md`)

Gate: **G1 — Canonical terminology + product-contract lock** (type: **DOC**; lint only).
Authored UTC: 2026-05-24T17:52:25Z.
Lane: Gate 1 documentation-only writer, visible tmux pane, Claude Code Opus 4.7, effort high.
Controlling roadmap: **Option B re-issued definitive roadmap**, SHA256
`5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13` (§2.7, §3).
Canonical baseline: live `refs/heads/main` = `36377f8c4caf6817e01d58072062eb5caccc164b`.
Requirement: **RV1-012** (`specs/_traceability_matrix.md`); decision lock: **DP-3 = B** (ADR-0001 §3).

> **Authority and scope (read first).** This file records the governed-environment guard predicate as
> a **requirement and RED test plan only**. **Gate 1 implements nothing**: no code, no schema, no
> validator, **no `ce doctor`**, no dependency work, no wheelhouse work. Implementation is **Gate 6**
> (RV1-061), under strict refusal-TDD. This file authorizes no implementation and re-decides no Source
> lock.

---

## 1. What the guard protects

The governed-environment guard predicate exists so that **Creator Engine v1.0 runs as a governed local
runtime kernel, not an unmanaged host script bundle.** Because DP-3 = B permits **host-local
development** in v1.0 (it does not mandate a project-dev container), the guard is the explicit
predicate — surfaced through `ce doctor` / `ce check` — that **asserts governed-environment posture and
refuses ungoverned host drift**. It is the v1.0 **substitute** for mandatory project-dev
containerization. Without it, host-local development could silently drift out of the governance
contract; the guard makes that drift **detectable and fail-closed**.

(Definitions: `docs/governance/V1_CANONICAL_TERMINOLOGY.md` §6, "governed environment" and
"governed-environment guard predicate". Product boundary: `docs/governance/V1_PRODUCT_CONTRACT.md` §1.)

## 2. What the guard must refuse later at Gate 6

At Gate 6, the implemented guard predicate **must refuse (fail-closed, non-zero exit, machine-readable
diagnostic naming the violated clause)** each of the following ungoverned-host conditions:

1. **Out-of-contract interpreter** — an active interpreter that does not satisfy the floor + target
   contract `>=3.14` / 3.14.x (e.g. Python 3.13 or 3.15).
2. **Missing tmux** — tmux absent when a visibility-required lane / Controller-seat launch needs the
   only contract-conformant visible terminal (PCO-049).
3. **Missing rootless Podman for worker execution** — rootless Podman unavailable (or **rootful**
   Podman presented) when a worker/agent execution operation is requested.
4. **Ungoverned state-path posture** — `.hermes/` state-path posture that is not governed (e.g.
   `.hermes/` not git-ignored, or a governed write targeting a tracked governance artifact instead of
   ignored `.hermes/` state).
5. **Unsafe hidden continuation** — a posture that would let in-flight work continue **hidden** (no
   visible pane / dead-pane continuation) and be treated as ratified. There is **no hidden fallback**.
6. **Dependency / wheelhouse contract drift** — installed dependency set or offline wheelhouse that
   diverges from the locked Option B contract (`PyYAML==6.0.3`, `jsonschema==4.26.0`, **cp314-only**
   wheelhouse, `uv.lock` reproducibility, `requires-python = ">=3.14"`).

On a clean governed host, the guard predicate **passes** (PASS branch), and `ce doctor` proceeds. The
guard is designed **forward-compatibly**: a future v1.1 **governed dev-container** posture becomes an
additional detectable, validatable **PASS branch** of the same predicate, not a new isolation model
(`docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md`).

## 3. What Gate 1 does NOT implement

Gate 1 records the requirement only. Gate 1 does **not**:

- write any **code** or **`ce doctor`** / `ce check` predicate logic;
- author or modify any **schema** (`schemas/`) or **validator** (`validators/`);
- author or modify any **test** code (`tests/`);
- perform any **dependency / wheelhouse / packaging** work (`pyproject.toml`, `uv.lock`,
  `requirements.txt`, wheelhouse files);
- run `uv`, `pip install`, dependency resolution, a wheelhouse rebuild, a container start, or any live
  `ce` runtime command.

All of the above is Gate 6 implementation scope (RV1-061), gated by its own Source ratification.

## 4. RED test plan (recorded; executed at Gate 6)

The guard is implemented under **strict refusal-TDD** at Gate 6: each RED case below is authored and
**observed failing for the right reason** (predicate absent) **before** the predicate exists, then made
GREEN by the minimal predicate implementation.

| RED case | Ungoverned condition | Expected refusal (Gate 6) |
|---|---|---|
| RED-G-1 | Active interpreter is 3.13 or 3.15 (out-of-contract) | `ce doctor` refuses; names the floor/target clause `>=3.14`/3.14.x; non-zero exit |
| RED-G-2 | tmux missing for a visibility-required launch | refuses; names PCO-049 visible-terminal clause; non-zero exit |
| RED-G-3 | rootless Podman missing, or rootful Podman presented, for worker execution | refuses; names rootless-required / rootful-refused clause (PCO-045); non-zero exit |
| RED-G-4 | ungoverned `.hermes/` state-path posture (not ignored / tracked-artifact write) | refuses; names the state-boundary clause; non-zero exit |
| RED-G-5 | unsafe hidden continuation (no visible pane / dead-pane continuation) | refuses; preserves evidence; refuses to treat in-flight work as ratified |
| RED-G-6 | dependency / wheelhouse drift from the Option B contract | refuses; names the violated dependency/wheelhouse clause; non-zero exit |

### Expected future GREEN evidence (Gate 6)

- `ce doctor --json` output for the **PASS** case (clean governed host) and for each **guard-FAIL**
  case above, each fail naming the violated clause with a non-zero exit.
- The out-of-contract-interpreter refusal demonstrated against an interpreter outside `>=3.14`/3.14.x.
- Proof that the guard PASS branch is forward-compatible with a future v1.1 governed dev-container
  posture (the v1.1 seam adds a PASS branch, not a new model).

## 5. References

- `docs/adr/ADR-0001-v1-baseline-and-product-form.md` §3 — DP-3 = B lock.
- `docs/governance/V1_CANONICAL_TERMINOLOGY.md` §6 — governed-environment terms.
- `docs/governance/V1_PRODUCT_CONTRACT.md` §2–§3, §6 — DP-3 = B, IN/SEAM/POST-V1, Option B contract.
- `docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md` — forward-compatible v1.1 dev-container PASS branch.
- `specs/_traceability_matrix.md` — RV1-012 (this doc) and RV1-061 (Gate 6 implementation).
- Option B re-issued roadmap §2.7 (worker/guard), §3 (guard row: G1 req / G6 impl) — `5a7e5ba7…`.
