# Work-Sizing Tiers Contract

CE work classes (`XS`, `S`, `M`, `L`) are CE ceremony tiers. The labels are
diff-size tiers, not Agile or Scrum work item types. They do not assert a
user-story, feature, epic, sprint, backlog, or parent/child relationship. A tier
only selects the minimum decomposition depth, artifact bundle, and review
ceremony expected for governed CE work. During the migration window, validators
accept legacy aliases (`tiny`, `story`, `feature`, `epic`) and map them to
`XS`, `S`, `M`, and `L`.

| Tier | Depth | Decomposition ceremony | Artifact set | Ratification gate posture |
| --- | ---: | --- | --- | --- |
| `XS` | 0 | `scope_card` | `scope_card` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |
| `S` | 1 | `intent` + `scope` + `tasks` | `intent_line`, `scope_record`, `inline_tasks`, `tasks.ce.yml` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |
| `M` | 2 | `spec` + `plan` + `tasks` | `spec.md`, `plan.md`, `tasks.md`, `tasks.ce.yml` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |
| `L` | 3 | `prd` + `per_feature_plan` + `slices` | `prd.md`, `per_feature_plan.md`, `thin_slice_scope`, `tasks.ce.yml` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |

Ratification gates are finalized by the independent mutation-class axis:
`code` adds distinct review and operator merge; `schema` and `deploy` require an
operator front bet and operator merge; privileged mutation classes (`governance`,
`identity`, `security`, `attestation`, `redaction`) add human ratification,
non-delegability, ring-1 push blocking, and operator merge.

The work-sizing gate enforces a floor, not an exact classifier. The validator
derives the minimum tier from the PR diff and rejects any declaration below
that derived minimum. Declaring a higher tier is allowed because it adds
ceremony; declaring a lower tier is invalid even when the author intended the
change to be "small" in an Agile sense.
