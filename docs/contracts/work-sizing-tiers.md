# Work-Sizing Tiers Contract

CE work classes (`tiny`, `story`, `feature`, `epic`) are ceremony tiers. They
are not Scrum or Agile work item types, and they do not assert a user-story or
epic relationship. The tier names select the minimum decomposition depth and
artifact bundle expected for governed work.

| Tier | Depth | Decomposition ceremony | Artifact set | Ratification gate posture |
| --- | ---: | --- | --- | --- |
| `tiny` | 0 | `scope_card` | `scope_card` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |
| `story` | 1 | `intent` + `scope` + `tasks` | `intent_line`, `scope_record`, `inline_tasks`, `tasks.ce.yml` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |
| `feature` | 2 | `spec` + `plan` + `tasks` | `spec.md`, `plan.md`, `tasks.md`, `tasks.ce.yml` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |
| `epic` | 3 | `prd` + `per_feature_plan` + `slices` | `prd.md`, `per_feature_plan.md`, `thin_slice_scope`, `tasks.ce.yml` | For `none` and `docs` mutation classes: `auto_back_gate`. Higher-risk mutation classes add their risk-axis gates. |

Ratification gates are finalized by the independent mutation-class axis:
`code` adds distinct review and operator merge; `schema` and `deploy` require an
operator front bet and operator merge; privileged mutation classes (`governance`,
`identity`, `security`, `attestation`, `redaction`) add human ratification,
non-delegability, ring-1 push blocking, and operator merge.

The work-sizing floor is a minimum, not an exact classifier. The validator
rejects declarations below the derived floor, but over-declaring is allowed and
conservative when an operator wants more ceremony than the diff strictly
requires.
