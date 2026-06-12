# PR path manifest — site-v8-pr1 · ce-ops#51 site v8 "The Factory Floor" PR1/3

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref site-v8-pr1
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED on ce-ops#51 (2026-06-12, relayed via the CE-DEV-2 controller). Ratified Scope
`site-v8-pr1` (`.ce/state/scopes/site-v8-pr1.scope.yaml`, ratified_scope_sha
`8ecdacc13542ae24eac7c7983ee1212932adcd4d8f086f1ecacb4ae745303cbf`). Design package
`ce-site-v8-design-package-20260612.md` (sha256
`6c37feaba5f3b6330f2b3577667740b24509955e92e3306eaea5d3f0ac273baf`, verified before authoring;
R1–R10 adopted as recommended). Change-type: docs.

Base:
`ce25fe59cefde080a40330035b3ad2c28f5455b8` (`main` = #214, `ce --version` surface).

The change (site v8 "The Factory Floor", PR1 of 3 — SS1–SS3 + SS5, the PR1 reductions):
A new ultra-minimalist dark "software factory" `docs/index.html` v8. Page skeleton: slim nav →
§1 hero conveyor → §2 install bay → footer (the §3 cockpit bay and ALL animations are PR2/PR3 and
deliberately absent). Art-direction tokens KEEP the 8 validator-pinned Control-Room Violet hexes
verbatim (R1) and add scene-local steel/near-black factory literals; color is rationed (steel grays
through Frame/Shape/Build/Review, `--spark` only at the Build weld + Ship, `--gate` only on the two
physical human-gate frames, the shipped product the page's one polychrome object). The hero is the
five governed stations rendered as a STATIC inline-SVG conveyor — the reduced-motion-first posed
diagram, identical with and without `prefers-reduced-motion`; the working arm is the CE mark's
six-axis weld arm re-posed per station (Build = the arched logo pose), Review's scanner is a
deliberately different machine. Type retires the v7 serif (R6) for all-sans display + mono machine
text. The install bay (R4) keeps "There is no install wizard.", moves the v7 reveal contents inline
with Copy buttons + the signed-playbook trust line, and retires all Matrix/red-pill language. The
footer keeps the OpenShell badge + honesty line + `llms` links verbatim. No animation/JS-motion
code is present; the only script is the proven clipboard helper; zero external requests preserved.
Per the site-versioning policy, the SAME PR snapshots the outgoing v7 page byte-identical to
`site-archive/index-v7-the-choice.html` (sha256 `38f89de4…`, == the pre-change `docs/index.html`),
demotes the v7 ledger row, and promotes v8 to "current — live".

Per-file purpose (the closed path-set — 4 paths):
- **`.ce/pr-manifests/site-v8-pr1.md`** *(A)* — this carrier (self-inclusive).
- **`docs/index.html`** *(M)* — the v8 "The Factory Floor" PR1 page (replaces v7 "The Choice").
- **`site-archive/index-v7-the-choice.html`** *(A)* — byte-identical snapshot of the outgoing v7
  `docs/index.html` (site-versioning policy step 1; never edited after the fact).
- **`site-archive/README.md`** *(M)* — ledger: v7 row demoted (snapshot file + live commit `ee37a4d`
  #200), new v8 "current — live" row added (policy steps 2–3).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=065cdc5b241f541fe77e07535eec44d5396bf53a9f9be17d07d9cab00d4bcaf7

```text
.ce/pr-manifests/site-v8-pr1.md
docs/index.html
site-archive/README.md
site-archive/index-v7-the-choice.html
```
