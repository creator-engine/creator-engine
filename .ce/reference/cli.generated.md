<!-- ce-autogen: generator=scripts/gen_cli_reference.py source=validators/creator_engine_validator/ce_cli.py:_build_parser -->

# `ce` CLI reference

GENERATED FILE — do not edit by hand. This is a deterministic projection of the `ce` argparse command tree. To refresh it, run `python scripts/gen_cli_reference.py --write` and commit the result; a stale committed copy fails the validator gate (`VAL-AUTOGEN-STALE-CLI`).

Creator Engine kernel (v1.0 Gate 3 lane-launch surface)

## Top-level options

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--version` | no |  | show the CE version identity (<semver>+<short-sha>) and exit |

## Commands

### `automerge-decide`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--paths` | no |  | repeatable: repo-relative path changed in the PR (from git diff --name-only) |
| `--paths-file` | no |  | path to a newline-separated file of changed paths (alternative to --paths) |
| `--declared-work-class` | no | `epic, feature, story, tiny` | declared PR work class (default: story) |
| `--policy-state` | no |  | path to the automerge policy state JSON (default: .ce/state/automerge/policy.json relative to --repo-root) |
| `--repo-root` | no |  | repo root for default policy state path (default: current directory) |
| `--pr` | no |  | optional PR number for the audit record |
| `--head-sha` | no |  | optional PR head SHA for the audit record |
| `--checks-json` | no |  | optional JSON object mapping check-name to status (e.g. '{"ci": "success"}') |
| `--review-decision` | no | `, APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED` | optional GitHub reviewDecision for the PR |
| `--json` | no |  | emit machine-readable JSON decision record |

### `bootstrap`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | source checkout root (default: cwd) |
| `--venv` | no |  | target venv directory (default: .venv) |
| `--python` | no |  | target interpreter path (overrides --venv) |
| `--json` | no |  |  |

### `brain`

local Knowledge-SSOT assertion ledger + recall (assert/check/correct/ingest/recall/verify/probe/bootstrap)

### `brain assert`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--scope` | no |  | scope as a non-empty string |
| `--scope-json` | no |  | scope as a JSON object |
| `--id` | no |  | optional brain-assertion-* id |
| `--statement` | no |  | required SSOT statement (derived from claim when omitted) |
| `--type` | no | `capability, convention, decision, gotcha` | assertion type (default: decision) |
| `--verification-method` | no | `manual-attested, probe, static` | verification method (derived from evidence-ref when omitted) |
| `--claim-json` | yes |  | structured claim mapping as JSON |
| `--evidence-ref` | yes |  | required local/opaque evidence reference |
| `--json` | no |  | emit machine-readable JSON |

### `brain bootstrap`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--scope` | no |  | override corrected assertion scope as a string |
| `--scope-json` | no |  | override corrected assertion scope as a JSON object |
| `--role` | no |  | bootstrap role label |
| `--seat-class` | no |  | foreman/worker; unknown fails closed to foreman |
| `--json` | no |  | emit machine-readable JSON |

### `brain check`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--scope` | no |  | scope as a non-empty string |
| `--scope-json` | no |  | scope as a JSON object |
| `--claim-json` | yes |  | structured claim mapping as JSON |
| `--json` | no |  | emit machine-readable JSON |

### `brain correct`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--scope` | no |  | override corrected assertion scope as a string |
| `--scope-json` | no |  | override corrected assertion scope as a JSON object |
| `--id` | yes |  | active brain-assertion-* id to supersede |
| `--new-id` | no |  | optional corrected brain-assertion-* id |
| `--statement` | no |  | corrected SSOT statement (derived from claim when omitted) |
| `--type` | no | `capability, convention, decision, gotcha` | corrected assertion type (default: previous assertion type) |
| `--verification-method` | no | `manual-attested, probe, static` | corrected verification method (derived from evidence-ref when omitted) |
| `--claim-json` | yes |  | corrected structured claim mapping as JSON |
| `--evidence-ref` | yes |  | required correction evidence reference |
| `--json` | no |  | emit machine-readable JSON |

### `brain ingest`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--scope` | no |  | override corrected assertion scope as a string |
| `--scope-json` | no |  | override corrected assertion scope as a JSON object |
| `--source` | yes |  | repeatable Markdown file or directory source |
| `--db` | no |  | recall SQLite DB path (default: <state-root>/brain/recall.sqlite) |
| `--embedder` | no | `deterministic, embeddinggemma, vllm-openai` | embedding adapter (default: deterministic offline fake) |
| `--model-path` | no |  | local model path for --embedder embeddinggemma |
| `--endpoint` | no |  | override /v1/embeddings URL for --embedder vllm-openai (default: http://127.0.0.1:8989/v1/embeddings) |
| `--endpoint-model-id` | no |  | override model name for --embedder vllm-openai (default: Qwen/Qwen3-Embedding-8B) |
| `--endpoint-dim` | no |  | override expected embedding dimension for --embedder vllm-openai (default: 4096) |
| `--allow-confidential-egress` | no |  | permit egress-requiring embedders to process confidential recall chunks |
| `--as-of` | no |  | snapshot timestamp for produced records (YYYY-MM-DDTHH:MM:SSZ; deterministic default) |
| `--json` | no |  | emit machine-readable JSON |

### `brain init`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--json` | no |  | emit machine-readable JSON |

### `brain probe`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `name` |  | probe name |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--all` | no |  | run all registered probes |
| `--json` | no |  | emit machine-readable JSON |

### `brain recall`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `context` |  | free-form context to recall against (task/ticket/diff) |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--db` | no |  | recall SQLite DB path (default: <state-root>/brain/recall.sqlite) |
| `--embedder` | no | `deterministic, embeddinggemma, vllm-openai` | embedding adapter to query with — MUST match the embedder the store was ingested with (default: deterministic offline fake) |
| `--model-path` | no |  | local model path for --embedder embeddinggemma (must match ingest) |
| `--endpoint` | no |  | override /v1/embeddings URL for --embedder vllm-openai (default: http://127.0.0.1:8989/v1/embeddings) |
| `--endpoint-model-id` | no |  | override model name for --embedder vllm-openai (default: Qwen/Qwen3-Embedding-8B) |
| `--endpoint-dim` | no |  | override expected embedding dimension for --embedder vllm-openai (default: 4096) |
| `--top-k` | no |  | max items per tier |
| `--scope` | no |  | restrict recall to this scope string |
| `--as-of` | no |  | exclude recall records stamped after this as_of (YYYY-MM-DDTHH:MM:SSZ) |
| `--allow-confidential-egress` | no |  | permit an egress-requiring embedder to embed the query over a confidential corpus |
| `--hydrate` | no |  | emit a session-hydration payload (additive over the always-load CORE markdown) |
| `--core-path` | no |  | always-load CORE markdown path reported by --hydrate (never edited) |
| `--json` | no |  | emit machine-readable JSON |

### `brain verify`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--state-root` | no |  | CE local state root (default: .ce/state) |
| `--drift` | no |  | re-verify active assertions against their evidence_ref |
| `--json` | no |  | emit machine-readable JSON |

### `check`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `paths` |  | paths to validate |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--json` | no |  | emit machine-readable JSON |
| `--tenant` | no |  | restrict cross-artifact checks to one tenant |
| `--list-checks` | no |  | list enabled checks and their FRs |

### `claim`

work-claim locks: hub-visible per-ticket compose/dispatch claims (ce-ops#38)

### `claim acquire`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `ticket` |  | owner/name#N, a GitHub issue URL, or N (with --repo) |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo` | no |  | owner/name context for a bare issue number |
| `--json` | no |  | emit machine-readable JSON |
| `--reason` | no | `compose, implement, manual, review` |  |
| `--holder` | no |  | claim holder id (default: env/controller/hostname) |
| `--host` | no |  | claim host (default: hostname) |
| `--stale-after-seconds` | no |  | staleness fence (status/takeover threshold; never auto-release) |
| `--takeover` | no |  | seize a STALE foreign (or legacy) claim explicitly |
| `--takeover-reason` | no |  |  |

### `claim release`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `ticket` |  | owner/name#N, a GitHub issue URL, or N (with --repo) |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo` | no |  | owner/name context for a bare issue number |
| `--json` | no |  | emit machine-readable JSON |
| `--claim-id` | no |  | claim id to release (default: your active claim) |
| `--reason` | no |  | release_reason text |
| `--deliverable-url` | no |  |  |

### `claim status`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `ticket` |  | owner/name#N, a GitHub issue URL, or N (with --repo) |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo` | no |  | owner/name context for a bare issue number |
| `--json` | no |  | emit machine-readable JSON |
| `--write-cache` | no |  | write the view-only Cockpit cache under <ROOT>/claims/claims.json |

### `connector`

GitHub connector runtime: read-only verify/plan/fetch (G2.005.1) + strict-mode write-plan/submit (G2.005.2)

### `connector fetch`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--connector` | yes |  |  |
| `--mission-brief` | yes |  |  |
| `--resource` | yes |  | read resource path (e.g. repos/OWNER/REPO/issues) |
| `--provider` | no | `github, gitlab, jira` | read provider adapter (github default; jira/gitlab read-only, G2.005.3) |
| `--base-url` | no |  | read API base URL (overrides the provider default) |
| `--json` | no |  | emit machine-readable JSON |

### `connector plan`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--connector` | yes |  |  |
| `--mission-brief` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `connector submit`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--connector` | yes |  |  |
| `--mission-brief` | yes |  |  |
| `--verb` | yes | `issue-create, issue-update, pr-comment` | tracker_mirror write verb |
| `--resource` | yes |  | write resource path (e.g. repos/OWNER/REPO/issues) |
| `--payload` | no |  | path to a JSON request-body file (optional) |
| `--base-url` | no |  | write API base URL |
| `--json` | no |  | emit machine-readable JSON |

### `connector verify`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--connector` | yes |  | path to a connector descriptor *.ce.yml |
| `--mission-brief` | yes |  | path to a Mission-Brief *.ce.yml |
| `--json` | no |  | emit machine-readable JSON |

### `connector write-plan`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--connector` | yes |  |  |
| `--mission-brief` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `containment-probe`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `pid` |  | target pid to probe (default: this process) |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--proc-root` | no |  | proc tree root to read (default: /proc; override for fixtures) |
| `--host-pid` | no |  | reference host pid to compare namespaces/root against (default: 1) |
| `--json` | no |  | emit the machine-readable JSON verdict |
| `--herdr-socket` | no |  | controller-held herdr socket path to probe for per-seat liveness |
| `--herdr-pane-id` | no |  | herdr pane id to probe for agent-status readiness |
| `--herdr-binary` | no |  | herdr CLI binary used for the liveness probe (default: herdr) |
| `--ring1-tool` | no |  | Ring-1 guarded tool to probe via the target process PATH (default: git) |

### `containment-status`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--seat` | no |  | repeatable seat id or seat=pid binding; comma-separated values allowed |
| `--registry` | no |  | repeatable registry file/dir containing pane or seat-lifecycle records |
| `--proc-root` | no |  | proc tree root to read (default: /proc; override for fixtures) |
| `--host-pid` | no |  | reference host pid to compare namespaces/root against (default: 1) |
| `--herdr-socket` | no |  | controller-held herdr socket path to probe herdr seats |
| `--herdr-binary` | no |  | herdr CLI binary used for liveness probes (default: herdr) |
| `--ring1-tool` | no |  | Ring-1 guarded tool to probe via each target PATH (default: git) |
| `--json` | no |  | emit the machine-readable JSON fleet status |

### `dequeue`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `PR` |  | pull request number |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo` | yes |  | owner/name repository scope |
| `--token-env` | no |  | env var containing the GitHub token |
| `--convert-to-draft` | no |  | also convert the PR back to draft after dequeue |
| `--json` | no |  | emit machine-readable JSON |

### `dispatch`

plan and inspect governed seat dispatch (ce-ops#42)

### `dispatch plan`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--arc-ticket` | yes |  |  |
| `--issues-json` | no |  |  |
| `--repo` | no |  |  |
| `--label` | no |  |  |
| `--seat` | no |  |  |
| `--json` | no |  |  |

### `doctor`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | repo root to preflight (default: cwd) |
| `--venv` | no |  | target controller/seat venv directory to inspect |
| `--target-python` | no |  | target controller/seat interpreter path to inspect (overrides --venv) |
| `--check-seat-env` | no |  | require the target controller/seat env check even when no .venv is discovered |
| `--json` | no |  | emit machine-readable JSON |
| `--require-visible-launch` | no |  | treat a missing visible tmux terminal as a refusal (PCO-049) |
| `--require-worker` | no |  | treat missing rootless Podman (or rootful Podman) as a refusal (PCO-045) |
| `--no-check-packaging` | no |  | skip the dependency wheelhouse contract clause (RED-G-6) |
| `--require-installed-ce` | no |  | refuse unless doctor is running via an installed ce/cev3 console script |

### `event`

append/verify/sign/replay/index local CE-event chains (G2.003.1)

### `event append`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--stream` | yes |  | chain stream name (path-safe slug) |
| `--event-root` | yes |  | CE-event home (e.g. .ce/ce-events) |
| `--block-id` | yes |  | block id (pattern ceevt-<slug>) |
| `--emitting-role` | yes |  | canonical non-ratifying emitting role |
| `--operating-mode` | yes |  | operating-mode context strict\|auto\|transcendence (recorded only; an unknown mode is refused by the runtime with G2-EVENT-MODE-INVALID) |
| `--recorded-at` | yes |  | UTC timestamp YYYY-MM-DDThh:mm:ssZ |
| `--event-json` | yes |  | event mapping as JSON (kind/subject/summary[/payload]) |
| `--repo-root` | no |  | repo root for the git-ignore guard |
| `--key-id` | no |  | shape-only signature key_id |
| `--signature-value` | no |  | refuse-guarded: must stay reserved-inactive (no cryptography) |
| `--json` | no |  | emit machine-readable JSON |

### `event index`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--stream` | yes |  |  |
| `--event-root` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `event replay`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--stream` | yes |  |  |
| `--event-root` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `event sign`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--block-json` | yes |  | draft CE-event block mapping as JSON |
| `--key-id` | no |  | shape-only signature key_id |
| `--signature-value` | no |  | refuse-guarded: must stay reserved-inactive (no cryptography) |
| `--json` | no |  | emit machine-readable JSON |

### `event verify`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--stream` | yes |  |  |
| `--event-root` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `fanin`

build/inspect a local read-only evidence fan-in packet (no authority)

### `fanin build`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--request` | yes |  | path to the fan-in request (YAML/JSON) |
| `--packet-root` | yes |  | ignored output root for the packet (e.g. .hermes/fan-in/) |
| `--repo-root` | no |  | repo root for the git-ignore guard |
| `--packet-id` | no |  | override the request's packet_id |
| `--ratify` | no |  | refuse-only flag: ratification is never granted by fan-in (always refused) |
| `--enqueue` | no |  | refuse-only flag: integration-queue enqueue is never granted by fan-in (always refused) |
| `--land` | no |  | refuse-only flag: landing is never granted by fan-in (always refused) |
| `--json` | no |  | emit machine-readable JSON |

### `fanin inspect`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--packet` | yes |  | path to an existing fan-in packet |
| `--json` | no |  | emit machine-readable JSON |

### `harness-matrix`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | repo root to probe (default: cwd) |
| `--json` | no |  | emit machine-readable JSON instead of Markdown |

### `hud`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--harness` | no |  | Controller-seat harness |
| `--session` | no |  | tmux session name |
| `--window` | no |  | tmux window name |
| `--resume` | no |  | attach an existing launcher session |
| `--dry-run` | no |  | plan only; no tmux spawn, no provider login |
| `--no-tmux` | no |  | refuse-only flag: request a non-visible/headless seat (always refused) |
| `--claude-arg` | no |  | repeatable extra arg passed to the claude harness (use --claude-arg=<value> for dashed values) |
| `--codex-arg` | no |  | repeatable allowlisted extra arg passed to the codex harness (use --codex-arg=<value> for dashed values) |
| `--mcp-config` | no |  | CE-owned MCP config path under .ce/state/launch (pins --strict-mcp-config) |
| `--completion-report-ref` | no |  | deterministic completion-report pointer recorded for Ring 0 closeout verification |
| `--closeout-file` | no |  | deterministic closeout file pointer recorded for Ring 0 closeout verification |
| `--runtime-policy` | no |  | v3.5-F: path to the ratified runtime policy whose resource_envelopes bound this seat (systemd-run --user wrap); --dry-run renders the resource_bound block offline |
| `--backend` | no | `gvisor, local-noop, openshell` | runtime backend selector carried by --runtime-policy (gvisor aliases to gvisor-proxy) |
| `--claim-ticket` | no |  | ce-ops#38: acquire + verify a work-claim lock on this ticket (owner/name#N, an issue URL, or N inside the slug) BEFORE any launch side effect; a foreign active claim refuses the launch |
| `--repo-root` | no |  | repo root for lifecycle registration |
| `--ledger-root` | no |  | path to .ce/state/active-work-ledger for lifecycle registration |
| `--controller-id` | no |  | owner/controller id recorded in the governed seat lifecycle record |
| `--host-id` | no |  | host id recorded in the governed seat lifecycle record |
| `--purpose` | no |  | operator-readable purpose recorded in the governed seat lifecycle record |
| `--json` | no |  | emit machine-readable JSON |

### `init`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | repo root to initialize (default: cwd) |
| `--json` | no |  | emit machine-readable JSON |

### `lane`

governed visible lane-launch primitive

### `lane archive`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--transcript` | yes |  |  |
| `--archive-root` | yes |  |  |
| `--batch-slug` | yes |  |  |
| `--role` | yes |  |  |
| `--repo-root` | no |  | repo root for the git-ignore check |
| `--json` | no |  |  |

### `lane launch`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--controller-id` | yes |  |  |
| `--lane-id` | yes |  |  |
| `--role` | yes | `architect, implementer, reviewer, verification` |  |
| `--prompt` | yes |  | path to the consumed prompt pointer |
| `--prompt-sha` | yes |  | expected byte-level SHA256 of --prompt |
| `--repo-root` | yes |  |  |
| `--ledger-root` | yes |  | path to .hermes/active-work-ledger |
| `--handoff` | no |  | optional consumed handoff pointer path |
| `--handoff-sha` | no |  | expected byte-level SHA256 of --handoff |
| `--command` | no |  | optional local command to run in the pane (defaults to a safe inert placeholder) |
| `--claude-arg` | no |  | repeatable extra arg appended to a claude --command (use --claude-arg=<value> for dashed values) |
| `--mcp-config` | no |  | CE-owned MCP config path inside the repo / .hermes (pins --strict-mcp-config) |
| `--completion-report-ref` | no |  | deterministic completion-report pointer for Ring 0 closeout verification |
| `--closeout-file` | no |  | deterministic closeout file pointer for Ring 0 closeout verification |
| `--operating-mode` | no | `auto, strict, transcendence` | lane operating mode (default: strict); auto/transcendence require --tenant-policy |
| `--autonomy-class` | no |  | optional autonomy class carrier (G2.002.0 enum) |
| `--lane-kind` | no | `approval, audit, implementation, merge, read-only, review` | optional lane kind carrier (read-only/implementation/review/approval/merge/audit) |
| `--tenant-policy` | no |  | path to an Operator-ratified operating-mode-policy sidecar that ratifies an elevated mode |
| `--runtime-policy` | no |  | v3.5-F: path to the ratified runtime policy whose resource_envelopes bound this seat (systemd-run --user wrap); enforce refuses loudly on an unsupported host; advisory/off require a resource_optout ratification binding |
| `--backend` | no | `gvisor, local-noop, openshell` | runtime backend selector carried by --runtime-policy (gvisor aliases to gvisor-proxy) |
| `--ratification-evidence` | no |  | inherited ratification-evidence pointer carried for elevated modes / privileged lane kinds |
| `--reviewer-authority-ref` | no |  | G2.007.3: reviewer-authority envelope ref for a distinct reviewer venue (role=reviewer + --lane-kind review); validated then exported to the pane env as CE_REVIEWER_AUTHORITY_REF for the in-band hook |
| `--seat-env-file` | no |  | v3.1-G2f (F4/D2): path to an owner-only (0600-class) env file sourced into the seat process via an exec-wrap before launch — the per-seat credential contract (e.g. a reviewer token). The file PATH transits argv; the secret VALUE never enters argv, the tmux server, or any record. Refused if missing or group/world-accessible |
| `--claim-ticket` | no |  | ce-ops#38: acquire + verify a work-claim lock on this ticket (owner/name#N / issue URL / N inside the slug) BEFORE any lane side effect; a foreign active claim refuses the launch |
| `--purpose` | no |  | operator-readable purpose recorded in the governed seat lifecycle record |
| `--host-id` | no |  |  |
| `--pane-id` | no |  |  |
| `--session` | no |  | tmux session name |
| `--window` | no |  | tmux window name |
| `--worktree-path` | no |  |  |
| `--branch` | no |  |  |
| `--envelope-ref` | no |  |  |
| `--no-tmux` | no |  | request the logged headless operator-inspectable visibility backend instead of tmux |
| `--terminal-kind` | no | `headless, herdr, tmux` | visibility backend terminal kind for the lane (default: tmux) |
| `--json` | no |  | emit the machine-readable launch record (pane_path + the Pane Registry record) — the v3.1-G2b consumption seam for the reviewer-venue bridge; default output unchanged |

### `lane status`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--controller-id` | yes |  |  |
| `--lane-id` | yes |  |  |
| `--ledger-root` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `lane verify`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--controller-id` | yes |  |  |
| `--lane-id` | yes |  |  |
| `--ledger-root` | yes |  |  |
| `--transcript` | yes |  |  |
| `--stop-line` | yes |  |  |
| `--completion-report` | no |  |  |
| `--json` | no |  |  |

### `launch`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--harness` | no |  | Controller-seat harness |
| `--session` | no |  | tmux session name |
| `--window` | no |  | tmux window name |
| `--resume` | no |  | attach an existing launcher session |
| `--dry-run` | no |  | plan only; no tmux spawn, no provider login |
| `--no-tmux` | no |  | refuse-only flag: request a non-visible/headless seat (always refused) |
| `--claude-arg` | no |  | repeatable extra arg passed to the claude harness (use --claude-arg=<value> for dashed values) |
| `--codex-arg` | no |  | repeatable allowlisted extra arg passed to the codex harness (use --codex-arg=<value> for dashed values) |
| `--mcp-config` | no |  | CE-owned MCP config path under .ce/state/launch (pins --strict-mcp-config) |
| `--completion-report-ref` | no |  | deterministic completion-report pointer recorded for Ring 0 closeout verification |
| `--closeout-file` | no |  | deterministic closeout file pointer recorded for Ring 0 closeout verification |
| `--runtime-policy` | no |  | v3.5-F: path to the ratified runtime policy whose resource_envelopes bound this seat (systemd-run --user wrap); --dry-run renders the resource_bound block offline |
| `--backend` | no | `gvisor, local-noop, openshell` | runtime backend selector carried by --runtime-policy (gvisor aliases to gvisor-proxy) |
| `--claim-ticket` | no |  | ce-ops#38: acquire + verify a work-claim lock on this ticket (owner/name#N, an issue URL, or N inside the slug) BEFORE any launch side effect; a foreign active claim refuses the launch |
| `--repo-root` | no |  | repo root for lifecycle registration |
| `--ledger-root` | no |  | path to .ce/state/active-work-ledger for lifecycle registration |
| `--controller-id` | no |  | owner/controller id recorded in the governed seat lifecycle record |
| `--host-id` | no |  | host id recorded in the governed seat lifecycle record |
| `--purpose` | no |  | operator-readable purpose recorded in the governed seat lifecycle record |
| `--json` | no |  | emit machine-readable JSON |

### `ledger`

Side-Effect Ledger runtime (append-only hash chain)

### `ledger record`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--controller-id` | yes |  |  |
| `--lane-id` | yes |  |  |
| `--claim-ref` | yes |  | claim path relative to --active-work-ledger-root |
| `--effect-id` | yes |  |  |
| `--effect-kind` | yes | `container_action, credential_secret_adjacent_event, external_tracker_mutation, git_mutation, github_mutation, network_ci_deploy_action, provider_mcp_plugin_config_change, runtime_process_action, tracked_file_change` |  |
| `--effect-status` | yes | `cancelled, failed, observed, requested, started, succeeded, unknown` |  |
| `--summary` | yes |  |  |
| `--occurred-at` | yes |  | ISO-8601 UTC timestamp or source-controlled ref |
| `--repo-root` | yes |  |  |
| `--side-effect-ledger-root` | yes |  |  |
| `--active-work-ledger-root` | yes |  | path to .hermes/active-work-ledger |
| `--actor-role` | no | `architect, controller, implementer, reviewer, verification` |  |
| `--pane-ref` | no |  |  |
| `--subject-ref` | no |  |  |
| `--evidence-ref` | no |  | repeatable redaction-safe evidence reference |
| `--redaction` | no |  | repeatable redaction note |
| `--details-json` | no |  | non-secret metadata as a JSON object (arrays/scalars rejected) |
| `--json` | no |  |  |

### `ledger verify`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--side-effect-ledger-root` | yes |  |  |
| `--active-work-ledger-root` | no |  | optional: bind each record to a live claim |
| `--controller-id` | no |  | optional: restrict verification to one controller |
| `--lane-id` | no |  | optional: restrict verification to one lane |
| `--json` | no |  |  |

### `onboard`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | repo root to onboard (default: cwd) |
| `--state-root` | no |  | CE local state root for brain-init (default: .ce/state) |
| `--ledger-root` | no |  | path to the active-work-ledger for first-launch lifecycle registration |
| `--install-mode` | no | `agent, guided, hybrid, print, skip` | install mode (default: auto per §A.5 — hybrid when an agent is present, else guided; NEVER print). print = manual fallback; skip = dev override |
| `--install-root` | no |  | CE bootstrap install root passed to the verify-install provenance gate |
| `--harness` | no |  | first-launch Controller-seat harness (default: claude) |
| `--no-launch` | no |  | do everything up to (not including) the first governed launch |
| `--no-fix-path` | no |  | opt out of the managed CE-marked profile PATH block (Decision 4 default-on) |
| `--offline` | no |  | verify provenance against local install-state only (no live SHA256SUMS) |
| `--yes` | no |  | non-interactive: refuse with the missing list rather than silently proceed |
| `--emit-manifest` | no |  | emit the machine-readable phase manifest (consequence-class + reversibility) and exit |
| `--json` | no |  | emit machine-readable JSON |

### `pcl`

append/verify/replay/index/merge local PCL coordination ledgers (G2.004.1)

### `pcl append`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--ledger` | yes |  | ledger name (path-safe slug) |
| `--pcl-root` | yes |  | PCL home (e.g. .ce/pcl) |
| `--record-id` | yes |  | record id (pattern pcl-<slug>) |
| `--record-kind` | yes |  | canonical PCL record_kind |
| `--emitting-role` | yes |  | canonical non-ratifying emitting role |
| `--operating-mode` | yes |  | operating-mode context strict\|auto\|transcendence (recorded only; an unknown mode is refused with G2-PCL-MODE-INVALID) |
| `--recorded-at` | yes |  | UTC timestamp YYYY-MM-DDThh:mm:ssZ |
| `--body-json` | yes |  | record body mapping as JSON |
| `--repo-root` | no |  | repo root (records must not target .hermes/) |
| `--key-id` | no |  | shape-only signature key_id |
| `--signature-value` | no |  | refuse-guarded: must stay reserved-inactive (no cryptography) |
| `--json` | no |  | emit machine-readable JSON |

### `pcl index`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--ledger` | yes |  |  |
| `--pcl-root` | yes |  |  |
| `--repo-root` | no |  | repo root for the cache git-ignore guard |
| `--no-cache` | no |  | compute only; do not write the cache projection |
| `--json` | no |  | emit machine-readable JSON |

### `pcl merge`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--source` | yes |  | repeatable source ledger (>=2) |
| `--target` | yes |  | target ledger name for the merge projection |
| `--pcl-root` | yes |  |  |
| `--repo-root` | no |  | repo root for the cache git-ignore guard |
| `--no-cache` | no |  | compute only; do not write the cache projection |
| `--json` | no |  | emit machine-readable JSON |

### `pcl replay`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--ledger` | yes |  |  |
| `--pcl-root` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `pcl verify`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--ledger` | yes |  |  |
| `--pcl-root` | yes |  |  |
| `--json` | no |  | emit machine-readable JSON |

### `pickup`

autonomous forge work-pickup poller (read-only; ce-ops#55/#182)

### `pickup poll`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--identity` | yes |  | seat identity (e.g. ce-dev-2); selects ~/.ce-keys/<identity>.pat |
| `--keys-dir` | no |  | PAT directory (default: ~/.ce-keys) |
| `--allow-ambient-gh` | no |  | allow fallback to ambient gh auth token after CE_PICKUP_TOKEN and PAT file |
| `--repo` | no |  | restrict Search API queries and claims to one owner/name repo |
| `--org` | no |  | restrict Search API queries to one GitHub org/user slug |
| `--label` | no |  | repeatable team label to include as labeled work (comma-separated allowed) |
| `--state-root`, `--ledger-root` | no |  | pickup state root for dedup ledger (default: <state>/pickup) |
| `--claim` | no |  | S2: forge-arbitrate a claim per actionable item (else observe-only) |
| `--run-id` | no |  | run id stamped into the claim marker (default: derived) |
| `--enable-launch` | no |  | S3 canary (default OFF): on a successful claim, launch a governed lane |
| `--harness` | no | `claude, codex` | harness for the spawned governed lane (S3) |
| `--seed-root` | no |  | directory for per-item seed files (S3; default: <ledger-root>/seeds) |
| `--repo-root` | no |  | repo root for the spawned governed lane (S3) |
| `--lane-ledger-root` | no |  | active-work-ledger root for the spawned lane (S3; default: <repo-root>/.ce/state/active-work-ledger) |
| `--backoff-seconds` | no |  | re-read backoff for the fail-closed acquire race (default: 1.0) |
| `--json` | no |  | emit machine-readable JSON |

### `pickup triage`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--arc-ticket` | yes |  | parent/arc ticket (owner/name#N, URL, or N with --repo) |
| `--issues-json` | no |  | path to GitHub Search/list issues JSON, or '-' for stdin |
| `--repo` | no |  | owner/name default repo for bare arc tickets or issue payloads |
| `--label` | no |  | pickup label to add and expose as a ce pickup poll hint |
| `--seat` | no |  | repeatable seat/assignee login; comma-separated allowed |
| `--apply` | no |  | apply planned labels/assignees through gh api after claim collision checks |
| `--check-claims` | no |  | dry-run with live work-claim collision checks through gh api |
| `--json` | no |  | emit machine-readable JSON |

### `playbook`

discover, inspect, and run governed CE playbooks

### `playbook list`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--playbooks-root`, `--root` | no |  | root to search for PLAYBOOK.md files (default: cwd) |
| `--json` | no |  | emit machine-readable JSON |

### `playbook run`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `ref` |  | playbook id, directory, or PLAYBOOK.md path |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--playbooks-root`, `--root` | no |  | root used to resolve playbook ids (default: cwd) |
| `--dry-run` | no |  | print the governed run plan without side effects |
| `--json` | no |  | emit machine-readable JSON |

### `playbook show`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `ref` |  | playbook id, directory, or PLAYBOOK.md path |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--playbooks-root`, `--root` | no |  | root used to resolve playbook ids (default: cwd) |
| `--json` | no |  | emit machine-readable JSON |

### `publish-branch`

Positional arguments:

| Argument | Choices | Description |
| --- | --- | --- |
| `branch` |  | local branch to publish to origin |

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | repo worktree containing the branch |
| `--repo` | no |  | owner/name repo; default derives from origin URL |
| `--seat-id` | yes |  | contained seat id that authored the branch |
| `--actor` | no |  | host actor performing the publish |
| `--expect-author-name` | no |  |  |
| `--expect-author-email` | no |  |  |
| `--expect-committer-name` | no |  |  |
| `--expect-committer-email` | no |  |  |
| `--controller-id` | no |  | side-effect ledger controller id |
| `--lane-id` | no |  | side-effect ledger lane id |
| `--claim-ref` | no |  | active-work claim ref bound to this publish |
| `--side-effect-ledger-root` | no |  |  |
| `--active-work-ledger-root` | no |  |  |
| `--dry-run` | no |  | verify publishability without pushing |
| `--json` | no |  | emit machine-readable JSON |

### `queue`

preview/inspect Integration Queue state or run the Integrator poll belt

### `queue dry-run`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--request` | yes |  | path to the dry-run request (YAML/JSON) |
| `--preview-root` | yes |  | ignored output root for the preview (e.g. .hermes/integration-queue/) |
| `--repo-root` | no |  | repo root for the git-ignore guard |
| `--preview-id` | no |  | override the request's preview_id |
| `--json` | no |  | emit machine-readable JSON |

### `queue inspect`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--preview` | yes |  | path to an existing dry-run landing preview |
| `--json` | no |  | emit machine-readable JSON |

### `reviewer-triage`

plan-only reviewer assignment decision (no source-host mutation)

### `reviewer-triage plan`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--pr` | yes |  | pull request number |
| `--json` | no |  | emit machine-readable JSON |
| `--repo-root` | no |  | repo root for tracked policy inputs |
| `--repo` | no |  | owner/name repo id (default: derived from origin URL) |
| `--head-sha` | no |  | PR head SHA (default: local HEAD) |
| `--expected-head-sha` | no |  | fail closed unless it matches --head-sha |
| `--author-run-id` | no |  | author run id for the decision work_ref |
| `--author-login` | no |  | author source-host login |
| `--author-human-id` | no |  | resolved author human id |
| `--author-controller-id` | no |  | author controller id |
| `--author-venue-id` | no |  | author venue id |
| `--author-credential-domain-ref` | no |  | author credential-domain ref |
| `--author-os-user-ref` | no |  | author OS-user-domain ref |
| `--author-host-ref` | no |  | author host ref |
| `--last-pusher-login` | no |  | last pusher source-host login |
| `--last-pusher-human-id` | no |  | resolved last-pusher human id |
| `--changed-path` | no |  |  |
| `--mutation-class` | no |  |  |
| `--risk-tier` | no |  |  |
| `--registry` | no |  | reviewer registry YAML (default: .ce/reviewer-registry.yml if present) |
| `--coordination-policy` | no |  | coordination policy YAML (default: .ce/coordination.yml) |
| `--codeowners` | no |  | CODEOWNERS path (default: .github/CODEOWNERS) |
| `--codeowners-text` | no |  | inline CODEOWNERS text for tests/offline probes |
| `--required-team` | no |  |  |

### `surfaces`

inspect rented surface metadata

### `surfaces check-updates`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | repo root (default: cwd) |
| `--manifest` | no |  | surface manifest path (default: <repo-root>/surfaces/manifest.yaml) |
| `--json` | no |  |  |

### `surfaces fleet-rollout`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--manifest` | no |  | path to surfaces/manifest.yaml |
| `--timeout` | no |  | herdr readiness timeout per seat (seconds) |
| `--dry-run` | no |  | show plan without executing |

### `update`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--check` | no |  | resolve the latest signed release and compare without mutating |
| `--install-root` | no |  | CE bootstrap install root (default: CE_INSTALL_ROOT or installer default) |
| `--site` | no |  | CE mirror site (default: https://creator-engine.dev) |
| `--trust-anchor-url` | no |  | out-of-band ce-root-v1 DNS TXT resolver URL |
| `--json` | no |  |  |

### `validate-pr`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--repo-root` | no |  | PR worktree root (default: current directory) |
| `--base` | no |  | base branch/ref to fetch and merge-base against (default: origin/main) |
| `--declared-work-class` | no | `epic, feature, story, tiny` | declared PR work class; when omitted, read exactly one declared-work-class line from the PR carrier/body |
| `--head-ref` | no |  | PR head branch name for carrier slug (default: current branch) |
| `--allow-dirty` | no |  | continue despite working-tree changes; committed base..HEAD state is still what gets validated |
| `--test-command` | no |  | test command to compare at base and HEAD (default: <python> -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup) |

### `verify-install`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--install-root` | no |  | CE bootstrap install root (default: CE_INSTALL_ROOT or the installer default) |
| `--offline` | no |  | local-only verification; skip live SHA256SUMS comparison |
| `--json` | no |  |  |

### `worker`

worker isolation/spawn runtime

### `worker allocate`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--policy` | yes |  | path to the ratified worker-container policy record |
| `--controller-id` | yes |  |  |
| `--lane-id` | yes |  |  |
| `--claim-ref` | yes |  | claim path relative to --active-work-ledger-root |
| `--lease-ref` | yes |  | lease path relative to --active-work-ledger-root |
| `--active-work-ledger-root` | yes |  | path to .hermes/active-work-ledger |
| `--container-instance-root` | yes |  | root for container-instance records |
| `--instance-id` | yes |  |  |
| `--started-at` | no |  | ISO-8601 UTC start timestamp (defaults to now) |
| `--details-json` | no |  | non-secret metadata as a JSON object (secret-shaped values refused) |
| `--side-effect-ledger-root` | no |  | optional: record a container_started side effect |
| `--repo-root` | no |  | repo root (required with --side-effect-ledger-root) |
| `--json` | no |  |  |

### `worker gc`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--container-instance-root` | yes |  |  |
| `--claim-id` | no |  | optional: scope the sweep to one claim |
| `--json` | no |  |  |

### `worker run`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--role` | yes |  | role name from .claude/agents/<role>.md |
| `--brief` | yes |  | brief file to run |
| `--repo-root` | no |  | repo root containing .claude/agents (default: cwd) |
| `--worktree` | no |  | existing worker worktree path (default: --repo-root) |
| `--harness` | no | `claude, codex, hermes, openclaw` |  |
| `--run-id` | no |  | optional run id for .ce/state/worker-runs |
| `--parent-id` | no |  | parent/foreman id; defaults from worker-spawn environment |
| `--worker-id` | no |  | optional stable worker id for the spawned lane |
| `--findings-timeout` | no |  | seconds to wait for the worker findings artifact (default: 300) |
| `--json` | no |  |  |

### `worker scrub-env`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--worker-id` | yes |  |  |
| `--role` | yes | `architect_research, implementer, researcher, reviewer, verification` |  |
| `--scope-id` | yes |  |  |
| `--depth` | yes |  |  |
| `--parent-id` | no |  |  |
| `--home-path` | yes |  |  |
| `--json` | no |  |  |

### `worker spawn`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--role` | yes | `architect_research, implementer, researcher, reviewer, verification` |  |
| `--harness` | yes | `claude, codex, hermes, openclaw` |  |
| `--worktree` | yes |  | existing worker worktree path; must differ from the caller cwd |
| `--scope-id` | yes |  | ticket/scope identifier carried into the worker record |
| `--prompt-file` | no |  | prompt file consumed by digest/ref; body is not recorded |
| `--brief` | no |  | inline brief digested but not recorded |
| `--dry-run` | no |  | plan only; no launch and no worker.yaml write |
| `--depth` | no |  | worker recursion depth (default: CE_WORKER_DEPTH+1 or 1) |
| `--max-depth` | no |  | fail-closed recursion depth bound |
| `--parent-id` | no |  | parent/foreman id; defaults from CE_WORKER_ID/CE_FOREMAN_ID/CE_CONTROLLER_ID |
| `--worker-id` | no |  | optional stable worker id; otherwise derived from value-free inputs |
| `--json` | no |  |  |

### `worker status`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--container-instance-root` | yes |  |  |
| `--claim-id` | yes |  |  |
| `--instance-id` | yes |  |  |
| `--json` | no |  |  |

### `worker terminate`

Options:

| Option | Required | Choices | Description |
| --- | --- | --- | --- |
| `--instance-id` | yes |  |  |
| `--claim-id` | yes |  |  |
| `--container-instance-root` | yes |  |  |
| `--reason` | yes | `claim_lapsed, force_reap, normal_release, operator_abort, validator_refusal` |  |
| `--exit-code` | no |  |  |
| `--controller-id` | no |  |  |
| `--lane-id` | no |  |  |
| `--claim-ref` | no |  | claim path relative to --active-work-ledger-root |
| `--active-work-ledger-root` | no |  |  |
| `--side-effect-ledger-root` | no |  | optional: record a container_stopped side effect |
| `--repo-root` | no |  |  |
| `--json` | no |  |  |
